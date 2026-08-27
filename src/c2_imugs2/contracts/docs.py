from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import sys
from typing import Any

from .inventory import build_contract_inventory
from .graph import build_contract_graph


REPOSITORY_URL = "https://github.com/LEBaz2211/C2_imugs2"
EXTRACTED_NODE_KINDS = {"http_endpoint", "ros_topic", "ros_service", "ros_type", "json_schema"}
EXTRACTED_USAGE_KINDS = {"http_handler", "http_call", "ros_usage"}
EXTRACTED_STATE_MACHINES = {"mission_lifecycle", "edge_task_lifecycle"}
VERIFIED_RUN_PATH = Path("fixtures/verified_runs/single_robot_point_navigation.json")


def build_contract_model(repo_root: Path) -> dict[str, Any]:
    """Return source-extracted contracts plus separately labelled runtime examples."""

    raw_graph = build_contract_graph(repo_root, runtime={})
    inventory = build_contract_inventory(repo_root)
    nodes = [item for item in raw_graph["nodes"] if item["kind"] in EXTRACTED_NODE_KINDS]
    node_ids = {item["id"] for item in nodes}
    raw_nodes = {item["id"]: item for item in raw_graph["nodes"]}
    usages: list[dict[str, Any]] = []
    for edge in raw_graph["edges"]:
        if edge["kind"] not in EXTRACTED_USAGE_KINDS or not edge.get("source_refs"):
            continue
        interface_id = edge["source"] if edge["source"] in node_ids else edge["target"] if edge["target"] in node_ids else None
        if not interface_id:
            continue
        module_id = edge["target"] if edge["source"] == interface_id else edge["source"]
        if (raw_nodes.get(module_id) or {}).get("kind") != "component":
            module_id = ""
        usages.append(
            {
                "id": edge["id"],
                "interface_id": interface_id,
                "module_id": module_id,
                "usage_kind": edge["kind"],
                "relationship": edge["label"],
                "direction": edge.get("direction", ""),
                "contract": edge.get("contract", ""),
                "source_refs": _dedupe_refs(edge["source_refs"]),
            }
        )
    state_machines = [
        item
        for item in inventory["state_machines"]
        if item["id"] in EXTRACTED_STATE_MACHINES and item.get("transitions")
    ]
    verified_run = _load_verified_run(repo_root)
    _validate_verified_run(verified_run, nodes, model_enum_names={item["name"] for item in inventory["enum_groups"]}, state_machines=state_machines)
    modules, data_flows = _build_data_flows(nodes, usages, raw_nodes)
    return {
        "schema_version": 2,
        "catalog_kind": "static_source_extraction",
        "canonical_source_tree": "backend",
        "source_digest": raw_graph["source_digest"],
        "interfaces": sorted(nodes, key=lambda item: (item["kind"], item["label"])),
        "usages": sorted(usages, key=lambda item: (item["interface_id"], item["relationship"], item["id"])),
        "modules": modules,
        "data_flows": data_flows,
        "enum_definitions": inventory["enum_definitions"],
        "enum_groups": inventory["enum_groups"],
        "state_machines": state_machines,
        "verified_examples": [verified_run],
        "verified_example_digest": hashlib.sha256(
            (repo_root / VERIFIED_RUN_PATH).read_bytes()
        ).hexdigest(),
    }


