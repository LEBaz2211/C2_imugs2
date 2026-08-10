from pathlib import Path

from c2_imugs2.contract_docs import build_contract_model, build_docs_navigation, check_contract_documents, generate_contract_documents, render_contract_documents
from c2_imugs2.contract_inventory import build_contract_inventory
from c2_imugs2.contracts import build_contract_graph


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
    assert "Complete extracted schema" in documents["schemas/mission-config.md"]
    assert "http/methods/get.md" in documents
    assert "ros-types/packages/task-msgs-srv.md" in documents
    assert "enums/sources/task-msgs.md" in documents
    assert "workflows/index.md" not in documents
    assert "components/index.md" not in documents
    assert "gaps.md" not in documents
    assert "interfaces/operator-compose.md" not in documents
    assert documents["contract-model.json"].find('"atlas"') == -1
    (output / "states/mission-lifecycle.md").write_text("stale\n", encoding="utf-8")
    assert "stale: states/mission-lifecycle.md" in check_contract_documents(ROOT, output)


def test_documentation_model_contains_extracted_contracts_only() -> None:
    model = build_contract_model(ROOT)

    assert model["catalog_kind"] == "static_source_extraction"
    assert set(model) == {
        "schema_version",
        "catalog_kind",
        "canonical_source_tree",
        "source_digest",
        "interfaces",
        "usages",
        "enum_definitions",
        "enum_groups",
        "state_machines",
    }
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
    navigation = build_docs_navigation(ROOT)
    assert any("HTTP API" in section for section in navigation)
    assert any("ROS types" in section for section in navigation)
