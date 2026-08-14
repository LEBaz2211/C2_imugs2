import csv
import io
from pathlib import Path

from c2_imugs2.contract_docs import build_contract_model, build_docs_navigation, check_contract_documents, generate_contract_documents, render_contract_documents
from c2_imugs2.contract_inventory import build_contract_inventory
from c2_imugs2.contracts import build_contract_graph
from c2_imugs2.mission_config import validate_mission_config
from c2_imugs2.task_plan import validate_task_plan


ROOT = Path(__file__).resolve().parents[1]


def test_contract_graph_uses_editable_backend_as_canonical_evidence() -> None:
    graph = build_contract_graph(ROOT)

    evidence_paths = [ref["path"] for node in graph["nodes"] for ref in node.get("source_refs", [])]
    assert any(path.startswith("backend/") for path in evidence_paths)
    assert not any(path.startswith("legacy_ros/") for path in evidence_paths)
    assert all(
        ref["path"].startswith("backend/") or not ref["path"].startswith(("legacy_ros/", "backend/"))
        for interaction in graph["atlas"]["interactions"]
        for ref in interaction["source_refs"]
    )


def test_inventory_extracts_enums_transitions_and_numeric_contract_gap() -> None:
    inventory = build_contract_inventory(ROOT)
    groups = {item["name"]: item for item in inventory["enum_groups"]}
    machines = {item["id"]: item for item in inventory["state_machines"]}

    assert groups["MissionStatus"]["status"] == "consistent"
    assert groups["TaskState"]["status"] == "conflict"
    mission_edges = {(item["from"], item["to"]) for item in machines["mission_lifecycle"]["transitions"]}
    assert ("STARTED", "PAUSED") in mission_edges
    assert ("STARTED", "COMPLETED") in mission_edges
    task_mapping = {item["request"]: item["state"] for item in machines["edge_task_lifecycle"]["request_mappings"]}
    assert task_mapping["EXECUTE"] == "STARTED"
    assert task_mapping["DELETE"] == "COMPLETED"


def test_generated_contract_docs_are_deterministic_and_checkable(tmp_path: Path) -> None:
    documents = render_contract_documents(ROOT)
    output = tmp_path / "generated"

    generate_contract_documents(ROOT, output)

    assert check_contract_documents(ROOT, output) == []
    assert "```mermaid" in documents["states/mission-lifecycle.md"]
    assert "POST /api/missions/init" in documents["http/methods/post.md"]
    assert "GET /api/planning/diagnostics${suffix}" not in documents
    assert "http/get-api-planning-diagnostics-suffix.md" not in documents
    assert "http/get-api-planning-diagnostics.md" in documents
    assert "ros:service:multi_robot/edge/" not in {item["id"] for item in build_contract_model(ROOT)["interfaces"]}
    assert "ros:service:multi_robot/edge/agent_" not in {item["id"] for item in build_contract_model(ROOT)["interfaces"]}
    assert "ros:service:multi_robot/edge/agent_{agent_id}/add_task" in {
        item["id"] for item in build_contract_model(ROOT)["interfaces"]
    }
    assert "Complete extracted schema" in documents["schemas/mission-config.md"]
    assert "http/methods/get.md" in documents
    assert "ros-types/packages/task-msgs-srv.md" in documents
    assert "enums/sources/task-msgs.md" in documents
    assert "examples/single-robot-point-navigation.md" in documents
    assert "interface-inventory.csv" in documents
    csv_rows = list(csv.DictReader(io.StringIO(documents["interface-inventory.csv"])))
    assert len(csv_rows) == len(build_contract_model(ROOT)["interfaces"])
    init_row = next(row for row in csv_rows if row["interface_id"] == "http:POST /api/missions/init")
    assert init_row["modules"] == "Browser UI; FastAPI Adapter"
    assert init_row["verified_example_ids"] == "canonical_mission_config"
    assert init_row["standalone_doc"] == "http/post-api-missions-init.md"
    assert "10-waypoint route to Themis Fr" in documents["examples/single-robot-point-navigation.md"]
    assert "Canonical mission submitted to the adapter" in documents["http/post-api-missions-init.md"]
    assert "APPROVE status request" in documents["ros-topics/multi-robot-change-mission-status-request.md"]
    assert "State path in the verified navigation run" in documents["states/mission-lifecycle.md"]
    assert "Values used by the verified navigation run" in documents["enums/missionstatus.md"]
    assert "Verified one-robot navigation data" not in documents["http/get-api-health.md"]
    browser = documents["index.md"]
    assert browser.startswith("# Contract browser\n")
    assert "Documentation label: GENERATED" in browser
    assert "Source tree: `legacy_ros`" in browser
    assert "not the current editable backend" in browser
    assert browser.count('=== "') == 9
    assert browser.count('??? abstract "') >= len(build_contract_model(ROOT)["interfaces"])
    assert "Download interface inventory (CSV)" in browser
    assert "Module data flow extracted from code" in browser
    assert "Verified Themis navigation path" in browser
    assert "producer not statically paired" in browser
    assert "Canonical mission submitted to the adapter" in browser
    assert "POST /api/missions/init · init_mission" in browser
    assert "Mission lifecycle" in browser
    assert "TaskState · conflict" in browser
    assert "MissionConfig · mission_config.schema.json" in browser
    assert "workflows/index.md" not in documents
    assert "components/index.md" not in documents
    assert "gaps.md" not in documents
    assert "interfaces/operator-compose.md" not in documents
    assert documents["contract-model.json"].find('"atlas"') == -1
    (output / "states/mission-lifecycle.md").write_text("stale\n", encoding="utf-8")
    assert "stale: states/mission-lifecycle.md" in check_contract_documents(ROOT, output)