def _build_data_flows(
    interfaces: list[dict[str, Any]],
    usages: list[dict[str, Any]],
    raw_nodes: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Pair source-extracted callers/publishers with handlers/providers/subscribers."""

    usages_by_interface: dict[str, list[dict[str, Any]]] = {}
    used_module_ids: set[str] = set()
    for usage in usages:
        usages_by_interface.setdefault(usage["interface_id"], []).append(usage)
        if usage.get("module_id"):
            used_module_ids.add(usage["module_id"])

    modules = [
        {
            "id": module_id,
            "label": raw_nodes[module_id]["label"],
            "description": raw_nodes[module_id].get("description", ""),
            "source_refs": _dedupe_refs(raw_nodes[module_id].get("source_refs", [])),
        }
        for module_id in sorted(used_module_ids)
        if module_id in raw_nodes
    ]
    flows: list[dict[str, Any]] = []
    for interface in interfaces:
        if interface["kind"] not in {"http_endpoint", "ros_topic", "ros_service"}:
            continue
        producers: set[str] = set()
        consumers: set[str] = set()
        interface_usages = usages_by_interface.get(interface["id"], [])
        for usage in interface_usages:
            module_id = usage.get("module_id")
            if not module_id:
                continue
            relationship = usage.get("direction") or usage.get("relationship")
            if usage["usage_kind"] == "http_call" or relationship in {"publishes", "calls"}:
                producers.add(module_id)
            elif usage["usage_kind"] == "http_handler" or relationship in {"subscribes", "provides"}:
                consumers.add(module_id)
        details = interface.get("details") or {}
        flows.append(
            {
                "interface_id": interface["id"],
                "label": interface["label"],
                "kind": interface["kind"],
                "data_type": details.get("type", ""),
                "producers": sorted(producers),
                "consumers": sorted(consumers),
                "fields": interface.get("fields", []),
                "source_refs": _dedupe_refs(
                    [
                        *interface.get("source_refs", []),
                        *(ref for usage in interface_usages for ref in usage.get("source_refs", [])),
                    ]
                ),
            }
        )
    return modules, sorted(flows, key=lambda item: (item["kind"], item["label"]))


def _interface_inventory_csv(
    model: dict[str, Any],
    examples_by_target: dict[str, list[dict[str, Any]]],
) -> str:
    """Render one RFC-compatible navigation row per extracted interface."""

    usages_by_interface: dict[str, list[dict[str, Any]]] = {}
    for usage in model["usages"]:
        usages_by_interface.setdefault(usage["interface_id"], []).append(usage)
    module_labels = {item["id"]: item["label"] for item in model["modules"]}
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(
        [
            "interface_id",
            "kind",
            "label",
            "method",
            "path_or_interface",
            "data_type",
            "package",
            "field_count",
            "fields_json",
            "usage_count",
            "modules",
            "relationships",
            "verified_example_ids",
            "verified_phases",
            "source_evidence",
            "standalone_doc",
        ]
    )
    for interface in model["interfaces"]:
        details = interface.get("details") or {}
        usages = usages_by_interface.get(interface["id"], [])
        examples = examples_by_target.get(interface["id"], [])
        modules = sorted(
            {
                module_labels.get(usage.get("module_id", ""), usage.get("module_id", ""))
                for usage in usages
                if usage.get("module_id")
            }
        )
        relationships = sorted(
            {
                f"{module_labels.get(usage.get('module_id', ''), usage.get('module_id', ''))}: {usage['relationship']}"
                for usage in usages
            }
        )
        fields = interface.get("fields") or []
        writer.writerow(
            [
                interface["id"],
                interface["kind"],
                interface["label"],
                details.get("method", ""),
                details.get("path") or details.get("interface") or details.get("path", ""),
                details.get("type", ""),
                details.get("package", ""),
                len(fields),
                json.dumps(fields, ensure_ascii=False, separators=(",", ":")),
                len(usages),
                "; ".join(modules),
                "; ".join(relationships),
                "; ".join(example["id"] for example in examples),
                "; ".join(dict.fromkeys(str(example.get("phase", "")) for example in examples)),
                "; ".join(f"{ref['path']}:{ref['line']}" for ref in _dedupe_refs(interface.get("source_refs", []))),
                _node_doc_path(interface),
            ]
        )
    return stream.getvalue()


def render_contract_documents(repo_root: Path) -> dict[str, str]:
    model = build_contract_model(repo_root)
    verified_run = model["verified_examples"][0]
    examples_by_target = _examples_by_target(verified_run)
    nodes_by_kind = {
        kind: [item for item in model["interfaces"] if item["kind"] == kind]
        for kind in EXTRACTED_NODE_KINDS
    }
    usages_by_interface: dict[str, list[dict[str, Any]]] = {}
    for usage in model["usages"]:
        usages_by_interface.setdefault(usage["interface_id"], []).append(usage)
    http_groups = _group_nodes(nodes_by_kind["http_endpoint"], lambda node: str((node.get("details") or {}).get("method") or "OTHER"))
    topic_groups = _group_nodes(nodes_by_kind["ros_topic"], _ros_namespace_group)
    service_groups = _group_nodes(nodes_by_kind["ros_service"], _ros_namespace_group)
    type_groups = _group_nodes(nodes_by_kind["ros_type"], _ros_type_group)
    enum_source_groups = _enum_source_groups(model)

    documents: dict[str, str] = {
        "contract-model.json": json.dumps(model, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        "interface-inventory.csv": _interface_inventory_csv(model, examples_by_target),
        "index.md": _contract_browser(
            repo_root,
            model,
            nodes_by_kind,
            usages_by_interface,
            verified_run,
            examples_by_target,
            http_groups,
            topic_groups,
            service_groups,
            type_groups,
        ),
        "examples/single-robot-point-navigation.md": _verified_run_page(verified_run, model["interfaces"]),
        "http/index.md": _group_overview("HTTP API", "FastAPI routes and matching frontend calls found in source, grouped by HTTP method.", http_groups, "methods"),
        "ros-topics/index.md": _group_overview("ROS topics", "Publisher and subscriber declarations grouped by their extracted ROS namespace.", topic_groups, "groups"),
        "ros-services/index.md": _group_overview("ROS services", "Service providers and clients grouped by their extracted ROS namespace.", service_groups, "groups"),
        "ros-types/index.md": _group_overview("ROS message and service types", "Fields parsed from checked-in `.msg` and `.srv` files, grouped by package and IDL kind.", type_groups, "packages"),
        "states/index.md": _states_index(model["state_machines"]),
        "enums/index.md": _enums_index(model, enum_source_groups),
        "schemas/index.md": _schemas_index(repo_root),
        "stylesheets/contract-reference.css": """.md-grid {
  max-width: 96rem;
}

.md-typeset table:not([class]) {
  display: table;
  width: 100%;
}

.md-typeset code {
  overflow-wrap: anywhere;
}

.mermaid {
  overflow-x: auto;
  text-align: center;
}

.tabbed-set > .tabbed-labels {
  position: sticky;
  top: 2.4rem;
  z-index: 3;
  background: var(--md-default-bg-color);
  border-bottom: 1px solid var(--md-default-fg-color--lightest);
}

.tabbed-set > .tabbed-labels > label {
  font-weight: 700;
}

.md-typeset details.abstract {
  margin: 0.45rem 0;
}

.md-typeset details.abstract > summary {
  cursor: pointer;
  font-family: var(--md-code-font-family);
}
""",
    }
    page_roots = {
        "http_endpoint": "http",
        "ros_topic": "ros-topics",
        "ros_service": "ros-services",
        "ros_type": "ros-types",
    }
    for node in model["interfaces"]:
        page_root = page_roots.get(node["kind"])
        if page_root:
            documents[f"{page_root}/{_node_slug(node)}.md"] = _interface_page(
                node,
                usages_by_interface.get(node["id"], []),
                verified_run,
                examples_by_target.get(node["id"], []),
            )
    for group_name, nodes in http_groups.items():
        documents[f"http/methods/{_slug(group_name)}.md"] = _node_index(f"HTTP {group_name}", "Routes extracted from FastAPI decorators.", nodes, "../")
    for group_name, nodes in topic_groups.items():
        documents[f"ros-topics/groups/{_slug(group_name)}.md"] = _node_index(f"ROS topics · {group_name}", "Topic declarations in this extracted namespace group.", nodes, "../")
    for group_name, nodes in service_groups.items():
        documents[f"ros-services/groups/{_slug(group_name)}.md"] = _node_index(f"ROS services · {group_name}", "Service declarations in this extracted namespace group.", nodes, "../")
    for group_name, nodes in type_groups.items():
        documents[f"ros-types/packages/{_slug(group_name)}.md"] = _node_index(f"ROS types · {group_name}", "IDL definitions in this extracted package/type group.", nodes, "../")
    for machine in model["state_machines"]:
        documents[f"states/{_slug(machine['id'])}.md"] = _state_machine_page(
            machine,
            verified_run,
            verified_run.get("state_paths", {}).get(machine["id"], []),
        )
    definitions = {item["id"]: item for item in model["enum_definitions"]}
    for group in model["enum_groups"]:
        documents[f"enums/{_slug(group['name'])}.md"] = _enum_page(
            group,
            definitions,
            verified_run,
            verified_run.get("enum_usage", {}).get(group["name"]),
        )
    for source_name, groups in enum_source_groups.items():
        documents[f"enums/sources/{_slug(source_name)}.md"] = _enum_source_page(source_name, groups)
    for schema_path in sorted((repo_root / "schemas").glob("*.schema.json")):
        schema_id = f"schema:{schema_path.name}"
        documents[f"schemas/{_slug(schema_path.stem.replace('.schema', ''))}.md"] = _schema_page(
            repo_root,
            schema_path,
            verified_run,
            examples_by_target.get(schema_id, []),
        )
    for relative, content in list(documents.items()):
        if relative.endswith(".md"):
            documents[relative] = _generated_document_label(content, verified_run)
    return documents


def _generated_document_label(content: str, verified_run: dict[str, Any]) -> str:
    heading, remainder = content.split("\n", 1)
    verification = verified_run["verification"]
    label = "\n".join(
        [
            heading,
            "",
            "> **Documentation label: GENERATED**",
            "> Static discovery from the editable `backend/`, adapter, frontend, and schemas;",
            "> declarations are not proof of runtime availability. Linked runtime examples are",
            f"> separate `{verification['source_tree']}` evidence from `{verification['stack']}` and do not verify the current editable backend.",
        ]
    )
    return f"{label}\n{remainder}"


def generate_contract_documents(repo_root: Path, output_dir: Path | None = None) -> list[Path]:
    repo_root = repo_root.resolve()
    output_dir = (output_dir or repo_root / "docs" / "generated").resolve()
    documents = render_contract_documents(repo_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    expected = {(output_dir / relative).resolve() for relative in documents}
    for existing in output_dir.rglob("*"):
        if existing.is_file() and existing.resolve() not in expected:
            existing.unlink()
    written: list[Path] = []
    for relative, content in sorted(documents.items()):
        path = output_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            path.write_text(content, encoding="utf-8")
        written.append(path)
    return written


def check_contract_documents(repo_root: Path, output_dir: Path | None = None) -> list[str]:
    repo_root = repo_root.resolve()
    output_dir = (output_dir or repo_root / "docs" / "generated").resolve()
    documents = render_contract_documents(repo_root)
    problems: list[str] = []
    expected = set(documents)
    actual = {str(path.relative_to(output_dir)) for path in output_dir.rglob("*") if path.is_file()} if output_dir.exists() else set()
    for relative in sorted(expected - actual):
        problems.append(f"missing: {relative}")
    for relative in sorted(actual - expected):
        problems.append(f"unexpected: {relative}")
    for relative in sorted(expected & actual):
        if (output_dir / relative).read_text(encoding="utf-8") != documents[relative]:
            problems.append(f"stale: {relative}")
    return problems


def build_docs_navigation(repo_root: Path) -> list[dict[str, Any]]:
    """Keep normal navigation on the single-page expandable browser."""

    build_contract_model(repo_root)
    return [{"All contracts": "index.md"}]


def _load_verified_run(repo_root: Path) -> dict[str, Any]:
    path = repo_root / VERIFIED_RUN_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["source_ref"] = {"path": str(VERIFIED_RUN_PATH), "line": 1}
    return payload


def _validate_verified_run(
    run: dict[str, Any],
    interfaces: list[dict[str, Any]],
    *,
    model_enum_names: set[str],
    state_machines: list[dict[str, Any]],
) -> None:
    interface_ids = {item["id"] for item in interfaces}
    target_ids = {
        target
        for example in run.get("examples", [])
        for target in example.get("targets", [])
    }
    unknown_targets = sorted(target_ids - interface_ids)
    if unknown_targets:
        raise ValueError(f"Verified run references unknown extracted contracts: {', '.join(unknown_targets)}")
    unknown_enums = sorted(set(run.get("enum_usage", {})) - model_enum_names)
    if unknown_enums:
        raise ValueError(f"Verified run references unknown extracted enums: {', '.join(unknown_enums)}")
    machine_ids = {item["id"] for item in state_machines}
    unknown_machines = sorted(set(run.get("state_paths", {})) - machine_ids)
    if unknown_machines:
        raise ValueError(f"Verified run references unknown extracted state machines: {', '.join(unknown_machines)}")
    example_ids = [str(item.get("id", "")) for item in run.get("examples", [])]
    if any(not item for item in example_ids) or len(example_ids) != len(set(example_ids)):
        raise ValueError("Verified run example ids must be present and unique")
    verification = run.get("verification") or {}
    source_tree = verification.get("source_tree")
    if source_tree not in {"backend", "legacy_ros"}:
        raise ValueError("Verified run must identify source_tree as backend or legacy_ros")
    evidence_refs = [
        ref
        for owner in [verification, *run.get("examples", [])]
        for ref in owner.get("evidence_refs", [])
    ]
    other_tree = "backend/" if source_tree == "legacy_ros" else "legacy_ros/"
    mixed_refs = sorted({ref["path"] for ref in evidence_refs if str(ref.get("path", "")).startswith(other_tree)})
    if mixed_refs:
        raise ValueError(
            f"Verified {source_tree} run mixes evidence from the other ROS tree: {', '.join(mixed_refs)}"
        )


def _examples_by_target(run: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for example in run.get("examples", []):
        for target in example.get("targets", []):
            grouped.setdefault(target, []).append(example)
    return grouped


def _contract_browser(
    repo_root: Path,
    model: dict[str, Any],
    nodes_by_kind: dict[str, list[dict[str, Any]]],
    usages_by_interface: dict[str, list[dict[str, Any]]],
    verified_run: dict[str, Any],
    examples_by_target: dict[str, list[dict[str, Any]]],
    http_groups: dict[str, list[dict[str, Any]]],
    topic_groups: dict[str, list[dict[str, Any]]],
    service_groups: dict[str, list[dict[str, Any]]],
    type_groups: dict[str, list[dict[str, Any]]],
) -> str:
    conflict_count = sum(item["status"] == "conflict" for item in model["enum_groups"])
    definitions = {item["id"]: item for item in model["enum_definitions"]}
    paired_flow_count = sum(bool(item["producers"] and item["consumers"]) for item in model["data_flows"])
    tabs = [
        (f"Verified run ({len(verified_run.get('examples', []))})", _browser_verified_run(verified_run, model["interfaces"])),
        (f"Data flow ({paired_flow_count})", _browser_data_flow(model, verified_run, examples_by_target)),
        (f"HTTP ({len(nodes_by_kind['http_endpoint'])})", _browser_interface_groups(http_groups, usages_by_interface, verified_run, examples_by_target)),
        (f"ROS topics ({len(nodes_by_kind['ros_topic'])})", _browser_interface_groups(topic_groups, usages_by_interface, verified_run, examples_by_target)),
        (f"ROS services ({len(nodes_by_kind['ros_service'])})", _browser_interface_groups(service_groups, usages_by_interface, verified_run, examples_by_target)),
        (f"ROS types ({len(nodes_by_kind['ros_type'])})", _browser_interface_groups(type_groups, usages_by_interface, verified_run, examples_by_target)),
        (f"States ({len(model['state_machines'])})", _browser_states(model["state_machines"], verified_run)),
        (f"Enums ({len(model['enum_groups'])})", _browser_enums(model["enum_groups"], definitions, verified_run)),
        (f"Schemas ({len(nodes_by_kind['json_schema'])})", _browser_schemas(repo_root, nodes_by_kind["json_schema"], verified_run, examples_by_target)),
    ]
    lines = [
        "# Contract browser",
        "",
        "Everything is available on this page. Select a tab, then expand only the contracts you need. Browser find (`Ctrl+F` / `Cmd+F`) searches the generated page text.",
        "",
        "[Download interface inventory (CSV)](interface-inventory.csv){ .md-button } [Download complete contract model (JSON)](contract-model.json){ .md-button }",
        "",
        '!!! info "What is generated"',
        "    Contract definitions, fields, usages, enums, and transitions are statically extracted from the editable source tree and schemas. The navigation payloads are separately labelled evidence from a frozen-reference run; they demonstrate contract compatibility, not current-backend runtime verification.",
        "",
        "| HTTP | ROS topics | ROS services | ROS types | States | Enums | Schemas |",
        "|---:|---:|---:|---:|---:|---:|---:|",
        f"| {len(nodes_by_kind['http_endpoint'])} | {len(nodes_by_kind['ros_topic'])} | {len(nodes_by_kind['ros_service'])} | {len(nodes_by_kind['ros_type'])} | {len(model['state_machines'])} | {len(model['enum_groups'])} ({conflict_count} conflict) | {len(nodes_by_kind['json_schema'])} |",
        "",
        f"Source digest: `{model['source_digest']}`",
        "",
    ]
    for title, body in tabs:
        lines.extend(_browser_tab(title, body))
    lines.extend([
        "",
        "## Extraction limitation",
        "",
        "Static extraction can miss names assembled dynamically at runtime. A declaration proves that it exists in source; it does not by itself prove that it was observed on a running ROS graph.",
    ])
    return "\n".join(lines) + "\n"


def _browser_tab(title: str, body: list[str]) -> list[str]:
    lines = [f'=== "{title}"', ""]
    lines.extend(f"    {line}" if line else "" for line in body)
    lines.append("")
    return lines


def _browser_collapse(title: str, body: list[str]) -> list[str]:
    safe_title = str(title).replace('"', "'").replace("\n", " ")
    lines = [f'??? abstract "{safe_title}"']
    lines.extend(f"    {line}" if line else "" for line in body)
    lines.append("")
    return lines


def _browser_verified_run(run: dict[str, Any], interfaces: list[dict[str, Any]]) -> list[str]:
    verification = run["verification"]
    facts = run["facts"]
    labels = {item["id"]: item["label"] for item in interfaces}
    lines = [
        "## One robot navigating to one Point",
        "",
        '!!! success "Runtime verified"',
        f"    {verification['summary']}",
        f"    Source tree: `{verification['source_tree']}` · Stack: `{verification['stack']}` · Evidence: {_refs(verification.get('evidence_refs', []))}",
        "    This run verifies the frozen compatibility reference, not the current editable backend.",
        "",
        "| Value | Runtime data |",
        "|---|---|",
        f"| Mission | `{facts['mission_id']}` |",
        f"| Robot | `{facts['agent_name']}` · `{facts['agent_id']}` |",
        f"| Start | `{facts['start_lon_lat']}` [longitude, latitude] |",
        f"| Destination | `{facts['destination_lon_lat']}` [longitude, latitude] |",
        f"| Behavior | `{facts['behavior']}` (NAVIGATE) |",
        f"| Requested speed | `{facts['requested_speed_mps']} m/s` |",
        f"| Observed route | `{facts['observed_waypoint_count']}` waypoints |",
        "",
        "### Recorded route coordinates",
        "",
        "The verification retained the first two and final coordinates. The seven unrecorded intermediate points are not invented.",
        "",
        "| Recorded position | Longitude | Latitude |",
        "|---|---:|---:|",
    ]
    for label, coordinates in zip(["first", "second", "final"], facts["recorded_route_excerpt_lon_lat"]):
        lines.append(f"| {label} | `{coordinates[0]}` | `{coordinates[1]}` |")
    lines.extend(["", "### Payloads", ""])
    for example in run.get("examples", []):
        target_labels = [labels.get(target, target.removeprefix("schema:")) for target in example.get("targets", [])]
        body = [
            f"**Phase:** {example.get('phase', '—')}",
            "",
            f"**Evidence class:** `{example.get('sample_kind', 'verified_flow')}`",
            "",
            f"**Applicable contracts:** {', '.join(f'`{item}`' for item in target_labels) or '—'}",
            "",
            "```json",
            *json.dumps(example["payload"], indent=2, ensure_ascii=False).splitlines(),
            "```",
        ]
        if example.get("notes"):
            body.extend(["", *[f"- {note}" for note in example["notes"]]])
        body.extend(["", f"Evidence: {_refs([run['source_ref'], *example.get('evidence_refs', [])])}"])
        lines.extend(_browser_collapse(f"{example.get('phase', '—')} · {example['title']}", body))
    return lines


def _browser_data_flow(
    model: dict[str, Any],
    run: dict[str, Any],
    examples_by_target: dict[str, list[dict[str, Any]]],
) -> list[str]:
    module_labels = {item["id"]: item["label"] for item in model["modules"]}
    paired = [item for item in model["data_flows"] if item["producers"] and item["consumers"]]
    verified = [item for item in model["data_flows"] if examples_by_target.get(item["interface_id"])]
    pair_groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for flow in paired:
        for producer in flow["producers"]:
            for consumer in flow["consumers"]:
                if producer != consumer:
                    pair_groups.setdefault((producer, consumer), []).append(flow)

    lines = [
        "## Module data flow extracted from code",
        "",
        "Arrows are generated by pairing callers with handlers, publishers with subscribers, and service callers with providers using the exact interface names found in source. They are regenerated whenever MkDocs builds.",
        "",
        '!!! note "Static boundary"',
        "    A dashed endpoint means only one side of that exact interface name was statically extracted. This commonly occurs where ROS names are assembled dynamically; the generator does not invent the missing link.",
        "",
        "### Module overview",
        "",
        "```mermaid",
        "flowchart LR",
    ]
    overview_modules = {module_id for pair in pair_groups for module_id in pair}
    for module_id in sorted(overview_modules):
        lines.append(f'  {_mermaid_id(module_id)}["{_mermaid_text(module_labels.get(module_id, module_id))}"]')
    for index, ((producer, consumer), flows) in enumerate(sorted(pair_groups.items())):
        kinds: dict[str, int] = {}
        for flow in flows:
            kinds[flow["kind"]] = kinds.get(flow["kind"], 0) + 1
        summary = " · ".join(f"{_flow_kind_label(kind)} {count}" for kind, count in sorted(kinds.items()))
        lines.append(
            f"  {_mermaid_id(producer)} -->|{_mermaid_text(summary)}| {_mermaid_id(consumer)}"
        )
    lines.extend([
        "```",
        "",
        "The counts represent distinct exact interface contracts, not message volume.",
        "",
        "### Verified Themis navigation path",
        "",
        "This view filters the extracted flows to interfaces carrying data recorded in the checked-in single-robot test.",
        "",
        "```mermaid",
        "flowchart LR",
        "  classDef unresolved stroke-dasharray: 5 5,fill:transparent",
    ])
    verified_module_ids = {
        module_id
        for flow in verified
        for module_id in [*flow["producers"], *flow["consumers"]]
    }
    for module_id in sorted(verified_module_ids):
        lines.append(f'  {_mermaid_id(module_id)}["{_mermaid_text(module_labels.get(module_id, module_id))}"]')
    for index, flow in enumerate(verified):
        contract_id = f"FLOW_{index}"
        type_suffix = f"<br/>{flow['data_type']}" if flow.get("data_type") else ""
        lines.append(f'  {contract_id}(["{_mermaid_text(flow["label"])}{_mermaid_text(type_suffix)}"])')
        if flow["producers"]:
            for producer in flow["producers"]:
                lines.append(f"  {_mermaid_id(producer)} --> {contract_id}")
        else:
            unresolved_id = f"UNRESOLVED_IN_{index}"
            lines.extend([f'  {unresolved_id}["producer not statically paired"] -.-> {contract_id}', f"  class {unresolved_id} unresolved"])
        if flow["consumers"]:
            for consumer in flow["consumers"]:
                lines.append(f"  {contract_id} --> {_mermaid_id(consumer)}")
        else:
            unresolved_id = f"UNRESOLVED_OUT_{index}"
            lines.extend([f'  {contract_id} -.-> {unresolved_id}["consumer not statically paired"]', f"  class {unresolved_id} unresolved"])
    lines.extend(["```", "", "### Data structures and real examples", ""])
    for flow in verified:
        producers = ", ".join(f"`{module_labels.get(item, item)}`" for item in flow["producers"]) or "_not statically paired_"
        consumers = ", ".join(f"`{module_labels.get(item, item)}`" for item in flow["consumers"]) or "_not statically paired_"
        body = [
            f"**Flow:** {producers} → {consumers}",
            "",
            f"**Contract kind:** `{flow['kind']}`",
            "",
            f"**Data type:** `{flow.get('data_type') or 'not declared on this interface'}`",
        ]
        if flow.get("fields"):
            body.extend(["", "#### Extracted fields", "", "| Section | Type | Name |", "|---|---|---|"])
            for field in flow["fields"]:
                body.append(f"| {field.get('section', '—')} | `{_cell(field.get('type', ''))}` | `{_cell(field.get('name', ''))}` |")
        body.extend(_browser_examples(run, examples_by_target[flow["interface_id"]]))
        body.extend(["", "#### Source evidence", "", *_refs_list(flow.get("source_refs", [])).splitlines()])
        lines.extend(_browser_collapse(f"{flow['label']} · {flow.get('data_type') or flow['kind']}", body))
    return lines


def _flow_kind_label(kind: str) -> str:
    return {
        "http_endpoint": "HTTP",
        "ros_topic": "topics",
        "ros_service": "services",
    }.get(kind, kind)


def _browser_interface_groups(
    groups: dict[str, list[dict[str, Any]]],
    usages_by_interface: dict[str, list[dict[str, Any]]],
    verified_run: dict[str, Any],
    examples_by_target: dict[str, list[dict[str, Any]]],
) -> list[str]:
    lines: list[str] = []
    for group_name, nodes in groups.items():
        lines.extend([f"## {group_name}", "", f"{len(nodes)} extracted contract{'s' if len(nodes) != 1 else ''}.", ""])
        for node in nodes:
            details = node.get("details") or {}
            qualifier = details.get("type") or details.get("handler") or node["kind"]
            body = _browser_interface_body(node, usages_by_interface.get(node["id"], []), verified_run, examples_by_target.get(node["id"], []))
            lines.extend(_browser_collapse(f"{node['label']} · {qualifier}", body))
    return lines


def _browser_interface_body(
    node: dict[str, Any],
    usages: list[dict[str, Any]],
    verified_run: dict[str, Any],
    examples: list[dict[str, Any]],
) -> list[str]:
    details = node.get("details") or {}
    lines = [
        node.get("description") or "Extracted interface declaration.",
        "",
        f"[Open standalone page]({_node_doc_path(node)})",
        "",
        "| Property | Extracted value |",
        "|---|---|",
        f"| Kind | `{node['kind']}` |",
    ]
    for key in ("method", "path", "handler", "interface", "type", "package"):
        if details.get(key) not in (None, ""):
            lines.append(f"| {key.replace('_', ' ').title()} | `{_cell(details[key])}` |")
    fields = node.get("fields") or []
    if fields:
        lines.extend(["", "#### Fields", "", "| Section | Type | Name |", "|---|---|---|"])
        for field in fields:
            lines.append(f"| {field.get('section', '—')} | `{_cell(field.get('type', ''))}` | `{_cell(field.get('name', ''))}` |")
    if usages:
        lines.extend(["", "#### Source usages", "", "| Relationship | Contract | Evidence |", "|---|---|---|"])
        for usage in usages:
            lines.append(f"| {_cell(usage['relationship'])} | `{_cell(usage.get('contract') or '—')}` | {_refs(usage['source_refs'])} |")
    if examples:
        lines.extend(_browser_examples(verified_run, examples))
    lines.extend(["", "#### Definition evidence", "", *_refs_list(node.get("source_refs", [])).splitlines()])
    return lines


def _browser_examples(run: dict[str, Any], examples: list[dict[str, Any]]) -> list[str]:
    lines = ["", "#### Verified navigation data"]
    for example in examples:
        lines.extend([
            "",
            f"##### {example['title']}",
            "",
            f"Phase: **{example.get('phase', '—')}** · Evidence class: `{example.get('sample_kind', 'verified_flow')}`",
            "",
            "```json",
            *json.dumps(example["payload"], indent=2, ensure_ascii=False).splitlines(),
            "```",
        ])
        if example.get("notes"):
            lines.extend(["", *[f"- {note}" for note in example["notes"]]])
        lines.extend(["", f"Evidence: {_refs([run['source_ref'], *example.get('evidence_refs', [])])}"])
    return lines


def _browser_states(machines: list[dict[str, Any]], run: dict[str, Any]) -> list[str]:
    lines = [
        "## Source-parsed state machines",
        "",
        "Transitions are parsed from explicit source patterns. The verified path is shown separately inside each state machine.",
        "",
    ]
    for machine in machines:
        body = [machine["description"], "", "```mermaid", "stateDiagram-v2"]
        if "ANY" in {item["from"] for item in machine["transitions"]}:
            body.append('  state "Any current state" as N_ANY')
        for state in machine["states"]:
            body.append(f"  state \"{_mermaid_text(state['name'])} ({state['value']})\" as {_mermaid_id(state['name'])}")
        for transition in machine["transitions"]:
            if transition["from"] != transition["to"]:
                body.append(f"  {_mermaid_id(transition['from'])} --> {_mermaid_id(transition['to'])}: {_mermaid_text(transition['trigger'])}")
        body.extend(["```", "", "#### State values", "", "| Value | State | Description |", "|---:|---|---|"])
        for state in sorted(machine["states"], key=lambda item: (isinstance(item["value"], str), item["value"])):
            body.append(f"| `{state['value']}` | `{state['name']}` | {_cell(state.get('description') or '')} |")
        body.extend(["", "#### Extracted transitions", "", "| From | Trigger | To | Evidence |", "|---|---|---|---|"])
        for transition in machine["transitions"]:
            body.append(f"| `{transition['from']}` | {_cell(transition['trigger'])} | `{transition['to']}` | {_refs([transition['source_ref']])} |")
        if machine.get("request_mappings"):
            body.extend(["", "#### Request mapping", "", "| Request | Resulting state | Evidence |", "|---|---|---|"])
            for mapping in machine["request_mappings"]:
                body.append(f"| `{mapping['request']}` | `{mapping['state']}` | {_refs([mapping['source_ref']])} |")
        observed_path = run.get("state_paths", {}).get(machine["id"], [])
        if observed_path:
            body.extend(["", "#### Verified navigation path", "", "```mermaid", "flowchart LR"])
            for index, item in enumerate(observed_path):
                body.append(f"  V{index}[\"{_mermaid_text(item['state'])} ({item['value']})\"]")
                if index:
                    body.append(f"  V{index - 1} -->|{_mermaid_text(item['event'])}| V{index}")
            body.extend(["```", "", "| Order | State | Value | Runtime event |", "|---:|---|---:|---|"])
            for index, item in enumerate(observed_path, start=1):
                body.append(f"| {index} | `{item['state']}` | `{item['value']}` | {_cell(item['event'])} |")
        lines.extend(_browser_collapse(f"{machine['name']} · {len(machine['states'])} states · {len(machine['transitions'])} transitions", body))
    return lines


def _browser_enums(
    groups: list[dict[str, Any]],
    definitions: dict[str, dict[str, Any]],
    run: dict[str, Any],
) -> list[str]:
    lines = ["## Source enum registry", "", "Same-name declarations are compared by their member/value signatures.", ""]
    for group in groups:
        body: list[str] = []
        if group["status"] == "conflict":
            body.extend(['!!! warning "Conflicting extracted definitions"', f"    {group['variant_count']} different member/value signatures were found.", ""])
        for definition_id in group["definitions"]:
            item = definitions[definition_id]
            body.extend([
                f"#### {item['qualified_name']}",
                "",
                f"Language: **{item['language']}** · Evidence: {_refs([item['source_ref']])}",
                "",
                "| Value | Member | Source comment |",
                "|---:|---|---|",
            ])
            for member in item["members"]:
                body.append(f"| `{member['value']}` | `{member['name']}` | {_cell(member.get('description') or '')} |")
            body.append("")
        observed = run.get("enum_usage", {}).get(group["name"])
        if observed:
            body.extend(["#### Values used by the verified navigation run", ""])
            if observed.get("definition"):
                body.extend([f"Runtime definition: **{observed['definition']}**.", ""])
            body.extend(["| Value | Member | Where it appeared |", "|---:|---|---|"])
            for item in observed.get("values", []):
                body.append(f"| `{item['value']}` | `{item['member']}` | {_cell(item['when'])} |")
        status = "conflict" if group["status"] == "conflict" else "consistent"
        lines.extend(_browser_collapse(f"{group['name']} · {status} · {group['definition_count']} definitions", body))
    return lines


def _browser_schemas(
    repo_root: Path,
    nodes: list[dict[str, Any]],
    run: dict[str, Any],
    examples_by_target: dict[str, list[dict[str, Any]]],
) -> list[str]:
    lines = ["## Canonical JSON schemas", "", "Each entry includes the flattened contract and complete checked-in schema.", ""]
    for node in sorted(nodes, key=lambda item: item["label"].lower()):
        path = repo_root / str((node.get("details") or {}).get("path"))
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = _flatten_schema(payload)
        body = [
            f"[Open standalone page]({_node_doc_path(node)})",
            "",
            "| JSON path | Type | Required | Constraints / description |",
            "|---|---|---|---|",
        ]
        for row in rows:
            body.append(f"| `{_cell(row['path'])}` | `{_cell(row['type'])}` | {row['required']} | {_cell(row['details'])} |")
        examples = examples_by_target.get(node["id"], [])
        if examples:
            body.extend(_browser_examples(run, examples))
        body.extend(["", "#### Complete schema", "", "```json", *json.dumps(payload, indent=2, ensure_ascii=False).splitlines(), "```"])
        lines.extend(_browser_collapse(f"{node['label']} · {path.name}", body))
    return lines


def _node_doc_path(node: dict[str, Any]) -> str:
    if node["kind"] == "json_schema":
        schema_name = Path(str((node.get("details") or {}).get("path", ""))).name
        return f"schemas/{_slug(schema_name.replace('.schema.json', ''))}.md"
    roots = {
        "http_endpoint": "http",
        "ros_topic": "ros-topics",
        "ros_service": "ros-services",
        "ros_type": "ros-types",
    }
    return f"{roots[node['kind']]}/{_node_slug(node)}.md"


def _overview(model: dict[str, Any], nodes_by_kind: dict[str, list[dict[str, Any]]]) -> str:
    conflict_count = sum(item["status"] == "conflict" for item in model["enum_groups"])
    return "\n".join(
        [
            "# Extracted contract reference",
            "",
            "This site contains only contracts obtained by static extraction from checked-in software and schema files.",
            "",
            "!!! info \"Extraction scope\"",
            "    FastAPI decorators and frontend calls are parsed from Python/TypeScript. ROS declarations and types are parsed from C++/Python plus `.msg`/`.srv` files. Enums and supported state transitions are parsed from source. Manually curated workflows, components, scenarios, and UI activities are not included.",
            "",
            f"Source digest: `{model['source_digest']}`",
            "",
            "## Runtime-verified example",
            "",
            "The applicable contract pages include payloads from the checked-in [one-robot, one-Point navigation run](examples/single-robot-point-navigation.md). The example is kept separate from static extraction and clearly labels full observations, verified flow data, and abridged route evidence.",
            "",
            "| Extracted contract | Count | Open |",
            "|---|---:|---|",
            f"| HTTP endpoints | {len(nodes_by_kind['http_endpoint'])} | [HTTP API](http/index.md) |",
            f"| ROS topics | {len(nodes_by_kind['ros_topic'])} | [ROS topics](ros-topics/index.md) |",
            f"| ROS services | {len(nodes_by_kind['ros_service'])} | [ROS services](ros-services/index.md) |",
            f"| ROS message/service types | {len(nodes_by_kind['ros_type'])} | [ROS types](ros-types/index.md) |",
            f"| Source enum groups | {len(model['enum_groups'])} ({conflict_count} conflicts) | [Enums](enums/index.md) |",
            f"| Source-parsed state machines | {len(model['state_machines'])} | [States](states/index.md) |",
            f"| JSON Schemas | {len(nodes_by_kind['json_schema'])} | [Schemas](schemas/index.md) |",
            "",
            "## Limitations",
            "",
            "Static extraction can miss names assembled dynamically at runtime. An entry proves that a declaration or definition was found in source; it does not prove that the interface was observed on a running ROS graph.",
        ]
    ) + "\n"


def _group_nodes(nodes: list[dict[str, Any]], key_function: Any) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for node in nodes:
        groups.setdefault(str(key_function(node)), []).append(node)
    return {
        name: sorted(items, key=lambda item: item["label"].lower())
        for name, items in sorted(groups.items(), key=lambda item: item[0].lower())
    }


def _group_overview(title: str, description: str, groups: dict[str, list[dict[str, Any]]], folder: str) -> str:
    lines = [f"# {title}", "", description, "", "| Extracted group | Contracts |", "|---|---:|"]
    for name, nodes in groups.items():
        lines.append(f"| [{_cell(name)}]({folder}/{_slug(name)}.md) | {len(nodes)} |")
    if not groups:
        lines.append("| _None found_ | 0 |")
    return "\n".join(lines) + "\n"


def _ros_namespace_group(node: dict[str, Any]) -> str:
    interface = str((node.get("details") or {}).get("interface") or node["label"]).strip("/")
    parts = [part for part in interface.split("/") if part]
    if not parts:
        return "other"
    if parts[0] == "multi_robot" and len(parts) > 1:
        token = parts[1].split("_", 1)[0]
        return f"/multi_robot/{token}"
    return f"/{parts[0]}"


def _ros_type_group(node: dict[str, Any]) -> str:
    details = node.get("details") or {}
    package = str(details.get("package") or "unknown")
    kind = str(details.get("kind") or "type").upper()
    return f"{package} · {kind}"


def _enum_source_groups(model: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    definitions = {item["id"]: item for item in model["enum_definitions"]}
    groups: dict[str, list[dict[str, Any]]] = {}
    for enum_group in model["enum_groups"]:
        sources = {
            str(definitions[definition_id]["qualified_name"]).split(".", 1)[0]
            for definition_id in enum_group["definitions"]
        }
        for source in sources:
            groups.setdefault(source, []).append(enum_group)
    return {
        name: sorted(items, key=lambda item: item["name"].lower())
        for name, items in sorted(groups.items(), key=lambda item: item[0].lower())
    }


def _node_index(title: str, description: str, nodes: list[dict[str, Any]], link_prefix: str = "") -> str:
    lines = [f"# {title}", "", description, "", "| Contract | Type/details | Evidence |", "|---|---|---|"]
    for node in nodes:
        details = node.get("details") or {}
        detail = details.get("type") or details.get("handler") or node.get("description") or "—"
        lines.append(f"| [{_cell(node['label'])}]({link_prefix}{_node_slug(node)}.md) | `{_cell(detail)}` | {_refs(node.get('source_refs', []))} |")
    if not nodes:
        lines.append("| _None found_ | — | — |")
    return "\n".join(lines) + "\n"


def _interface_page(
    node: dict[str, Any],
    usages: list[dict[str, Any]],
    verified_run: dict[str, Any],
    examples: list[dict[str, Any]],
) -> str:
    details = node.get("details") or {}
    lines = [
        f"# {node['label']}",
        "",
        node.get("description") or "Extracted interface declaration.",
        "",
        "| Property | Extracted value |",
        "|---|---|",
        f"| Kind | `{node['kind']}` |",
    ]
    for key in ("method", "path", "handler", "interface", "type", "package"):
        if details.get(key) not in (None, ""):
            lines.append(f"| {key.replace('_', ' ').title()} | `{_cell(details[key])}` |")
    fields = node.get("fields") or []
    if fields:
        lines.extend(["", "## Fields", "", "| Section | Type | Name |", "|---|---|---|"])
        for field in fields:
            lines.append(f"| {field.get('section', '—')} | `{_cell(field.get('type', ''))}` | `{_cell(field.get('name', ''))}` |")
    if usages:
        lines.extend(["", "## Source usages", "", "| Relationship | Contract | Evidence |", "|---|---|---|"])
        for usage in usages:
            lines.append(f"| {_cell(usage['relationship'])} | `{_cell(usage.get('contract') or '—')}` | {_refs(usage['source_refs'])} |")
    if examples:
        lines.extend(_verified_example_sections(verified_run, examples))
    lines.extend(["", "## Definition evidence", "", _refs_list(node.get("source_refs", []))])
    return "\n".join(lines) + "\n"


def _verified_run_page(run: dict[str, Any], interfaces: list[dict[str, Any]]) -> str:
    verification = run["verification"]
    facts = run["facts"]
    nodes = {item["id"]: item for item in interfaces}
    lines = [
        f"# {run['title']}",
        "",
        "This example is generated from a checked-in runtime verification record and is linked into every extracted contract page that participates in the run.",
        "",
        '!!! success "Runtime verified"',
        f"    {verification['summary']}",
        f"    Source tree: `{verification['source_tree']}` · Stack: `{verification['stack']}` · Evidence: {_refs(verification.get('evidence_refs', []))}",
        "    This run verifies the frozen compatibility reference, not the current editable backend.",
        "",
        "## Fixed run data",
        "",
        "| Value | Runtime data |",
        "|---|---|",
        f"| Mission | `{facts['mission_id']}` |",
        f"| Robot | `{facts['agent_name']}` · `{facts['agent_id']}` |",
        f"| Start | `{facts['start_lon_lat']}` [longitude, latitude] |",
        f"| Destination | `{facts['destination_lon_lat']}` [longitude, latitude] |",
        f"| Behavior | `{facts['behavior']}` (NAVIGATE) |",
        f"| Requested speed | `{facts['requested_speed_mps']} m/s` |",
        f"| Observed route | `{facts['observed_waypoint_count']}` waypoints |",
        "",
        "## Recorded route coordinates",
        "",
        "Only coordinates explicitly retained by the verification walkthrough are shown; the seven unrecorded intermediate points are not invented.",
        "",
        "| Recorded position | Longitude | Latitude |",
        "|---|---:|---:|",
    ]
    route = facts["recorded_route_excerpt_lon_lat"]
    labels = ["first", "second", "final"]
    for label, coordinates in zip(labels, route):
        lines.append(f"| {label} | `{coordinates[0]}` | `{coordinates[1]}` |")
    lines.extend(
        [
            "",
            "## Payloads by phase",
            "",
            "| Phase | Payload | Evidence class | Applicable extracted contracts |",
            "|---|---|---|---|",
        ]
    )
    for example in run.get("examples", []):
        links = []
        for target in example.get("targets", []):
            node = nodes.get(target)
            if node:
                links.append(f"[{_cell(node['label'])}]({_example_target_link(node)})")
            elif target.startswith("schema:"):
                schema_name = target.removeprefix("schema:")
                links.append(f"[{_cell(schema_name)}](../schemas/{_slug(schema_name.replace('.schema.json', ''))}.md)")
        lines.append(
            f"| {_cell(example.get('phase', '—'))} | {_cell(example['title'])} | `{_cell(example.get('sample_kind', 'verified_flow'))}` | {'<br>'.join(links) or '—'} |"
        )
    lines.extend(
        [
            "",
            "## Provenance rules",
            "",
            "- `runtime_observed`: the concrete value was recorded from the running system or its runtime configuration.",
            "- `verified_flow`: the payload follows the exercised runtime path and extracted contract; generated identifiers remain labelled.",
            "- `observed_excerpt`: the checked-in verification retained only part of a larger runtime payload.",
            "",
            f"Example record: {_refs([run['source_ref']])}",
        ]
    )
    return "\n".join(lines) + "\n"


def _example_target_link(node: dict[str, Any]) -> str:
    if node["kind"] == "json_schema":
        schema_name = Path(str((node.get("details") or {}).get("path", ""))).name
        return f"../schemas/{_slug(schema_name.replace('.schema.json', ''))}.md"
    roots = {
        "http_endpoint": "http",
        "ros_topic": "ros-topics",
        "ros_service": "ros-services",
        "ros_type": "ros-types",
    }
    return f"../{roots[node['kind']]}/{_node_slug(node)}.md"


def _verified_example_sections(run: dict[str, Any], examples: list[dict[str, Any]]) -> list[str]:
    lines = [
        "",
        "## Verified one-robot navigation data",
        "",
        f"These payloads come from the [runtime-verified one-robot Point-navigation example](../examples/single-robot-point-navigation.md) using mission `{run['facts']['mission_id']}` and `{run['facts']['agent_name']}`.",
    ]
    for example in examples:
        sample_kind = str(example.get("sample_kind", "verified_flow"))
        admonition = "warning" if sample_kind == "observed_excerpt" else "success"
        lines.extend(
            [
                "",
                f"### {example['title']}",
                "",
                f'!!! {admonition} "{sample_kind.replace("_", " ").title()}"',
                f"    Phase: {example.get('phase', '—')}.",
                "",
                "```json",
                json.dumps(example["payload"], indent=2, ensure_ascii=False),
                "```",
            ]
        )
        notes = example.get("notes", [])
        if notes:
            lines.extend(["", *[f"- {note}" for note in notes]])
        refs = [run["source_ref"], *example.get("evidence_refs", [])]
        lines.extend(["", f"Example evidence: {_refs(refs)}"])
    return lines


def _verified_state_path(run: dict[str, Any], observed_path: list[dict[str, Any]]) -> list[str]:
    lines = [
        "",
        "## State path in the verified navigation run",
        "",
        f"The [one-robot Point-navigation run](../examples/single-robot-point-navigation.md) followed this concrete path:",
        "",
        "```mermaid",
        "flowchart LR",
    ]
    for index, item in enumerate(observed_path):
        lines.append(f"  S{index}[\"{_mermaid_text(item['state'])} ({item['value']})\"]")
        if index:
            lines.append(f"  S{index - 1} -->|{_mermaid_text(item['event'])}| S{index}")
    lines.extend(["```", "", "| Order | State | Value | Runtime event |", "|---:|---|---:|---|"])
    for index, item in enumerate(observed_path, start=1):
        lines.append(f"| {index} | `{item['state']}` | `{item['value']}` | {_cell(item['event'])} |")
    lines.extend(["", f"Example evidence: {_refs([run['source_ref'], *run['verification'].get('evidence_refs', [])])}"])
    return lines


def _verified_enum_usage(
    run: dict[str, Any],
    observed_usage: dict[str, Any],
) -> list[str]:
    lines = [
        "## Values used by the verified navigation run",
        "",
        f"The [one-robot Point-navigation run](../examples/single-robot-point-navigation.md) exercised these values:",
    ]
    if observed_usage.get("definition"):
        lines.extend(["", f"Runtime definition: **{observed_usage['definition']}**."])
    lines.extend([
        "",
        "| Value | Member | Where it appeared |",
        "|---:|---|---|",
    ])
    for item in observed_usage.get("values", []):
        lines.append(f"| `{item['value']}` | `{item['member']}` | {_cell(item['when'])} |")
    lines.extend(["", f"Example evidence: {_refs([run['source_ref'], *run['verification'].get('evidence_refs', [])])}", ""])
    return lines


def _states_index(machines: list[dict[str, Any]]) -> str:
    lines = [
        "# Source-parsed state machines",
        "",
        "Only transitions parsed from explicit source patterns are included.",
        "",
        "| State machine | States | Parsed transitions |",
        "|---|---:|---:|",
    ]
    for machine in machines:
        lines.append(f"| [{machine['name']}]({_slug(machine['id'])}.md) | {len(machine['states'])} | {len(machine['transitions'])} |")
    return "\n".join(lines) + "\n"


def _state_machine_page(
    machine: dict[str, Any],
    verified_run: dict[str, Any],
    observed_path: list[dict[str, Any]],
) -> str:
    lines = [f"# {machine['name']}", "", machine["description"], "", "```mermaid", "stateDiagram-v2"]
    if "ANY" in {item["from"] for item in machine["transitions"]}:
        lines.append('  state "Any current state" as N_ANY')
    for state in machine["states"]:
        lines.append(f"  state \"{_mermaid_text(state['name'])} ({state['value']})\" as {_mermaid_id(state['name'])}")
    for transition in machine["transitions"]:
        if transition["from"] != transition["to"]:
            lines.append(f"  {_mermaid_id(transition['from'])} --> {_mermaid_id(transition['to'])}: {_mermaid_text(transition['trigger'])}")
    lines.extend(["```", "", "## Extracted state values", "", "| Value | State | Source description |", "|---:|---|---|"])
    for state in sorted(machine["states"], key=lambda item: (isinstance(item["value"], str), item["value"])):
        lines.append(f"| `{state['value']}` | `{state['name']}` | {_cell(state.get('description') or '')} |")
    lines.extend(["", "## Extracted transitions", "", "| From | Trigger | To | Evidence |", "|---|---|---|---|"])
    for transition in machine["transitions"]:
        lines.append(f"| `{transition['from']}` | {_cell(transition['trigger'])} | `{transition['to']}` | {_refs([transition['source_ref']])} |")
    if machine.get("request_mappings"):
        lines.extend(["", "## Extracted request mapping", "", "| Request | Resulting state | Evidence |", "|---|---|---|"])
        for mapping in machine["request_mappings"]:
            lines.append(f"| `{mapping['request']}` | `{mapping['state']}` | {_refs([mapping['source_ref']])} |")
    if observed_path:
        lines.extend(_verified_state_path(verified_run, observed_path))
    return "\n".join(lines) + "\n"


def _enums_index(model: dict[str, Any], source_groups: dict[str, list[dict[str, Any]]]) -> str:
    lines = [
        "# Source enum registry",
        "",
        "Enum declarations are extracted from Python and C++ source. Same-name declarations are compared by member/value signature.",
        "",
        "## By extracted source namespace",
        "",
        "| Source | Enum groups |",
        "|---|---:|",
    ]
    for source, groups in source_groups.items():
        lines.append(f"| [{source}](sources/{_slug(source)}.md) | {len(groups)} |")
    lines.extend(["", "## Conflicts", "", "| Enum | Definitions | Variants |", "|---|---:|---:|"])
    for group in model["enum_groups"]:
        if group["status"] == "conflict":
            lines.append(f"| [{group['name']}]({_slug(group['name'])}.md) | {group['definition_count']} | {group['variant_count']} |")
    if not any(group["status"] == "conflict" for group in model["enum_groups"]):
        lines.append("| _No conflicts_ | — | — |")
    return "\n".join(lines) + "\n"


def _enum_source_page(source_name: str, groups: list[dict[str, Any]]) -> str:
    lines = [
        f"# Enums · {source_name}",
        "",
        "Enum groups with at least one definition in this extracted source namespace.",
        "",
        "| Enum | Comparison | Definitions |",
        "|---|---|---:|",
    ]
    for group in groups:
        status = "⚠ conflict" if group["status"] == "conflict" else "consistent"
        lines.append(f"| [{group['name']}](../{_slug(group['name'])}.md) | {status} | {group['definition_count']} |")
    return "\n".join(lines) + "\n"


def _enum_page(
    group: dict[str, Any],
    definitions: dict[str, dict[str, Any]],
    verified_run: dict[str, Any],
    observed_usage: dict[str, Any] | None,
) -> str:
    lines = [f"# {group['name']}", ""]
    if group["status"] == "conflict":
        lines.extend(["!!! warning \"Conflicting extracted definitions\"", f"    {group['variant_count']} member/value signatures were found.", ""])
    for definition_id in group["definitions"]:
        item = definitions[definition_id]
        lines.extend(
            [
                f"## {item['qualified_name']}",
                "",
                f"Language: **{item['language']}** · Evidence: {_refs([item['source_ref']])}",
                "",
                "| Value | Member | Source comment |",
                "|---:|---|---|",
            ]
        )
        for member in item["members"]:
            lines.append(f"| `{member['value']}` | `{member['name']}` | {_cell(member.get('description') or '')} |")
        lines.append("")
    if observed_usage:
        lines.extend(_verified_enum_usage(verified_run, observed_usage))
    return "\n".join(lines) + "\n"


def _schemas_index(repo_root: Path) -> str:
    lines = ["# JSON Schemas", "", "Schema pages are generated directly from `schemas/*.schema.json`.", "", "| Schema | Title | Required top-level fields |", "|---|---|---|"]
    for path in sorted((repo_root / "schemas").glob("*.schema.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        slug = _slug(path.stem.replace(".schema", ""))
        lines.append(f"| [{path.name}]({slug}.md) | {_cell(payload.get('title', path.stem))} | {_cell(', '.join(payload.get('required', [])) or '—')} |")
    return "\n".join(lines) + "\n"


def _schema_page(
    repo_root: Path,
    path: Path,
    verified_run: dict[str, Any],
    examples: list[dict[str, Any]],
) -> str:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = _flatten_schema(payload)
    relative = str(path.relative_to(repo_root))
    lines = [
        f"# {payload.get('title', path.stem)}",
        "",
        f"Extracted from `{relative}` · {_refs([{'path': relative, 'line': 1}])}",
        "",
        "| JSON path | Type | Required | Constraints / description |",
        "|---|---|---|---|",
    ]
    for row in rows:
        lines.append(f"| `{_cell(row['path'])}` | `{_cell(row['type'])}` | {row['required']} | {_cell(row['details'])} |")
    if examples:
        lines.extend(_verified_example_sections(verified_run, examples))
    lines.extend(["", "## Complete extracted schema", "", "```json", json.dumps(payload, indent=2, ensure_ascii=False), "```"])
    return "\n".join(lines) + "\n"


def _flatten_schema(schema: dict[str, Any], prefix: str = "$", required: bool = True) -> list[dict[str, str]]:
    kind = schema.get("type") or ("$ref" if "$ref" in schema else "union" if "oneOf" in schema or "anyOf" in schema else "object")
    details: list[str] = []
    for key in ("description", "format", "pattern", "minimum", "maximum", "minItems", "maxItems", "$ref"):
        if key in schema:
            details.append(f"{key}: {schema[key]}")
    if "enum" in schema:
        details.append("enum: " + ", ".join(map(str, schema["enum"])))
    rows = [{"path": prefix, "type": str(kind), "required": "yes" if required else "no", "details": "; ".join(details)}]
    required_names = set(schema.get("required", []))
    for name, child in (schema.get("properties") or {}).items():
        if isinstance(child, dict):
            rows.extend(_flatten_schema(child, f"{prefix}.{name}", name in required_names))
    if isinstance(schema.get("items"), dict):
        rows.extend(_flatten_schema(schema["items"], f"{prefix}[]", True))
    for branch_key in ("oneOf", "anyOf", "allOf"):
        for index, child in enumerate(schema.get(branch_key) or [], start=1):
            if isinstance(child, dict):
                rows.extend(_flatten_schema(child, f"{prefix}<{branch_key}:{index}>", required))
    return rows


def _node_slug(node: dict[str, Any]) -> str:
    details = node.get("details") or {}
    if node["kind"] == "http_endpoint":
        return _slug(f"{details.get('method', '')}-{details.get('path', node['label'])}")
    return _slug(str(details.get("interface") or node["label"]))


def _refs(refs: list[dict[str, Any]]) -> str:
    refs = _dedupe_refs(refs)
    return ", ".join(_ref_link(ref) for ref in refs) if refs else "—"


def _refs_list(refs: list[dict[str, Any]]) -> str:
    refs = _dedupe_refs(refs)
    return "\n".join(f"- {_ref_link(ref)}" for ref in refs) or "_No source reference found._"


def _ref_link(ref: dict[str, Any]) -> str:
    path = str(ref.get("path", "unknown"))
    line = int(ref.get("line", 1))
    return f"[`{path}:{line}`]({REPOSITORY_URL}/blob/main/{path}#L{line})"


def _dedupe_refs(refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[tuple[str, int], dict[str, Any]] = {}
    for ref in refs:
        key = (str(ref.get("path", "")), int(ref.get("line", 1)))
        deduped[key] = {"path": key[0], "line": key[1]}
    return list(deduped.values())


def _cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _mermaid_id(value: str) -> str:
    return "N_" + re.sub(r"[^A-Za-z0-9_]", "_", value)


def _mermaid_text(value: str) -> str:
    return str(value).replace('"', "'").replace("\n", " ")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate or verify the source-extracted C2 contract reference.")
    parser.add_argument("command", choices=("generate", "check"), nargs="?", default="generate")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)
    if args.command == "generate":
        written = generate_contract_documents(args.repo_root, args.output_dir)
        print(f"Generated {len(written)} extracted contract reference files.")
        return 0
    problems = check_contract_documents(args.repo_root, args.output_dir)
    if problems:
        print("Generated contract reference is stale:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        print("Run: python -m c2_imugs2.contracts.docs generate", file=sys.stderr)
        return 1
    print("Generated extracted contract reference is current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
