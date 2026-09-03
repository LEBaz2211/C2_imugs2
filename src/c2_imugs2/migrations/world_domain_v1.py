"""One-time reader for the pre-world control-plane vocabulary.

This is intentionally the only maintained module that knows the retired
collection and field names.  It never deletes source data; cleanup is a
separate operator step after verification and redeployment.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any

from pymongo import MongoClient

from ..infrastructure.legacy.map import load_user_geojson_map, normalize_user_geojson_feature


MIGRATION_ID = "world-domain-v1"
WORLD_DATABASE = "WorldDB"
MIGRATIONS_COLLECTION = "Migrations"


def create_backup(mongodb_url: str, backup_dir: Path) -> Path:
    executable = shutil.which("mongodump")
    backup_method = "host_mongodump"
    if executable:
        backup_dir.mkdir(parents=True, exist_ok=False)
        subprocess.run(
            [executable, "--uri", mongodb_url, "--out", str(backup_dir)],
            check=True,
        )
    else:
        docker = shutil.which("docker")
        if not docker:
            raise RuntimeError("mongodump or Docker is required before the world-domain migration can run")
        container = "c2-imugs2-backend-mongodb"
        remote_archive = f"/tmp/{MIGRATION_ID}-{hashlib.sha256(str(backup_dir).encode()).hexdigest()[:12]}.archive.gz"
        subprocess.run(
            [
                docker,
                "exec",
                container,
                "mongodump",
                "--uri",
                mongodb_url,
                f"--archive={remote_archive}",
                "--gzip",
            ],
            check=True,
        )
        backup_dir.mkdir(parents=True, exist_ok=False)
        subprocess.run(
            [
                docker,
                "cp",
                f"{container}:{remote_archive}",
                str(backup_dir / "mongodump.archive.gz"),
            ],
            check=True,
        )
        backup_method = "container_mongodump_archive"
    marker = backup_dir / "BACKUP_COMPLETE.json"
    marker.write_text(
        json.dumps(
            {
                "created_at": _now(),
                "mongodb_url_redacted": True,
                "method": backup_method,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return marker


def apply_migration(
    mongodb_url: str,
    repo_root: Path,
    *,
    backup_marker: Path,
    client_factory: Any = MongoClient,
) -> dict[str, Any]:
    if not backup_marker.is_file():
        raise RuntimeError("a completed mongodump marker is required before migration")
    with client_factory(mongodb_url, serverSelectionTimeoutMS=5000) as client:
        client.admin.command("ping")
        migrations = client[WORLD_DATABASE][MIGRATIONS_COLLECTION]
        existing = migrations.find_one({"migration_id": MIGRATION_ID}, {"_id": 0})
        if existing and existing.get("status") == "complete":
            return {**existing, "idempotent_reuse": True}

        report = _migrate_mongo(client)
        report["authoring_features"] = _import_authoring_features(client, repo_root)
        report.update(
            {
                "migration_id": MIGRATION_ID,
                "status": "complete",
                "completed_at": _now(),
                "backup_marker": str(backup_marker),
            }
        )
        migrations.replace_one(
            {"migration_id": MIGRATION_ID}, deepcopy(report), upsert=True
        )
        return report


def _migrate_mongo(client: Any) -> dict[str, Any]:
    old_map = client["MapDB"]
    world_db = client[WORLD_DATABASE]
    version_rows = list(old_map["_scenario_versions"].find({}, {"_id": 0}))
    active = old_map["_active_scenario"].find_one({"singleton": "active"}, {"_id": 0})
    launch_rows = list(old_map["_scenario_activations"].find({}, {"_id": 0}))

    migrated_versions = 0
    snapshot_names: set[str] = set()
    snapshot_by_source_collection: dict[str, str] = {}
    latest_definitions: dict[str, dict[str, Any]] = {}
    latest_features: dict[str, list[dict[str, Any]]] = {}
    for row in version_rows:
        old_collection = str(row.get("map_collection") or "")
        if not old_collection:
            continue
        world_id = _world_id(row.get("scenario_id"))
        features = _normalize_snapshot_features(
            list(old_map[old_collection].find({}, {"_id": 0})),
            selected_ids=row.get("feature_ids") or [],
            fallback_import_id=f"migrated-{str(row.get('version') or 'roads')[:16]}",
        )
        feature_hash = _feature_hash(features)
        snapshot_name = f"snapshot_{feature_hash[:32]}"
        snapshot_names.add(snapshot_name)
        snapshot_by_source_collection[old_collection] = snapshot_name
        snapshot = old_map[snapshot_name]
        if snapshot.count_documents({}) == 0 and features:
            snapshot.insert_many(deepcopy(features))
        if snapshot.count_documents({}) != len(features):
            raise RuntimeError(f"snapshot count verification failed for {snapshot_name}")
        if _feature_hash(list(snapshot.find({}, {"_id": 0}))) != feature_hash:
            raise RuntimeError(f"snapshot hash verification failed for {snapshot_name}")

        world_version = str(row.get("version") or row.get("content_hash") or "")[:64]
        version = {
            **_rename_fields(row),
            "world_id": world_id,
            "world_version": world_version,
            "map_collection": snapshot_name,
            "map_feature_hash": feature_hash,
            "feature_count": len(features),
            "immutable": True,
        }
        world_db["WorldVersions"].replace_one(
            {"world_id": world_id, "world_version": world_version}, version, upsert=True
        )
        migrated_versions += 1
        current = latest_definitions.get(world_id)
        if current is None or str(row.get("created_at") or "") > str(current.get("created_at") or ""):
            latest_definitions[world_id] = row
            latest_features[world_id] = features

    for world_id, row in latest_definitions.items():
        now = str(row.get("created_at") or _now())
        road_imports = _persist_migrated_road_imports(
            client,
            world_id,
            latest_features.get(world_id) or [],
            created_at=now,
        )
        definition = {
            "world_id": world_id,
            "name": str(row.get("name") or world_id),
            "map": str(row.get("map") or "rma"),
            "notes": str(row.get("notes") or ""),
            "feature_ids": deepcopy(row.get("feature_ids") or []),
            "agents": deepcopy(row.get("agents") or []),
            "road_imports": road_imports,
            "map_view": deepcopy(row.get("map_view")),
            "revision": 1,
            "created_at": now,
            "updated_at": now,
            "archived": False,
            "migrated_from": MIGRATION_ID,
        }
        world_db["WorldDefinitions"].update_one(
            {"world_id": world_id}, {"$setOnInsert": definition}, upsert=True
        )

    for row in launch_rows:
        migrated = _rename_fields(row)
        migrated["world_id"] = _world_id(row.get("scenario_id"))
        migrated["world_version"] = str(row.get("version") or "")
        migrated["launch_id"] = _launch_id(row)
        migrated["deployment_id"] = f"deployment-migrated-{migrated['launch_id'][:24]}"
        migrated["map_snapshot_token"] = str(row.get("activation_token") or "migrated")
        migrated["map_collection"] = snapshot_by_source_collection.get(
            str(row.get("map_collection") or ""), migrated.get("map_collection")
        )
        migrated["state_schema_version"] = "2.0"
        migrated["managed_runtime"] = False
        migrated["containers"] = []
        migrated["message"] = "Migrated historical world launch."
        for key in (
            "compose_file",
            "host_command",
            "started_containers",
            "docker_error",
            "error",
            "stale_at",
            "recovered_at",
        ):
            migrated.pop(key, None)
        world_db["WorldLaunches"].replace_one(
            {"launch_id": migrated["launch_id"]}, migrated, upsert=True
        )

    if active:
        migrated_active = _rename_fields(active)
        migrated_active.update(
            {
                "singleton": "active",
                "world_id": _world_id(active.get("scenario_id")),
                "world_version": str(active.get("version") or ""),
                "launch_id": str(active.get("activation_id") or "migrated-active"),
                "deployment_id": f"deployment-migrated-{str(active.get('activation_id') or 'active')[:24]}",
                "map_snapshot_token": str(active.get("activation_token") or "migrated"),
                "managed_runtime": True,
            }
        )
        source_collection = str(active.get("map_collection") or "")
        if source_collection:
            features = _normalize_snapshot_features(
                list(old_map[source_collection].find({}, {"_id": 0})),
                selected_ids=active.get("feature_ids") or [],
                fallback_import_id=f"migrated-{str(active.get('version') or 'roads')[:16]}",
            )
            feature_hash = _feature_hash(features)
            snapshot_name = f"snapshot_{feature_hash[:32]}"
            snapshot_names.add(snapshot_name)
            snapshot = old_map[snapshot_name]
            if snapshot.count_documents({}) == 0 and features:
                snapshot.insert_many(deepcopy(features))
            if snapshot.count_documents({}) != len(features):
                raise RuntimeError(f"snapshot count verification failed for {snapshot_name}")
            if _feature_hash(list(snapshot.find({}, {"_id": 0}))) != feature_hash:
                raise RuntimeError(f"snapshot hash verification failed for {snapshot_name}")
            migrated_active["map_collection"] = snapshot_name
            migrated_active["map_feature_hash"] = feature_hash
        world_db["ActiveWorld"].replace_one(
            {"singleton": "active"}, migrated_active, upsert=True
        )

    return {
        "source_versions": len(version_rows),
        "migrated_versions": migrated_versions,
        "world_definitions": len(latest_definitions),
        "deduplicated_snapshots": len(snapshot_names),
        "source_launches": len(launch_rows),
        "active_world_migrated": bool(active),
    }


def _import_authoring_features(client: Any, repo_root: Path) -> int:
    imported = 0
    runtime_dir = repo_root / "data" / "runtime"
    for path in sorted(runtime_dir.glob("user_features_*.geojson")):
        map_name = path.stem.removeprefix("user_features_")
        for raw in load_user_geojson_map(repo_root, map_name).get("features", []):
            feature = normalize_user_geojson_feature(raw)
            feature["properties"].update({"source": "authoring", "map": map_name})
            feature_id = feature["properties"]["feature_id"]
            result = client["MapDB"]["AuthoringFeatures"].update_one(
                {"map": map_name, "feature_id": feature_id},
                {
                    "$setOnInsert": {
                        "map": map_name,
                        "feature_id": feature_id,
                        "feature": feature,
                        "created_at": _now(),
                        "updated_at": _now(),
                        "migrated_from": str(path.relative_to(repo_root)),
                    }
                },
                upsert=True,
            )
            imported += int(result.upserted_id is not None)
    return imported


def _rename_fields(value: dict[str, Any]) -> dict[str, Any]:
    renamed = deepcopy(value)
    replacements = {
        "scenario_id": "world_id",
        "version": "world_version",
        "activation_id": "launch_id",
        "activation_token": "map_snapshot_token",
        "activation_phase": "launch_phase",
        "activated_at": "launched_at",
    }
    for old, new in replacements.items():
        if old in renamed:
            renamed[new] = renamed.pop(old)
    renamed.pop("singleton", None)
    return renamed


def _world_id(value: Any) -> str:
    text = str(value or "").strip()
    if text.startswith("scenario-"):
        return "world-" + text.removeprefix("scenario-")
    return text or "world-migrated-unknown"


def _launch_id(row: dict[str, Any]) -> str:
    text = str(row.get("activation_id") or "").strip()
    if text.startswith("activation-"):
        return "launch-" + text.removeprefix("activation-")
    return text or hashlib.sha256(
        json.dumps(row, sort_keys=True, default=str).encode()
    ).hexdigest()


def _feature_hash(features: list[dict[str, Any]]) -> str:
    ordered = sorted(
        features,
        key=lambda item: str((item.get("properties") or {}).get("feature_id") or item.get("id") or ""),
    )
    return hashlib.sha256(json.dumps(ordered, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _normalize_snapshot_features(
    features: list[dict[str, Any]],
    *,
    selected_ids: list[str],
    fallback_import_id: str,
) -> list[dict[str, Any]]:
    selected = {str(value) for value in selected_ids}
    normalized: list[dict[str, Any]] = []
    for raw in features:
        feature = deepcopy(raw)
        properties = dict(feature.get("properties") or {})
        legacy_import_id = properties.pop("scenario_road_import_id", None)
        if legacy_import_id and not properties.get("world_road_import_id"):
            properties["world_road_import_id"] = str(legacy_import_id)
        source_tool = properties.get("source_tool")
        if isinstance(source_tool, str):
            properties["source_tool"] = source_tool.replace("scenario_lab", "world_builder").replace(
                "scenario", "world"
            )
        feature_id = str(properties.get("feature_id") or feature.get("id") or "")
        if (
            feature_id not in selected
            and properties.get("feature_type") == "road"
            and (feature.get("geometry") or {}).get("type") == "LineString"
        ):
            properties.setdefault("world_road_import_id", fallback_import_id)
            properties["source"] = "frozen_openstreetmap"
        feature["properties"] = properties
        normalized.append(feature)
    return normalized


def _persist_migrated_road_imports(
    client: Any,
    world_id: str,
    features: list[dict[str, Any]],
    *,
    created_at: str,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for feature in features:
        properties = feature.get("properties") or {}
        import_id = properties.get("world_road_import_id")
        if (
            not import_id
            or properties.get("feature_type") != "road"
            or (feature.get("geometry") or {}).get("type") != "LineString"
        ):
            continue
        grouped.setdefault(str(import_id), []).append(feature)

    collection = client[WORLD_DATABASE]["WorldRoadFeatures"]
    metadata: list[dict[str, Any]] = []
    for import_id, roads in sorted(grouped.items()):
        collection.delete_many({"world_id": world_id, "import_id": import_id})
        if roads:
            collection.insert_many(
                [
                    {
                        "world_id": world_id,
                        "import_id": import_id,
                        "feature_index": index,
                        "feature": deepcopy(feature),
                        "migrated_from": MIGRATION_ID,
                    }
                    for index, feature in enumerate(roads)
                ]
            )
        metadata.append(
            {
                "import_id": import_id,
                "name": f"Migrated road section {import_id}",
                "bbox": _feature_bbox(roads),
                "feature_count": len(roads),
                "created_at": created_at,
            }
        )
    return metadata


def _feature_bbox(features: list[dict[str, Any]]) -> list[float]:
    points: list[tuple[float, float]] = []

    def collect(value: Any) -> None:
        if (
            isinstance(value, list)
            and len(value) >= 2
            and all(isinstance(item, int | float) and not isinstance(item, bool) for item in value[:2])
        ):
            points.append((float(value[0]), float(value[1])))
            return
        if isinstance(value, list):
            for item in value:
                collect(item)

    for feature in features:
        collect((feature.get("geometry") or {}).get("coordinates"))
    if not points:
        return [0.0, 0.0, 0.0, 0.0]
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return [min(xs), min(ys), max(xs), max(ys)]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(description="Back up and migrate the retired control plane into WorldDB")
    parser.add_argument("--mongodb-url", default="mongodb://127.0.0.1:27017")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--backup-dir", type=Path)
    args = parser.parse_args()
    backup_dir = args.backup_dir or args.repo_root / "data" / "backups" / f"world-domain-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    marker = create_backup(args.mongodb_url, backup_dir)
    print(json.dumps(apply_migration(args.mongodb_url, args.repo_root, backup_marker=marker), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