def test_documentation_model_keeps_runtime_example_separate_from_extracted_contracts() -> None:
    model = build_contract_model(ROOT)

    assert model["catalog_kind"] == "static_source_extraction"
    assert set(model) == {
        "schema_version",
        "catalog_kind",
        "canonical_source_tree",
        "source_digest",
        "interfaces",
        "usages",
        "modules",
        "data_flows",
        "enum_definitions",
        "enum_groups",
        "state_machines",
        "verified_examples",
        "verified_example_digest",
    }
    assert any(
        flow["interface_id"] == "http:POST /api/missions/init"
        and flow["producers"] == ["component:ui"]
        and flow["consumers"] == ["component:api"]
        for flow in model["data_flows"]
    )
    assert {item["kind"] for item in model["interfaces"]} <= {
        "http_endpoint",
        "ros_topic",
        "ros_service",
        "ros_type",
        "json_schema",
    }
    assert not any(
        "/centralized_coordination/test/" in ref["path"]
        for item in model["interfaces"]
        for ref in item.get("source_refs", [])
    )
    verified_run = model["verified_examples"][0]
    assert verified_run["verification"]["status"] == "runtime_verified"
    assert verified_run["verification"]["source_tree"] == "legacy_ros"
    assert not any(
        ref["path"].startswith("backend/")
        for example in verified_run["examples"]
        for ref in example.get("evidence_refs", [])
    )
    assert verified_run["facts"]["observed_waypoint_count"] == 10
    assert verified_run["facts"]["recorded_route_excerpt_lon_lat"][-1] == [
        4.391670213379427,
        50.84417059346137,
    ]
    interface_ids = {item["id"] for item in model["interfaces"]}
    assert {
        target
        for example in verified_run["examples"]
        for target in example["targets"]
    } <= interface_ids
    examples = {item["id"]: item["payload"] for item in verified_run["examples"]}
    validate_mission_config(examples["canonical_mission_config"])
    validate_task_plan(examples["task_plan_excerpt"])
    navigation = build_docs_navigation(ROOT)
    assert navigation == [{"All contracts": "index.md"}]
