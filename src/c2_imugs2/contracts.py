from __future__ import annotations

import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any


HTTP_METHODS = {"get", "post", "put", "patch", "delete"}
ROS_CALL_KIND = {
    "publisher": "publishes",
    "subscription": "subscribes",
    "service": "provides",
    "client": "calls",
}


def build_contract_graph(repo_root: Path, runtime: dict[str, Any] | None = None) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    runtime = runtime or {}
    source_files = _contract_source_files(repo_root)
    idl_catalog = _parse_ros_idl(repo_root)
    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[str, dict[str, Any]] = {}

    for node in _base_nodes():
        nodes[node["id"]] = node

    _add_http_contracts(repo_root, nodes, edges)
    _add_ros_idl_nodes(repo_root, idl_catalog, nodes)
    _add_ros_usage_edges(repo_root, idl_catalog, nodes, edges, runtime)
    _add_schema_nodes(repo_root, nodes, edges)
    _add_compose_nodes(repo_root, nodes, edges)
    _add_mongo_contracts(repo_root, nodes, edges)
    _add_system_edges(edges)

    for node in nodes.values():
        if node["kind"] in {"ros_topic", "ros_service"}:
            _apply_runtime_status(node, runtime)

    edge_values = sorted(edges.values(), key=lambda item: (item.get("layer", ""), item.get("label", ""), item.get("id", "")))
    node_values = sorted(nodes.values(), key=lambda item: (item.get("layer", ""), item.get("kind", ""), item.get("label", "")))
    scenarios = _scenario_contracts(repo_root)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_digest": _source_digest(source_files),
        "source_file_count": len(source_files),
        "summary": {
            "nodes": len(node_values),
            "edges": len(edge_values),
            "scenarios": len(scenarios),
            "by_layer": dict(Counter(item.get("layer", "unknown") for item in node_values)),
            "by_kind": dict(Counter(item.get("kind", "unknown") for item in node_values)),
        },
        "layers": [
            {"id": "system", "label": "System"},
            {"id": "http", "label": "HTTP/API"},
            {"id": "ros", "label": "ROS"},
            {"id": "data", "label": "Data"},
            {"id": "scenario", "label": "Scenarios"},
        ],
        "nodes": node_values,
        "edges": edge_values,
        "scenarios": scenarios,
        "runtime": {
            "ros_nodes": runtime.get("nodes", []),
            "ros_topics": runtime.get("topics", []),
            "ros_services": runtime.get("services", []),
        },
    }


def _base_nodes() -> list[dict[str, Any]]:
    return [
        _node("component:ui", "Browser UI", "component", "system", "React/Vite/Leaflet mission surface"),
        _node("component:api", "FastAPI Adapter", "component", "system", "UI-facing adapter and legacy normalizer"),
        _node("component:c2_rest", "Old REST Bridge", "component", "system", "C++ HTTP bridge to C2 ROS topics"),
        _node("component:centralized", "Centralized Coordination", "component", "system", "C2 interface, orchestrator, mission and fleet managers"),
        _node("component:planner", "Legacy Planner", "component", "system", "Actual ROS planner node and path planning library"),
        _node("component:fleet", "Fleet Manager", "component", "system", "Agent registry and edge task dispatcher"),
        _node("component:edge", "Edge Supervisor", "component", "system", "Per-agent task supervisor and autonomy adapter"),
        _node("component:autonomy", "Autonomy Sim", "component", "system", "Themis Fr autonomy simulation"),
        _node("component:rosbridge", "rosbridge", "component", "system", "WebSocket ROS introspection and topic reader"),
        _node("component:mongodb", "MongoDB", "component", "data", "Legacy RuntimeDB and MapDB persistence"),
        _node("component:schemas", "JSON Schemas", "component", "data", "Canonical replacement contract schemas"),
    ]


def _node(node_id: str, label: str, kind: str, layer: str, description: str = "", **extra: Any) -> dict[str, Any]:
    return {
        "id": node_id,
        "label": label,
        "kind": kind,
        "layer": layer,
        "description": description,
        "source_refs": [],
        **extra,
    }


