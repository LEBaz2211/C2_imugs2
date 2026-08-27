"""MongoDB index bootstrap and bounded runtime-retention maintenance."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
import argparse
import hashlib
import json
import os
from typing import Any, Iterable, Mapping, Sequence

from pymongo import ASCENDING, DESCENDING, GEOSPHERE, MongoClient
from pymongo.errors import PyMongoError


RUNTIME_DATABASE = "RuntimeDB"
MAP_DATABASE = "MapDB"
VEHICLE_DATABASE = "VehicleDB"
SCENARIO_METADATA_COLLECTION = "_scenario_versions"
ACTIVE_SCENARIO_COLLECTION = "_active_scenario"
SCENARIO_ACTIVATION_COLLECTION = "_scenario_activations"
DEFAULT_FEEDBACK_COMPACTION_MAX_DOCUMENTS = 100_000


IndexDirection = int | str


@dataclass(frozen=True)
class MongoIndexSpec:
    database: str
    collection: str
    keys: tuple[tuple[str, IndexDirection], ...]
    name: str
    unique: bool = False
    partial_filter: Mapping[str, Any] | None = None
    compatibility_note: str = ""

    def create_options(self) -> dict[str, Any]:
        options: dict[str, Any] = {"name": self.name}
        if self.unique:
            options["unique"] = True
        if self.partial_filter is not None:
            options["partialFilterExpression"] = dict(self.partial_filter)
        return options


@dataclass(frozen=True)
class MongoIndexOutcome:
    database: str
    collection: str
    name: str
    status: str
    detail: str
    compatibility_note: str = ""


@dataclass(frozen=True)
class MongoBootstrapReport:
    outcomes: tuple[MongoIndexOutcome, ...]
    map_collections: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return all(outcome.status in {"created", "existing"} for outcome in self.outcomes)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "map_collections": list(self.map_collections),
            "outcomes": [asdict(outcome) for outcome in self.outcomes],
        }


def base_index_specs() -> tuple[MongoIndexSpec, ...]:
    """Indexes that match current compatibility-writer query shapes.

    MissionConfig and Planning intentionally remain non-unique. Their C++
    writers implement replacement as delete-then-insert, which is not atomic;
    an old or interrupted runtime can therefore contain duplicates. Uniqueness
    may be enabled only after an explicit data audit and writer migration.
    """

    runtime_lookup_note = (
        "Uses ObjectId insertion order because the compatibility writer has no explicit sequence field. "
        "Keep generated ObjectId values, or add a durable sequence before changing this index."
    )
    replace_writer_note = (
        "Non-unique for compatibility with the current delete-then-insert writer; audit duplicates and "
        "migrate that writer to an atomic upsert before enforcing uniqueness."
    )
    return (
        MongoIndexSpec(
            RUNTIME_DATABASE,
            "MissionFeedback",
            (("mission_id", ASCENDING), ("_id", DESCENDING)),
            "mission_feedback_mission_order",
            compatibility_note=runtime_lookup_note,
        ),
        MongoIndexSpec(
            RUNTIME_DATABASE,
            "Logs",
            (("mission_id", ASCENDING), ("_id", DESCENDING)),
            "logs_mission_order",
            compatibility_note=runtime_lookup_note,
        ),
        MongoIndexSpec(
            RUNTIME_DATABASE,
            "MissionConfig",
            (("mission_id", ASCENDING),),
            "mission_config_mission",
            compatibility_note=replace_writer_note,
        ),
        MongoIndexSpec(
            RUNTIME_DATABASE,
            "Planning",
            (("mission_id", ASCENDING),),
            "planning_mission",
            compatibility_note=replace_writer_note,
        ),
        MongoIndexSpec(
            RUNTIME_DATABASE,
            "ConnectedVehicles",
            (("agent_id", ASCENDING),),
            "connected_vehicles_agent",
            compatibility_note=(
                "Non-unique because registration documents are observations from compatibility writers; "
                "the operational read model must report duplicate registrations rather than hiding them."
            ),
        ),
        MongoIndexSpec(
            VEHICLE_DATABASE,
            "Vehicles",
            (("agent_id", ASCENDING),),
            "vehicles_agent",
            compatibility_note=(
                "Non-unique until all backend vehicle-profile writers use an audited atomic upsert."
            ),
        ),
        MongoIndexSpec(
            MAP_DATABASE,
            SCENARIO_METADATA_COLLECTION,
            (("map_collection", ASCENDING),),
            "scenario_versions_collection_unique",
            unique=True,
            partial_filter={"map_collection": {"$type": "string"}},
            compatibility_note=(
                "Partial uniqueness leaves incomplete historical metadata visible for audit while preventing "
                "two valid version records from owning the same immutable collection."
            ),
        ),
        MongoIndexSpec(
            MAP_DATABASE,
            SCENARIO_METADATA_COLLECTION,
            (("scenario_id", ASCENDING), ("version", ASCENDING)),
            "scenario_versions_identity_unique",
            unique=True,
            partial_filter={
                "scenario_id": {"$type": "string"},
                "version": {"$type": "string"},
            },
            compatibility_note=(
                "Partial uniqueness excludes incomplete historical rows; duplicate valid identities must be "
                "resolved manually rather than being deleted by bootstrap."
            ),
        ),
        MongoIndexSpec(
            MAP_DATABASE,
            SCENARIO_METADATA_COLLECTION,
            (("scenario_id", ASCENDING), ("created_at", DESCENDING)),
            "scenario_versions_catalog",
        ),
        MongoIndexSpec(
            MAP_DATABASE,
            ACTIVE_SCENARIO_COLLECTION,
            (("singleton", ASCENDING),),
            "active_scenario_singleton_unique",
            unique=True,
            partial_filter={"singleton": {"$type": "string"}},
            compatibility_note=(
                "Enforces the durable active-scenario singleton used by the runtime manager while retaining "
                "any incomplete historical rows for explicit audit."
            ),
        ),
        MongoIndexSpec(
            MAP_DATABASE,
            SCENARIO_ACTIVATION_COLLECTION,
            (("activation_id", ASCENDING),),
            "scenario_activation_id_unique",
            unique=True,
            partial_filter={"activation_id": {"$type": "string"}},
            compatibility_note=(
                "Protects idempotent activation transition upserts; duplicate valid activation IDs block "
                "bootstrap and are never repaired automatically."
            ),
        ),
        MongoIndexSpec(
            MAP_DATABASE,
            SCENARIO_ACTIVATION_COLLECTION,
            (("status", ASCENDING), ("recorded_at", DESCENDING)),
            "scenario_activations_status_recorded",
        ),
    )


def map_feature_index_specs(collection: str) -> tuple[MongoIndexSpec, ...]:
    collection = _safe_collection_name(collection)
    return (
        MongoIndexSpec(
            MAP_DATABASE,
            collection,
            (("properties.feature_id", ASCENDING),),
            "scenario_feature_id_unique",
            unique=True,
            partial_filter={"properties.feature_id": {"$type": "string"}},
            compatibility_note=(
                "Partial uniqueness preserves legacy features with no string feature_id; duplicate string IDs "
                "block this index and require a scenario-data repair."
            ),
        ),
        MongoIndexSpec(
            MAP_DATABASE,
            collection,
            (("properties.feature_type", ASCENDING),),
            "scenario_feature_type",
        ),
        MongoIndexSpec(
            MAP_DATABASE,
            collection,
            (("geometry", GEOSPHERE),),
            "scenario_feature_geometry_2dsphere",
            compatibility_note=(
                "MongoDB validates indexed GeoJSON. Invalid historical geometry blocks this index and is "
                "reported without modifying the immutable scenario collection."
            ),
        ),
    )


class MongoIndexManager:
    """Create known indexes without dropping, rebuilding, or repairing data."""

    def __init__(self, client: Any) -> None:
        self.client = client

    def ensure(self, specs: Iterable[MongoIndexSpec]) -> tuple[MongoIndexOutcome, ...]:
        return tuple(self._ensure_one(spec) for spec in specs)

    def _ensure_one(self, spec: MongoIndexSpec) -> MongoIndexOutcome:
        collection = self.client[spec.database][spec.collection]
        try:
            existing = list(collection.list_indexes())
        except PyMongoError as exc:
            return _outcome(spec, "error", f"could not inspect indexes: {exc}")

        requested_keys = tuple(spec.keys)
        for index in existing:
            current_keys = tuple((str(key), value) for key, value in index.get("key", {}).items())
            if index.get("name") == spec.name:
                if current_keys == requested_keys and _options_satisfy(index, spec):
                    return _outcome(spec, "existing", "matching named index already exists")
                return _outcome(
                    spec,
                    "conflict",
                    "an index with this name exists with different keys or options; bootstrap will not replace it",
                )
            if current_keys == requested_keys:
                if _options_satisfy(index, spec):
                    return _outcome(
                        spec,
                        "existing",
                        f"equivalent index already exists as {index.get('name', '<unnamed>')}",
                    )
                return _outcome(
                    spec,
                    "conflict",
                    (
                        f"the same key pattern exists as {index.get('name', '<unnamed>')} with incompatible "
                        "uniqueness or partial-filter options; bootstrap will not rebuild it"
                    ),
                )

        if spec.unique:
            try:
                duplicate = _find_duplicate_key(collection, spec)
            except PyMongoError as exc:
                return _outcome(spec, "error", f"could not audit uniqueness before index creation: {exc}")
            if duplicate is not None:
                return _outcome(
                    spec,
                    "blocked",
                    f"duplicate indexed value exists ({duplicate!r}); data was left unchanged",
                )

        try:
            collection.create_index(list(spec.keys), **spec.create_options())
        except PyMongoError as exc:
            return _outcome(spec, "error", f"index creation failed without changing application data: {exc}")
        return _outcome(spec, "created", "index created")


def bootstrap_mongo_indexes(
    mongodb_url: str,
    *,
    client_factory: Any = MongoClient,
    server_selection_timeout_ms: int = 3000,
) -> MongoBootstrapReport:
    """Idempotently bootstrap runtime and immutable-scenario indexes.

    This function never drops indexes or edits application documents. A
    uniqueness conflict or invalid GeoJSON is returned as a non-OK outcome for
    an operator to resolve deliberately.
    """

    with client_factory(mongodb_url, serverSelectionTimeoutMS=server_selection_timeout_ms) as client:
        client.admin.command("ping")
        map_database = client[MAP_DATABASE]
        existing_collections = set(map_database.list_collection_names())
        metadata = map_database[SCENARIO_METADATA_COLLECTION]
        discovered = {
            str(item["map_collection"])
            for item in metadata.find(
                {"map_collection": {"$type": "string"}},
                {"_id": 0, "map_collection": 1},
            )
            if item.get("map_collection") in existing_collections
        }
        map_collections = tuple(sorted(discovered))
        specs = list(base_index_specs())
        for collection in map_collections:
            specs.extend(map_feature_index_specs(collection))
        outcomes = MongoIndexManager(client).ensure(specs)
        return MongoBootstrapReport(outcomes=outcomes, map_collections=map_collections)


@dataclass(frozen=True)
class FeedbackRetentionPolicy:
    """Keep transitions forever while compacting repeated periodic snapshots."""

    recent_per_mission: int = 100
    checkpoint_interval: timedelta = timedelta(hours=1)
    preserve_first: bool = True

    def __post_init__(self) -> None:
        if self.recent_per_mission < 1:
            raise ValueError("recent_per_mission must be at least 1")
        if self.checkpoint_interval <= timedelta(0):
            raise ValueError("checkpoint_interval must be positive")


@dataclass(frozen=True)
class FeedbackCompactionPlan:
    documents_seen: int
    keep_ids: tuple[Any, ...]
    delete_ids: tuple[Any, ...]
    kept_by_reason: Mapping[str, int] = field(default_factory=dict)

    @property
    def documents_kept(self) -> int:
        return len(self.keep_ids)

    @property
    def documents_deleted(self) -> int:
        return len(self.delete_ids)

    def as_dict(self, *, include_ids: bool = False) -> dict[str, Any]:
        value: dict[str, Any] = {
            "documents_seen": self.documents_seen,
            "documents_kept": self.documents_kept,
            "candidate_delete_count": self.documents_deleted,
            "kept_by_reason": dict(self.kept_by_reason),
        }
        if include_ids:
            value["keep_ids"] = [str(document_id) for document_id in self.keep_ids]
            value["delete_ids"] = [str(document_id) for document_id in self.delete_ids]
        return value


@dataclass(frozen=True)
class FeedbackCompactionResult:
    plan: FeedbackCompactionPlan
    dry_run: bool
    deleted_count: int

    def as_dict(self, *, include_ids: bool = False) -> dict[str, Any]:
        return {
            "dry_run": self.dry_run,
            "deleted_count": self.deleted_count,
            **self.plan.as_dict(include_ids=include_ids),
        }


def plan_feedback_compaction(
    documents: Iterable[Mapping[str, Any]],
    policy: FeedbackRetentionPolicy | None = None,
) -> FeedbackCompactionPlan:
    """Return a deletion plan without touching MongoDB.

    The first and latest snapshots, a recent tail, status/request/issue
    transitions, path-content changes, and periodic liveness checkpoints are
    retained. Documents missing a usable mission ID, ObjectId, or timestamp are
    retained because deleting them cannot be proven safe.
    """

    retention = policy or FeedbackRetentionPolicy()
    indexed = list(enumerate(documents))
    grouped: dict[str, list[tuple[int, Mapping[str, Any]]]] = defaultdict(list)
    unsafe: list[tuple[int, Mapping[str, Any], str]] = []
    for input_index, document in indexed:
        mission_id = document.get("mission_id")
        if not isinstance(mission_id, str) or not mission_id or "_id" not in document:
            unsafe.append((input_index, document, "invalid_identity"))
            continue
        grouped[mission_id].append((input_index, document))

    keep_reasons: dict[Any, set[str]] = defaultdict(set)
    all_deletable_ids: list[Any] = []
    for _input_index, document, reason in unsafe:
        if "_id" in document:
            keep_reasons[document["_id"]].add(reason)

    for mission_documents in grouped.values():
        ordered = sorted(mission_documents, key=_feedback_order_key)
        if not ordered:
            continue
        for _input_index, document in ordered:
            all_deletable_ids.append(document["_id"])

        if retention.preserve_first:
            keep_reasons[ordered[0][1]["_id"]].add("first")
        keep_reasons[ordered[-1][1]["_id"]].add("latest")
        for _input_index, document in ordered[-retention.recent_per_mission :]:
            keep_reasons[document["_id"]].add("recent")

        previous_state: str | None = None
        previous_path: str | None = None
        last_evidence_at: datetime | None = None
        for _input_index, document in ordered:
            document_id = document["_id"]
            observed_at = _feedback_timestamp(document)
            if observed_at is None:
                keep_reasons[document_id].add("invalid_timestamp")

            state_signature = _state_signature(document)
            path_signature = _path_signature(document)
            changed = False
            if previous_state is not None and state_signature != previous_state:
                keep_reasons[document_id].add("status_change")
                changed = True
            if previous_path is not None and path_signature != previous_path:
                keep_reasons[document_id].add("path_change")
                changed = True
            if previous_state is None or previous_path is None:
                changed = True

            if observed_at is not None:
                if changed or last_evidence_at is None:
                    last_evidence_at = observed_at
                elif observed_at - last_evidence_at >= retention.checkpoint_interval:
                    keep_reasons[document_id].add("checkpoint")
                    last_evidence_at = observed_at
            previous_state = state_signature
            previous_path = path_signature

    keep_ids = tuple(document_id for document_id in all_deletable_ids if document_id in keep_reasons)
    delete_ids = tuple(document_id for document_id in all_deletable_ids if document_id not in keep_reasons)
    unsafe_ids = tuple(
        document["_id"]
        for _input_index, document, _reason in unsafe
        if "_id" in document and document["_id"] not in keep_ids
    )
    keep_ids += unsafe_ids
    reason_counts = Counter(reason for reasons in keep_reasons.values() for reason in reasons)
    return FeedbackCompactionPlan(
        documents_seen=len(indexed),
        keep_ids=keep_ids,
        delete_ids=delete_ids,
        kept_by_reason=dict(sorted(reason_counts.items())),
    )


def compact_mission_feedback(
    collection: Any,
    *,
    policy: FeedbackRetentionPolicy | None = None,
    mission_id: str | None = None,
    dry_run: bool = True,
    delete_batch_size: int = 1000,
    max_documents: int = DEFAULT_FEEDBACK_COMPACTION_MAX_DOCUMENTS,
) -> FeedbackCompactionResult:
    """Plan or explicitly apply feedback compaction to one Mongo collection.

    ``dry_run`` defaults to true. The caller must pass ``dry_run=False`` to
    delete only the redundant ObjectIds listed by the deterministic plan. The
    database-backed path refuses to materialize more than ``max_documents`` in
    memory; operators must scope or explicitly raise that guard.
    """

    if delete_batch_size < 1:
        raise ValueError("delete_batch_size must be at least 1")
    if max_documents < 1:
        raise ValueError("max_documents must be at least 1")
    query = {"mission_id": mission_id} if mission_id is not None else {}
    projection = {
        "mission_id": 1,
        "date": 1,
        "status": 1,
        "requested_status": 1,
        "issue": 1,
        "tasks": 1,
        "Status": 1,
        "RequestedStatus": 1,
        "Issue": 1,
        "Tasks": 1,
    }
    # The pure planner performs its own timestamp/ObjectId ordering. Avoid a
    # global blocking Mongo sort here: the operational index is optimized for
    # mission-scoped latest-first reads, while a full compaction can span many
    # missions and a large periodic history.
    documents = collection.find(query, projection)
    limiter = getattr(documents, "limit", None)
    if callable(limiter):
        documents = limiter(max_documents + 1)
    documents = list(documents)
    if len(documents) > max_documents:
        scope = (
            "the selected mission"
            if mission_id is not None
            else "RuntimeDB.MissionFeedback"
        )
        raise ValueError(
            f"feedback compaction refused to load more than {max_documents} documents from {scope}; "
            "scope the run with --feedback-mission-id or deliberately raise "
            "--feedback-max-documents after reviewing memory capacity"
        )
    plan = plan_feedback_compaction(documents, policy)
    if dry_run or not plan.delete_ids:
        return FeedbackCompactionResult(plan=plan, dry_run=dry_run, deleted_count=0)

    deleted_count = 0
    for offset in range(0, len(plan.delete_ids), delete_batch_size):
        batch = plan.delete_ids[offset : offset + delete_batch_size]
        result = collection.delete_many({"_id": {"$in": list(batch)}})
        deleted_count += int(result.deleted_count)
    return FeedbackCompactionResult(plan=plan, dry_run=False, deleted_count=deleted_count)


def compact_feedback_history(
    mongodb_url: str,
    *,
    policy: FeedbackRetentionPolicy | None = None,
    mission_id: str | None = None,
    dry_run: bool = True,
    delete_batch_size: int = 1000,
    max_documents: int = DEFAULT_FEEDBACK_COMPACTION_MAX_DOCUMENTS,
    client_factory: Any = MongoClient,
    server_selection_timeout_ms: int = 3000,
) -> FeedbackCompactionResult:
    """Preview or explicitly apply the policy to RuntimeDB.MissionFeedback."""

    with client_factory(mongodb_url, serverSelectionTimeoutMS=server_selection_timeout_ms) as client:
        client.admin.command("ping")
        return compact_mission_feedback(
            client[RUNTIME_DATABASE]["MissionFeedback"],
            policy=policy,
            mission_id=mission_id,
            dry_run=dry_run,
            delete_batch_size=delete_batch_size,
            max_documents=max_documents,
        )


def _options_satisfy(existing: Mapping[str, Any], requested: MongoIndexSpec) -> bool:
    if bool(existing.get("unique")) != requested.unique:
        return False
    existing_partial = existing.get("partialFilterExpression")
    if requested.partial_filter is None and existing_partial is not None:
        return False
    if requested.partial_filter is not None and existing_partial != requested.partial_filter:
        return False
    return True


def _find_duplicate_key(collection: Any, spec: MongoIndexSpec) -> Any | None:
    group_id: Any
    if len(spec.keys) == 1:
        group_id = f"${spec.keys[0][0]}"
    else:
        group_id = {f"key_{index}": f"${key}" for index, (key, _direction) in enumerate(spec.keys)}
    pipeline: list[dict[str, Any]] = []
    if spec.partial_filter:
        pipeline.append({"$match": dict(spec.partial_filter)})
    pipeline.extend(
        [
            {"$group": {"_id": group_id, "count": {"$sum": 1}}},
            {"$match": {"count": {"$gt": 1}}},
            {"$limit": 1},
        ]
    )
    duplicate = next(iter(collection.aggregate(pipeline, allowDiskUse=True)), None)
    return duplicate.get("_id") if duplicate else None


def _outcome(spec: MongoIndexSpec, status: str, detail: str) -> MongoIndexOutcome:
    return MongoIndexOutcome(
        database=spec.database,
        collection=spec.collection,
        name=spec.name,
        status=status,
        detail=detail,
        compatibility_note=spec.compatibility_note,
    )


def _safe_collection_name(value: str) -> str:
    if not value or "\x00" in value or value.startswith("system."):
        raise ValueError(f"unsafe MongoDB collection name: {value!r}")
    return value


def _feedback_order_key(item: tuple[int, Mapping[str, Any]]) -> tuple[datetime, str, int]:
    input_index, document = item
    observed_at = _feedback_timestamp(document) or datetime.min.replace(tzinfo=timezone.utc)
    return observed_at, str(document.get("_id", "")), input_index


def _feedback_timestamp(document: Mapping[str, Any]) -> datetime | None:
    raw = document.get("date")
    if isinstance(raw, datetime):
        parsed = raw
    elif isinstance(raw, str) and raw:
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        generation_time = getattr(document.get("_id"), "generation_time", None)
        parsed = generation_time if isinstance(generation_time, datetime) else None
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _state_signature(document: Mapping[str, Any]) -> str:
    state = {
        "status": document.get("status", document.get("Status")),
        "requested_status": document.get("requested_status", document.get("RequestedStatus")),
        "issue": document.get("issue", document.get("Issue")),
    }
    return _stable_hash(state)


def _path_signature(document: Mapping[str, Any]) -> str:
    if "tasks" in document:
        tasks = document.get("tasks")
    elif "Tasks" in document:
        tasks = document.get("Tasks")
    else:
        tasks = {"__path_field__": "absent"}
    return _stable_hash(tasks)


def _stable_hash(value: Any) -> str:
    serialized = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Create C2 iMUGS2 MongoDB indexes, or preview/apply deterministic feedback compaction."
        )
    )
    parser.add_argument(
        "--mongodb-url",
        default=os.environ.get("C2_IMUGS2_MONGODB_URL", "mongodb://localhost:27017"),
    )
    parser.add_argument(
        "--compact-feedback",
        action="store_true",
        help="preview RuntimeDB.MissionFeedback compaction instead of creating indexes",
    )
    parser.add_argument(
        "--apply-feedback-compaction",
        action="store_true",
        help="delete the previewed redundant feedback rows; requires --compact-feedback",
    )
    parser.add_argument("--feedback-mission-id", help="limit compaction to one mission ID")
    parser.add_argument(
        "--feedback-recent",
        type=int,
        default=100,
        help="retain this many latest snapshots per mission (default: 100)",
    )
    parser.add_argument(
        "--feedback-checkpoint-minutes",
        type=float,
        default=60.0,
        help="retain one unchanged liveness checkpoint per interval (default: 60)",
    )
    parser.add_argument(
        "--feedback-max-documents",
        type=int,
        default=DEFAULT_FEEDBACK_COMPACTION_MAX_DOCUMENTS,
        help=(
            "refuse a compaction scope larger than this many documents "
            f"(default: {DEFAULT_FEEDBACK_COMPACTION_MAX_DOCUMENTS})"
        ),
    )
    args = parser.parse_args(argv)
    if args.apply_feedback_compaction and not args.compact_feedback:
        parser.error("--apply-feedback-compaction requires --compact-feedback")
    try:
        if args.compact_feedback:
            policy = FeedbackRetentionPolicy(
                recent_per_mission=args.feedback_recent,
                checkpoint_interval=timedelta(minutes=args.feedback_checkpoint_minutes),
            )
            result = compact_feedback_history(
                args.mongodb_url,
                policy=policy,
                mission_id=args.feedback_mission_id,
                dry_run=not args.apply_feedback_compaction,
                max_documents=args.feedback_max_documents,
            )
            print(
                json.dumps(
                    {
                        "database": RUNTIME_DATABASE,
                        "collection": "MissionFeedback",
                        **result.as_dict(),
                    },
                    indent=2,
                )
            )
            return 0
        report = bootstrap_mongo_indexes(args.mongodb_url)
        print(json.dumps(report.as_dict(), indent=2))
        return 0 if report.ok else 1
    except (PyMongoError, ValueError) as exc:
        parser.error(f"MongoDB maintenance failed: {exc}")


if __name__ == "__main__":
    raise SystemExit(main())
