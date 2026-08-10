from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

from .contract_inventory import build_contract_inventory
from .contracts import build_contract_graph


REPOSITORY_URL = "https://github.com/LEBaz2211/C2_imugs2"
EXTRACTED_NODE_KINDS = {"http_endpoint", "ros_topic", "ros_service", "ros_type", "json_schema"}
EXTRACTED_USAGE_KINDS = {"http_handler", "http_call", "ros_usage"}
EXTRACTED_STATE_MACHINES = {"mission_lifecycle", "edge_task_lifecycle"}


def build_contract_model(repo_root: Path) -> dict[str, Any]:
    """Return only contracts obtained from static source/config extraction."""

    raw_graph = build_contract_graph(repo_root, runtime={})
    inventory = build_contract_inventory(repo_root)
    nodes = [item for item in raw_graph["nodes"] if item["kind"] in EXTRACTED_NODE_KINDS]
    node_ids = {item["id"] for item in nodes}
    usages: list[dict[str, Any]] = []
    for edge in raw_graph["edges"]:
        if edge["kind"] not in EXTRACTED_USAGE_KINDS or not edge.get("source_refs"):
            continue
        interface_id = edge["source"] if edge["source"] in node_ids else edge["target"] if edge["target"] in node_ids else None
        if not interface_id:
            continue
        usages.append(
            {
                "id": edge["id"],
                "interface_id": interface_id,
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
    return {
        "schema_version": 2,
        "catalog_kind": "static_source_extraction",
        "canonical_source_tree": "backend",
        "source_digest": raw_graph["source_digest"],
        "interfaces": sorted(nodes, key=lambda item: (item["kind"], item["label"])),
        "usages": sorted(usages, key=lambda item: (item["interface_id"], item["relationship"], item["id"])),
        "enum_definitions": inventory["enum_definitions"],
        "enum_groups": inventory["enum_groups"],
        "state_machines": state_machines,
    }


def render_contract_documents(repo_root: Path) -> dict[str, str]:
    model = build_contract_model(repo_root)
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
        "index.md": _overview(model, nodes_by_kind),
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
            documents[f"{page_root}/{_node_slug(node)}.md"] = _interface_page(node, usages_by_interface.get(node["id"], []))
    for group_name, nodes in http_groups.items():
        documents[f"http/methods/{_slug(group_name)}.md"] = _node_index(f"HTTP {group_name}", "Routes extracted from FastAPI decorators.", nodes, "../")
    for group_name, nodes in topic_groups.items():
        documents[f"ros-topics/groups/{_slug(group_name)}.md"] = _node_index(f"ROS topics · {group_name}", "Topic declarations in this extracted namespace group.", nodes, "../")
    for group_name, nodes in service_groups.items():
        documents[f"ros-services/groups/{_slug(group_name)}.md"] = _node_index(f"ROS services · {group_name}", "Service declarations in this extracted namespace group.", nodes, "../")
    for group_name, nodes in type_groups.items():
        documents[f"ros-types/packages/{_slug(group_name)}.md"] = _node_index(f"ROS types · {group_name}", "IDL definitions in this extracted package/type group.", nodes, "../")
    for machine in model["state_machines"]:
        documents[f"states/{_slug(machine['id'])}.md"] = _state_machine_page(machine)
    definitions = {item["id"]: item for item in model["enum_definitions"]}
    for group in model["enum_groups"]:
        documents[f"enums/{_slug(group['name'])}.md"] = _enum_page(group, definitions)
    for source_name, groups in enum_source_groups.items():
        documents[f"enums/sources/{_slug(source_name)}.md"] = _enum_source_page(source_name, groups)
    for schema_path in sorted((repo_root / "schemas").glob("*.schema.json")):
        documents[f"schemas/{_slug(schema_path.stem.replace('.schema', ''))}.md"] = _schema_page(repo_root, schema_path)
    return documents


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
    """Build grouped MkDocs navigation from the same extracted catalog."""

    model = build_contract_model(repo_root)
    by_kind = {
        kind: [item for item in model["interfaces"] if item["kind"] == kind]
        for kind in EXTRACTED_NODE_KINDS
    }
    http_groups = _group_nodes(by_kind["http_endpoint"], lambda node: str((node.get("details") or {}).get("method") or "OTHER"))
    topic_groups = _group_nodes(by_kind["ros_topic"], _ros_namespace_group)
    service_groups = _group_nodes(by_kind["ros_service"], _ros_namespace_group)
    type_groups = _group_nodes(by_kind["ros_type"], _ros_type_group)
    enum_sources = _enum_source_groups(model)
    schemas = []
    for path in sorted((repo_root / "schemas").glob("*.schema.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        schemas.append({str(payload.get("title") or path.stem): f"schemas/{_slug(path.stem.replace('.schema', ''))}.md"})
    return [
        {"Overview": "index.md"},
        {
            "HTTP API": [
                {"Overview": "http/index.md"},
                *[{f"{name} ({len(nodes)})": f"http/methods/{_slug(name)}.md"} for name, nodes in http_groups.items()],
            ]
        },
        {
            "ROS topics": [
                {"Overview": "ros-topics/index.md"},
                *[{f"{name} ({len(nodes)})": f"ros-topics/groups/{_slug(name)}.md"} for name, nodes in topic_groups.items()],
            ]
        },
        {
            "ROS services": [
                {"Overview": "ros-services/index.md"},
                *[{f"{name} ({len(nodes)})": f"ros-services/groups/{_slug(name)}.md"} for name, nodes in service_groups.items()],
            ]
        },
        {
            "ROS types": [
                {"Overview": "ros-types/index.md"},
                *[{f"{name} ({len(nodes)})": f"ros-types/packages/{_slug(name)}.md"} for name, nodes in type_groups.items()],
            ]
        },
        {
            "States": [
                {"Overview": "states/index.md"},
                *[{machine["name"]: f"states/{_slug(machine['id'])}.md"} for machine in model["state_machines"]],
            ]
        },
        {
            "Enums": [
                {"Overview": "enums/index.md"},
                *[{f"{name} ({len(groups)})": f"enums/sources/{_slug(name)}.md"} for name, groups in enum_sources.items()],
            ]
        },
        {"JSON Schemas": [{"Overview": "schemas/index.md"}, *schemas]},
    ]


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


def _interface_page(node: dict[str, Any], usages: list[dict[str, Any]]) -> str:
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
    lines.extend(["", "## Definition evidence", "", _refs_list(node.get("source_refs", []))])
    return "\n".join(lines) + "\n"


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


def _state_machine_page(machine: dict[str, Any]) -> str:
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


def _enum_page(group: dict[str, Any], definitions: dict[str, dict[str, Any]]) -> str:
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
    return "\n".join(lines) + "\n"


def _schemas_index(repo_root: Path) -> str:
    lines = ["# JSON Schemas", "", "Schema pages are generated directly from `schemas/*.schema.json`.", "", "| Schema | Title | Required top-level fields |", "|---|---|---|"]
    for path in sorted((repo_root / "schemas").glob("*.schema.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        slug = _slug(path.stem.replace(".schema", ""))
        lines.append(f"| [{path.name}]({slug}.md) | {_cell(payload.get('title', path.stem))} | {_cell(', '.join(payload.get('required', [])) or '—')} |")
    return "\n".join(lines) + "\n"


def _schema_page(repo_root: Path, path: Path) -> str:
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
        print("Run: python -m c2_imugs2.contract_docs generate", file=sys.stderr)
        return 1
    print("Generated extracted contract reference is current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