def _edge(edge_id: str, source: str, target: str, label: str, kind: str, layer: str, **extra: Any) -> dict[str, Any]:
    return {
        "id": edge_id,
        "source": source,
        "target": target,
        "label": label,
        "kind": kind,
        "layer": layer,
        "source_refs": [],
        "fields": [],
        "notes": [],
        **extra,
    }


def _contract_source_files(repo_root: Path) -> list[Path]:
    roots = [
        repo_root / "src" / "c2_imugs2",
        repo_root / "frontend" / "src",
        repo_root / "schemas",
        repo_root / "legacy_ros" / "fog",
        repo_root / "legacy_ros" / "edge",
    ]
    files: list[Path] = [repo_root / "docker-compose.yml", repo_root / "docker-compose.legacy-ros.yml"]
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.suffix.lower() in {".py", ".ts", ".tsx", ".cpp", ".hpp", ".h", ".msg", ".srv", ".json", ".yaml", ".yml"}:
                files.append(path)
    return sorted({path.resolve() for path in files if path.exists()})


def _source_digest(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(str(path).encode("utf-8"))
        try:
            digest.update(path.read_bytes())
        except OSError:
            continue
    return digest.hexdigest()[:16]


def _add_http_contracts(repo_root: Path, nodes: dict[str, dict[str, Any]], edges: dict[str, dict[str, Any]]) -> None:
    api_path = repo_root / "src" / "c2_imugs2" / "api.py"
    for route in _fastapi_routes(api_path, repo_root):
        node_id = f"http:{route['method']} {route['path']}"
        nodes[node_id] = _node(
            node_id,
            f"{route['method']} {route['path']}",
            "http_endpoint",
            "http",
            f"FastAPI handler `{route['handler']}`",
            source_refs=[route["source_ref"]],
            details={"handler": route["handler"], "method": route["method"], "path": route["path"]},
        )
        edges[f"http-server:{node_id}"] = _edge(
            f"http-server:{node_id}",
            node_id,
            "component:api",
            f"handled by {route['handler']}",
            "http_handler",
            "http",
            protocol="HTTP",
            source_refs=[route["source_ref"]],
        )

    frontend_path = repo_root / "frontend" / "src" / "api.ts"
    for call in _frontend_api_calls(frontend_path, repo_root):
        node_id = _match_http_endpoint_node(nodes, call["method"], call["path"]) or f"http:{call['method']} {call['path']}"
        if node_id not in nodes:
            nodes[node_id] = _node(
                node_id,
                f"{call['method']} {call['path']}",
                "http_endpoint",
                "http",
                "Frontend API call without a matching static FastAPI route",
                source_refs=[call["source_ref"]],
                details={"method": call["method"], "path": call["path"]},
            )
        edges[f"http-client:{call['function']}:{node_id}"] = _edge(
            f"http-client:{call['function']}:{node_id}",
            "component:ui",
            node_id,
            call["function"],
            "http_call",
            "http",
            protocol="HTTP",
            method=call["method"],
            source_refs=[call["source_ref"]],
        )


def _fastapi_routes(path: Path, repo_root: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    tree = ast.parse(path.read_text(encoding="utf-8"))
    routes: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                continue
            method = decorator.func.attr.lower()
            if method not in HTTP_METHODS:
                continue
            if not decorator.args or not isinstance(decorator.args[0], ast.Constant):
                continue
            route_path = decorator.args[0].value
            if isinstance(route_path, str) and route_path.startswith("/api/"):
                routes.append(
                    {
                        "method": method.upper(),
                        "path": route_path,
                        "handler": node.name,
                        "source_ref": _source_ref(path, repo_root, node.lineno),
                    }
                )
    return routes


def _frontend_api_calls(path: Path, repo_root: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    calls: list[dict[str, Any]] = []
    function_pattern = re.compile(r"export\s+async\s+function\s+(\w+)\s*\([^)]*\)[^{]*\{(?P<body>.*?)\n\}", re.S)
    call_pattern = re.compile(r"\b(getJson|postJson|putJson|deleteJson)\s*\(\s*([`\"'])(?P<path>/api/.*?)(?:\2|[`\"'])", re.S)
    method_map = {"getJson": "GET", "postJson": "POST", "putJson": "PUT", "deleteJson": "DELETE"}
    for function_match in function_pattern.finditer(text):
        body = function_match.group("body")
        for call_match in call_pattern.finditer(body):
            raw_path = call_match.group("path").replace("\n", "").strip()
            source_index = function_match.start() + call_match.start()
            calls.append(
                {
                    "function": function_match.group(1),
                    "method": method_map[call_match.group(1)],
                    "path": raw_path,
                    "source_ref": _source_ref(path, repo_root, text[:source_index].count("\n") + 1),
                }
            )
    return calls


def _match_http_endpoint_node(nodes: dict[str, dict[str, Any]], method: str, call_path: str) -> str | None:
    call_base = call_path.split("?", 1)[0]
    call_pattern = re.sub(r"\$\{[^}]+\}", "{param}", call_base)
    for node_id, node in nodes.items():
        details = node.get("details") or {}
        if details.get("method") != method:
            continue
        route = str(details.get("path") or "")
        route_pattern = re.sub(r"\{[^}]+\}", "{param}", route)
        if call_pattern == route_pattern or call_base == route:
            return node_id
    return None


def _parse_ros_idl(repo_root: Path) -> dict[str, dict[str, Any]]:
    catalog: dict[str, dict[str, Any]] = {}
    for path in sorted((repo_root / "legacy_ros").rglob("*")):
        if path.suffix not in {".msg", ".srv"} or "message_packages" not in path.parts:
            continue
        try:
            package = path.parts[path.parts.index("message_packages") + 1]
        except (ValueError, IndexError):
            continue
        kind = "srv" if path.suffix == ".srv" else "msg"
        type_name = f"{package}/{kind}/{path.stem}"
        text = path.read_text(encoding="utf-8")
        entry = {
            "type": type_name,
            "package": package,
            "kind": kind,
            "name": path.stem,
            "path": _relative(path, repo_root),
            "source_ref": _source_ref(path, repo_root, 1),
            "fields": _parse_idl_fields(text, kind),
        }
        catalog[type_name] = entry
    catalog.setdefault(
        "std_msgs/msg/String",
        {
            "type": "std_msgs/msg/String",
            "package": "std_msgs",
            "kind": "msg",
            "name": "String",
            "path": "external:std_msgs",
            "source_ref": {"path": "external:std_msgs", "line": 1},
            "fields": [{"section": "message", "type": "string", "name": "data"}],
        },
    )
    return catalog


def _parse_idl_fields(text: str, kind: str) -> list[dict[str, str]]:
    section = "request" if kind == "srv" else "message"
    fields: list[dict[str, str]] = []
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if line == "---":
            section = "response"
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        fields.append({"section": section, "type": parts[0], "name": parts[1]})
    return fields


def _add_ros_idl_nodes(repo_root: Path, idl_catalog: dict[str, dict[str, Any]], nodes: dict[str, dict[str, Any]]) -> None:
    for type_name, entry in idl_catalog.items():
        if entry["path"].startswith("external:"):
            continue
        node_id = f"ros_type:{type_name}"
        nodes[node_id] = _node(
            node_id,
            type_name,
            "ros_type",
            "ros",
            f"{entry['kind'].upper()} definition from `{entry['package']}`",
            source_refs=[entry["source_ref"]],
            fields=entry["fields"],
            details={"package": entry["package"], "kind": entry["kind"], "path": entry["path"]},
        )


def _add_ros_usage_edges(
    repo_root: Path,
    idl_catalog: dict[str, dict[str, Any]],
    nodes: dict[str, dict[str, Any]],
    edges: dict[str, dict[str, Any]],
    runtime: dict[str, Any],
) -> None:
    for usage in _ros_usages(repo_root):
        component = _component_for_path(usage["path"])
        if component not in nodes:
            continue
        interface = usage["name"]
        if usage["kind"] in {"publisher", "subscription"}:
            node_id = f"ros:topic:{interface}"
            kind = "ros_topic"
            label = interface
            protocol = "ROS topic"
            source, target = (component, node_id) if usage["kind"] == "publisher" else (node_id, component)
        else:
            node_id = f"ros:service:{interface}"
            kind = "ros_service"
            label = interface
            protocol = "ROS service"
            source, target = (component, node_id)

        type_name = _resolve_ros_type(usage["type"], idl_catalog)
        if node_id not in nodes:
            nodes[node_id] = _node(
                node_id,
                label,
                kind,
                "ros",
                f"{protocol} `{interface}`",
                source_refs=[],
                details={"interface": interface, "type": type_name or usage["type"]},
            )
        nodes[node_id].setdefault("source_refs", []).append(usage["source_ref"])
        if type_name:
            fields = idl_catalog.get(type_name, {}).get("fields", [])
            nodes[node_id].setdefault("fields", fields)
            edges[f"ros-type:{node_id}:{type_name}"] = _edge(
                f"ros-type:{node_id}:{type_name}",
                node_id,
                f"ros_type:{type_name}",
                "uses type",
                "ros_type_link",
                "ros",
                protocol=protocol,
                fields=fields,
            )

        edge_id = f"ros-usage:{usage['kind']}:{interface}:{usage['path']}:{usage['line']}"
        edges[edge_id] = _edge(
            edge_id,
            source,
            target,
            ROS_CALL_KIND[usage["kind"]],
            "ros_usage",
            "ros",
            protocol=protocol,
            direction=ROS_CALL_KIND[usage["kind"]],
            contract=type_name or usage["type"],
            fields=idl_catalog.get(type_name or "", {}).get("fields", []),
            source_refs=[usage["source_ref"]],
        )


def _ros_usages(repo_root: Path) -> list[dict[str, Any]]:
    usages: list[dict[str, Any]] = []
    roots = [repo_root / "legacy_ros", repo_root / "src" / "c2_imugs2"]
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.suffix == ".py":
                usages.extend(_python_ros_usages(path, repo_root))
            elif path.suffix in {".cpp", ".hpp", ".h"}:
                usages.extend(_cpp_ros_usages(path, repo_root))
    return usages


def _python_ros_usages(path: Path, repo_root: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    usages: list[dict[str, Any]] = []
    pattern = re.compile(r"create_(publisher|subscription|service)\s*\(\s*([A-Za-z0-9_\.]+)\s*,\s*['\"]([^'\"]+)['\"]", re.S)
    for match in pattern.finditer(text):
        usages.append(
            {
                "kind": match.group(1),
                "type": match.group(2).split(".")[-1],
                "name": match.group(3),
                "path": _relative(path, repo_root),
                "line": text[: match.start()].count("\n") + 1,
                "source_ref": _source_ref(path, repo_root, text[: match.start()].count("\n") + 1),
            }
        )
    return usages


def _cpp_ros_usages(path: Path, repo_root: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    usages: list[dict[str, Any]] = []
    pattern = re.compile(r"create_(publisher|subscription|service|client)<([^>]+)>\s*\(\s*\"([^\"]+)\"", re.S)
    for match in pattern.finditer(text):
        usages.append(
            {
                "kind": match.group(1),
                "type": match.group(2).strip(),
                "name": match.group(3),
                "path": _relative(path, repo_root),
                "line": text[: match.start()].count("\n") + 1,
                "source_ref": _source_ref(path, repo_root, text[: match.start()].count("\n") + 1),
            }
        )
    return usages


def _resolve_ros_type(raw_type: str, idl_catalog: dict[str, dict[str, Any]]) -> str | None:
    normalized = raw_type.strip().replace("::", "/")
    normalized = normalized.replace("<", "").replace(">", "")
    if normalized in idl_catalog:
        return normalized
    if normalized in {"String", "std_msgs/msg/String"}:
        return "std_msgs/msg/String"
    base = normalized.split("/")[-1].split(".")[-1]
    matches = [type_name for type_name in idl_catalog if type_name.endswith(f"/{base}")]
    if len(matches) == 1:
        return matches[0]
    for preferred in ("c2_msgs", "centralized_msgs", "task_msgs", "autonomy_msgs"):
        package_matches = [type_name for type_name in matches if type_name.startswith(f"{preferred}/")]
        if package_matches:
            return package_matches[0]
    return None


def _add_schema_nodes(repo_root: Path, nodes: dict[str, dict[str, Any]], edges: dict[str, dict[str, Any]]) -> None:
    schema_root = repo_root / "schemas"
    for path in sorted(schema_root.glob("*.schema.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        title = str(payload.get("title") or path.stem)
        node_id = f"schema:{path.name}"
        nodes[node_id] = _node(
            node_id,
            title,
            "json_schema",
            "data",
            f"Canonical JSON schema `{path.name}`",
            source_refs=[_source_ref(path, repo_root, 1)],
            fields=_schema_fields(payload),
            details={"required": payload.get("required", []), "path": _relative(path, repo_root)},
        )
        edges[f"schema-owner:{node_id}"] = _edge(
            f"schema-owner:{node_id}",
            "component:schemas",
            node_id,
            "defines",
            "schema_definition",
            "data",
            protocol="JSON Schema",
            source_refs=[_source_ref(path, repo_root, 1)],
        )


def _schema_fields(payload: dict[str, Any]) -> list[dict[str, str]]:
    fields = []
    properties = payload.get("properties")
    if isinstance(properties, dict):
        required = set(payload.get("required", []))
        for name, value in properties.items():
            kind = value.get("type") if isinstance(value, dict) else "unknown"
            fields.append({"name": name, "type": str(kind), "section": "required" if name in required else "optional"})
    return fields


def _add_compose_nodes(repo_root: Path, nodes: dict[str, dict[str, Any]], edges: dict[str, dict[str, Any]]) -> None:
    for compose_path in [repo_root / "docker-compose.yml", repo_root / "docker-compose.legacy-ros.yml"]:
        if not compose_path.exists():
            continue
        services = _compose_services(compose_path)
        for service in services:
            node_id = f"container:{service['name']}"
            component = _component_for_compose_service(service["name"])
            nodes[node_id] = _node(
                node_id,
                service["name"],
                "container",
                "system",
                service.get("command") or "Docker Compose service",
                source_refs=[_source_ref(compose_path, repo_root, service["line"])],
                details=service,
            )
            if component:
                edges[f"container-component:{service['name']}"] = _edge(
                    f"container-component:{service['name']}",
                    node_id,
                    component,
                    "runs",
                    "deployment",
                    "system",
                    protocol="Docker Compose",
                    source_refs=[_source_ref(compose_path, repo_root, service["line"])],
                )


def _compose_services(path: Path) -> list[dict[str, Any]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    services: list[dict[str, Any]] = []
    in_services = False
    current: dict[str, Any] | None = None
    for index, line in enumerate(lines, start=1):
        if line.strip() == "services:":
            in_services = True
            current = None
            continue
        if not in_services:
            continue
        service_match = re.match(r"^  ([A-Za-z0-9_.-]+):\s*$", line)
        if service_match:
            current = {"name": service_match.group(1), "line": index}
            services.append(current)
            continue
        if current is None:
            continue
        if line.startswith("    command:"):
            current["command"] = line.split("command:", 1)[1].strip()
        if line.startswith("    container_name:"):
            current["container_name"] = line.split("container_name:", 1)[1].strip()
    return services


def _add_mongo_contracts(repo_root: Path, nodes: dict[str, dict[str, Any]], edges: dict[str, dict[str, Any]]) -> None:
    collections = {
        "RuntimeDB.MissionConfig": "Mission configuration stored by legacy C2/mission manager",
        "RuntimeDB.Planning": "Raw planner result JSON persisted by mission manager",
        "RuntimeDB.MissionFeedback": "Mission feedback emitted back to C2/UI",
        "RuntimeDB.Logs": "Legacy swarm and planner log records",
        "MapDB.features": "Optional planner map feature collection",
    }
    for name, description in collections.items():
        node_id = f"mongo:{name}"
        nodes[node_id] = _node(node_id, name, "mongo_collection", "data", description)
        edges[f"mongo-owner:{name}"] = _edge(
            f"mongo-owner:{name}",
            "component:mongodb",
            node_id,
            "stores",
            "persistence",
            "data",
            protocol="MongoDB",
        )
    source_refs = [_source_ref(repo_root / "src" / "c2_imugs2" / "api.py", repo_root, 455)]
    for collection in ("RuntimeDB.MissionConfig", "RuntimeDB.Planning", "RuntimeDB.MissionFeedback", "RuntimeDB.Logs"):
        edges[f"api-reads-mongo:{collection}"] = _edge(
            f"api-reads-mongo:{collection}",
            f"mongo:{collection}",
            "component:api",
            "diagnostic read",
            "mongo_read",
            "data",
            protocol="MongoDB",
            source_refs=source_refs,
        )
    planner_ref = _source_ref(repo_root / "legacy_ros" / "fog" / "planner" / "ros2ws" / "src" / "planner" / "planner" / "planner_node.py", repo_root, 70)
    edges["planner-mapdb"] = _edge(
        "planner-mapdb",
        "component:planner",
        "mongo:MapDB.features",
        "feature lookup",
        "mongo_read",
        "data",
        protocol="MongoDB",
        source_refs=[planner_ref],
    )


def _add_system_edges(edges: dict[str, dict[str, Any]]) -> None:
    system_edges = [
        ("system:ui-api", "component:ui", "component:api", "HTTP adapter calls", "HTTP"),
        ("system:api-rest", "component:api", "component:c2_rest", "mission commands", "HTTP"),
        ("system:rest-centralized", "component:c2_rest", "component:centralized", "C2 ROS topics", "ROS"),
        ("system:centralized-planner", "component:centralized", "component:planner", "planner services/state", "ROS"),
        ("system:centralized-fleet", "component:centralized", "component:fleet", "agent and task services", "ROS"),
        ("system:fleet-edge", "component:fleet", "component:edge", "edge task dispatch", "ROS"),
        ("system:edge-autonomy", "component:edge", "component:autonomy", "autonomy topics", "ROS"),
        ("system:rosbridge-api", "component:rosbridge", "component:api", "live diagnostics/events", "WebSocket/SSE"),
        ("system:legacy-mongo", "component:centralized", "component:mongodb", "runtime persistence", "MongoDB"),
    ]
    for edge_id, source, target, label, protocol in system_edges:
        edges[edge_id] = _edge(edge_id, source, target, label, "system_flow", "system", protocol=protocol)


def _scenario_contracts(repo_root: Path) -> list[dict[str, Any]]:
    planner = repo_root / "legacy_ros" / "fog" / "planner" / "ros2ws" / "src" / "path_planning_lib" / "path_planning_lib" / "multi_robot_path_planning.py"
    planner_node = repo_root / "legacy_ros" / "fog" / "planner" / "ros2ws" / "src" / "planner" / "planner" / "planner_node.py"
    mission_manager = repo_root / "legacy_ros" / "fog" / "centralized-coordination" / "src" / "centralized_coordination" / "src" / "mission_manager.cpp"
    api = repo_root / "src" / "c2_imugs2" / "api.py"
    return [
        {
            "id": "mission_lifecycle",
            "label": "Mission Lifecycle",
            "summary": "Init, plan, approve, start, edge execution, and mission feedback.",
            "stages": [
                _stage("ui_init", "UI sends Init", "component:ui", outputs=["POST /api/missions/init"]),
                _stage("adapter_init", "Adapter normalizes and posts old REST", "component:api", source_refs=[_source_ref(api, repo_root, 219)], inputs=["MissionConfig"], outputs=["old REST action=initialize"]),
                _stage("c2_topic", "Old REST publishes mission init topic", "component:c2_rest", outputs=["/multi_robot/mission_init_request"]),
                _stage("create_planner", "Mission manager creates planner", "component:centralized", source_refs=[_source_ref(mission_manager, repo_root, 337)], inputs=["GetAgents", "MissionConfig"], outputs=["/multi_robot/planner/create"]),
                _stage("planner_output", "Planner caches path and exposes plan", "component:planner", source_refs=[_source_ref(planner_node, repo_root, 219), _source_ref(planner_node, repo_root, 361)], outputs=["GetPlan.plan JSON"]),
                _stage("feedback", "Mission manager stores planning and publishes feedback", "component:centralized", source_refs=[_source_ref(mission_manager, repo_root, 273), _source_ref(mission_manager, repo_root, 827)], outputs=["RuntimeDB.Planning", "/multi_robot/mission_feedback"]),
                _stage("edge_start", "Approve/start sends tasks and execute status", "component:fleet", source_refs=[_source_ref(mission_manager, repo_root, 1056), _source_ref(mission_manager, repo_root, 1078)], outputs=["edge add_task", "edge change_task_state"]),
            ],
        },
        {
            "id": "single_robot_navigation",
            "label": "Single Robot NAVIGATE",
            "summary": "One vehicle and one point objective produce one A* path.",
            "stages": [
                _stage("config", "MissionConfig behavior=0, one vehicle, Point geometry", "schema:mission_config.schema.json", inputs=["objective.geometries[].Point", "vehicles[1]", "transit.optimization.road_usage"]),
                _stage("allocate", "Point allocated to one agent", "component:planner", source_refs=[_source_ref(planner, repo_root, 110)], outputs=["allocations[agent_id]=point"]),
                _stage("astar", "A* path to nearest routable graph nodes", "component:planner", source_refs=[_source_ref(planner, repo_root, 184), _source_ref(planner, repo_root, 390)], outputs=["agent path [[lon,lat], ...]"]),
                _stage("plan_json", "Planner plan JSON objectives per waypoint", "component:planner", source_refs=[_source_ref(planner_node, repo_root, 296)], outputs=["tasks[agent_id].objectives[]"]),
            ],
        },
        {
            "id": "multi_robot_navigation",
            "label": "Multi-Robot NAVIGATE",
            "summary": "Multiple vehicles and point objectives are assigned before path planning.",
            "stages": [
                _stage("config", "MissionConfig behavior=0, multiple vehicles and points", "schema:mission_config.schema.json", inputs=["vehicles[n]", "Point or MultiPoint geometries"]),
                _stage("assign", "Hungarian when points <= vehicles; mTSP when points > vehicles", "component:planner", source_refs=[_source_ref(planner, repo_root, 114)], outputs=["agent objective allocations"]),
                _stage("mapf", "Independent A* per agent or CBS by planner parameter", "component:planner", source_refs=[_source_ref(planner, repo_root, 199)], outputs=["paths keyed by agent_id"]),
            ],
        },
        {
            "id": "coverage_zone",
            "label": "Coverage / Sweep Zone",
            "summary": "Coverage currently selects reachable coverage points; it is not a dense lawnmower sweep.",
            "stages": [
                _stage("config", "MissionConfig behavior=1, Polygon or LineString objective", "schema:mission_config.schema.json", inputs=["objective.geometries[].Polygon", "maximize_coverage"]),
                _stage("single", "One remaining agent selects first reachable coverage point", "component:planner", source_refs=[_source_ref(planner, repo_root, 143)], outputs=["one path to selected coverage point"]),
                _stage("multi", "Multiple agents select MCLP coverage points, then Hungarian assignment", "component:planner", source_refs=[_source_ref(planner, repo_root, 161)], outputs=["one target per remaining agent"]),
            ],
            "risks": ["Current implementation does not output full sweep strips for every zone."],
        },
        {
            "id": "mission_roads",
            "label": "Runtime Drawn Roads",
            "summary": "LineString geometries in transit.roads or objective.geometries become temporary routable road graph edges.",
            "stages": [
                _stage("inline", "Adapter inlines runtime feature_id references", "component:api", source_refs=[_source_ref(api, repo_root, 1194)], outputs=["inline LineString geometry"]),
                _stage("graph", "Planner augments graph with mission_line and mission_connector edges", "component:planner", source_refs=[_source_ref(planner, repo_root, 237)], outputs=["temporary road graph"]),
                _stage("roads_only", "road_usage >= 0.999 restricts to preferred road sources", "component:planner", source_refs=[_source_ref(repo_root / "legacy_ros" / "fog" / "planner" / "ros2ws" / "src" / "path_planning_lib" / "path_planning_lib" / "mapf.py", repo_root, 25)], outputs=["osm, mission_line, mission_connector"]),
            ],
        },
        {
            "id": "unsupported_no_planning",
            "label": "NAVIGATE_NO_PLANNING Gap",
            "summary": "Enum and schema allow behavior=2, but the active planner branch rejects it.",
            "stages": [
                _stage("enum", "Legacy enum declares NAVIGATE_NO_PLANNING=2", "ros_type:centralized_msgs/msg/Agent", source_refs=[_source_ref(repo_root / "legacy_ros" / "fog" / "planner" / "ros2ws" / "src" / "message_packages" / "centralized_msgs" / "json" / "Enums.hpp", repo_root, 66)]),
                _stage("schema", "Canonical schema allows behavior enum [0,1,2]", "schema:mission_config.schema.json", source_refs=[_source_ref(repo_root / "schemas" / "mission_config.schema.json", repo_root, 11)]),
                _stage("planner", "Planner solve branch only supports behavior 0 and 1", "component:planner", source_refs=[_source_ref(planner, repo_root, 170)], outputs=["ValueError unsupported behavior"]),
            ],
            "risks": ["This is a real code/contract mismatch and should be shown as unsupported in the UI."],
        },
    ]


def _stage(
    stage_id: str,
    label: str,
    component: str,
    *,
    inputs: list[str] | None = None,
    outputs: list[str] | None = None,
    source_refs: list[dict[str, Any]] | None = None,
    notes: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": stage_id,
        "label": label,
        "component": component,
        "inputs": inputs or [],
        "outputs": outputs or [],
        "source_refs": source_refs or [],
        "notes": notes or [],
    }


def _component_for_path(relative_path: str) -> str:
    if relative_path.startswith("frontend/"):
        return "component:ui"
    if relative_path.startswith("src/c2_imugs2/api.py") or relative_path.startswith("src/c2_imugs2/rosbridge.py"):
        return "component:api"
    if "legacy_ros/fog/command-control" in relative_path:
        return "component:c2_rest"
    if "legacy_ros/fog/planner" in relative_path:
        return "component:planner"
    if "legacy_ros/edge" in relative_path:
        return "component:edge"
    if "legacy_ros/fog/centralized-coordination" in relative_path:
        if "fleet_manager" in relative_path:
            return "component:fleet"
        return "component:centralized"
    if relative_path.startswith("schemas/"):
        return "component:schemas"
    return "component:api"


def _component_for_compose_service(name: str) -> str | None:
    return {
        "c2-imugs2-api": "component:api",
        "c2-imugs2-ui": "component:ui",
        "mongodb": "component:mongodb",
        "centralized-coordination": "component:centralized",
        "planner": "component:planner",
        "c2-ros-rest": "component:c2_rest",
        "rosbridge": "component:rosbridge",
        "edge-agent-sim-1": "component:edge",
    }.get(name)


def _apply_runtime_status(node: dict[str, Any], runtime: dict[str, Any]) -> None:
    interface = (node.get("details") or {}).get("interface") or node["label"]
    if node["kind"] == "ros_topic":
        visible = interface in set(runtime.get("topics", []))
    elif node["kind"] == "ros_service":
        visible = interface in set(runtime.get("services", []))
    else:
        visible = False
    node["runtime_status"] = "visible" if visible else "not_seen"


def _source_ref(path: Path, repo_root: Path, line: int) -> dict[str, Any]:
    return {"path": _relative(path, repo_root), "line": line}


def _relative(path: Path, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except (OSError, ValueError):
        return str(path)
