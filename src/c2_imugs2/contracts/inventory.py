"""Static enum and state-machine contract inventory."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import re
from typing import Any


_CPP_ENUM = re.compile(r"enum\s+class\s+(?P<name>\w+)\s*(?::\s*[^\{]+)?\{(?P<body>.*?)\};", re.S)
_CPP_MEMBER = re.compile(r"^\s*(?P<name>[A-Za-z_]\w*)\s*(?:=\s*(?P<value>[-+]?\d+|0[xX][0-9A-Fa-f]+))?\s*$")


def build_contract_inventory(repo_root: Path) -> dict[str, Any]:
    """Extract enum/state contracts and the backend-to-legacy change set."""

    repo_root = repo_root.resolve()
    definitions = _python_enums(repo_root) + _cpp_enums(repo_root)
    definitions.sort(key=lambda item: (item["name"], item["source_ref"]["path"], item["source_ref"]["line"]))
    return {
        "enum_definitions": definitions,
        "enum_groups": _group_enums(definitions),
        "state_machines": [
            _mission_state_machine(repo_root),
            _planner_state_machine(repo_root),
            _task_state_machine(repo_root, definitions),
        ],
        "backend_legacy_changes": compare_backend_to_legacy(repo_root),
    }


def _python_enums(repo_root: Path) -> list[dict[str, Any]]:
    definitions: list[dict[str, Any]] = []
    root = repo_root / "src" / "c2_imugs2"
    for path in sorted(root.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        for node in tree.body:
            if not isinstance(node, ast.ClassDef) or not _is_enum_class(node):
                continue
            members: list[dict[str, Any]] = []
            for statement in node.body:
                if not isinstance(statement, (ast.Assign, ast.AnnAssign)):
                    continue
                target = statement.targets[0] if isinstance(statement, ast.Assign) else statement.target
                value_node = statement.value
                if not isinstance(target, ast.Name) or value_node is None:
                    continue
                try:
                    value = ast.literal_eval(value_node)
                except (ValueError, TypeError):
                    continue
                if isinstance(value, (str, int)) and not isinstance(value, bool):
                    members.append({"name": target.id, "value": value, "description": ""})
            if members:
                definitions.append(
                    {
                        "id": f"python:{node.name}:{_relative(path, repo_root)}:{node.lineno}",
                        "name": node.name,
                        "qualified_name": (
                            ".".join(
                                path.relative_to(repo_root / "src")
                                .with_suffix("")
                                .parts
                            )
                            + f".{node.name}"
                        ),
                        "language": "Python",
                        "members": members,
                        "source_ref": _ref(path, repo_root, node.lineno),
                    }
                )
    return definitions


def _is_enum_class(node: ast.ClassDef) -> bool:
    for base in node.bases:
        if isinstance(base, ast.Name) and base.id in {"Enum", "IntEnum", "StrEnum"}:
            return True
        if isinstance(base, ast.Attribute) and base.attr in {"Enum", "IntEnum", "StrEnum"}:
            return True
    return False


def _cpp_enums(repo_root: Path) -> list[dict[str, Any]]:
    definitions: list[dict[str, Any]] = []
    root = repo_root / "backend"
    for path in sorted(root.rglob("*")):
        if path.suffix not in {".h", ".hpp", ".cpp"} or _ignored_source(path):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        scan_text = re.sub(r"/\*.*?\*/", lambda value: "\n" * value.group(0).count("\n"), text, flags=re.S)
        scan_text = re.sub(r"(?m)^\s*//.*$", "", scan_text)
        for match in _CPP_ENUM.finditer(scan_text):
            members = _parse_cpp_members(match.group("body"))
            if not members:
                continue
            line = scan_text[: match.start()].count("\n") + 1
            package = _message_package(path)
            qualified = f"{package}.{match.group('name')}" if package else match.group("name")
            definitions.append(
                {
                    "id": f"cpp:{qualified}:{_relative(path, repo_root)}:{line}",
                    "name": match.group("name"),
                    "qualified_name": qualified,
                    "language": "C++",
                    "members": members,
                    "source_ref": _ref(path, repo_root, line),
                }
            )
    return definitions


def _parse_cpp_members(body: str) -> list[dict[str, Any]]:
    members: list[dict[str, Any]] = []
    current_value = -1
    for raw in body.splitlines():
        code, _, comment = raw.partition("//")
        code = code.strip().rstrip(",").strip()
        description = comment.strip()
        match = _CPP_MEMBER.match(code)
        if not match:
            continue
        raw_value = match.group("value")
        current_value = int(raw_value, 0) if raw_value is not None else current_value + 1
        members.append({"name": match.group("name"), "value": current_value, "description": description})
    return members


def _message_package(path: Path) -> str:
    parts = path.parts
    try:
        return parts[parts.index("message_packages") + 1]
    except (ValueError, IndexError):
        return ""


def _group_enums(definitions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_name: dict[str, list[dict[str, Any]]] = {}
    for definition in definitions:
        by_name.setdefault(definition["name"], []).append(definition)
    groups: list[dict[str, Any]] = []
    for name, items in sorted(by_name.items()):
        signatures: dict[tuple[tuple[str, Any], ...], list[str]] = {}
        for item in items:
            signature = tuple((member["name"], member["value"]) for member in item["members"])
            signatures.setdefault(signature, []).append(item["id"])
        groups.append(
            {
                "name": name,
                "status": "consistent" if len(signatures) == 1 else "conflict",
                "definition_count": len(items),
                "variant_count": len(signatures),
                "definitions": [item["id"] for item in items],
            }
        )
    return groups


def _mission_state_machine(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp"
    text = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
    enum = _first_enum(repo_root, "MissionStatus", preferred="centralized_msgs")
    transitions: list[dict[str, Any]] = []
    transition_pattern = re.compile(
        r"(?:if|else\s+if)\s*\(new_state\s*==\s*\(int\)\s*MissionStatus::(?P<source>\w+)\).*?"
        r"allowed_indices\.insert\([^\{]*\{(?P<targets>.*?)\}\);",
        re.S,
    )
    for match in transition_pattern.finditer(text):
        source = match.group("source")
        line = text[: match.start()].count("\n") + 1
        for target in re.findall(r"MissionStatus::(\w+)", match.group("targets")):
            transitions.append({"from": source, "to": target, "trigger": "allowed status change", "source_ref": _ref(path, repo_root, line)})

    request_mappings: list[dict[str, Any]] = []
    mapping_pattern = re.compile(
        r"case\s+\(int\)\s*MissionStatusRequest::(?P<request>\w+)\s*:\s*"
        r"return\s+\(int\)\s*MissionStatus::(?P<state>\w+)",
        re.S,
    )
    for match in mapping_pattern.finditer(text):
        request_mappings.append(
            {
                "request": match.group("request"),
                "state": match.group("state"),
                "source_ref": _ref(path, repo_root, text[: match.start()].count("\n") + 1),
            }
        )
    return {
        "id": "mission_lifecycle",
        "name": "Mission lifecycle",
        "description": "Allowed mission status transitions enforced by MissionManager.",
        "states": enum.get("members", []),
        "transitions": transitions,
        "request_mappings": request_mappings,
        "notes": ["Self-transitions are present where the backend explicitly permits them."],
        "source_refs": [_ref(path, repo_root, _line_for(text, "_updateAllowedTransitions"))],
    }


def _planner_state_machine(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "backend/fog/planner/ros2ws/src/planner/planner/planner_node.py"
    text = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
    labels = {0: "INITIALIZED", 1: "PLANNING", 2: "PLANNED", 3: "DISCONNECTED", 4: "PLANNING_FAILED"}
    states = [{"name": name, "value": value, "description": ""} for value, name in labels.items()]
    refs: dict[int, dict[str, Any]] = {}
    pattern = re.compile(r"planner_states\.update\(\{mission_id:\s*(\d+)\}\)\s*(?:#\s*([^\n]*))?")
    for match in pattern.finditer(text):
        refs.setdefault(int(match.group(1)), _ref(path, repo_root, text[: match.start()].count("\n") + 1))
    transitions = [
        {"from": "INITIALIZED", "to": "PLANNING", "trigger": "planning starts", "source_ref": refs.get(1, _ref(path, repo_root, 1))},
        {"from": "PLANNING", "to": "PLANNED", "trigger": "non-empty plan cached", "source_ref": refs.get(2, _ref(path, repo_root, 1))},
        {"from": "PLANNING", "to": "PLANNING_FAILED", "trigger": "empty route or planning exception", "source_ref": refs.get(4, _ref(path, repo_root, 1))},
    ]
    return {
        "id": "planner_lifecycle",
        "name": "Planner lifecycle",
        "description": "Per-mission numeric planner state published on /multi_robot/planner/state.",
        "states": states,
        "transitions": transitions,
        "request_mappings": [],
        "notes": ["State 3 is interpreted as disconnected by MissionManager; Planner does not assign it in the scanned source."],
        "source_refs": [_ref(path, repo_root, _line_for(text, "planner_states"))],
    }


def _task_state_machine(repo_root: Path, definitions: list[dict[str, Any]]) -> dict[str, Any]:
    path = repo_root / "backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp"
    text = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
    state = _definition(definitions, "TaskState", "task_msgs")
    request = _definition(definitions, "TaskRequestState", "task_msgs")
    states = state.get("members", [])
    by_value = {member["value"]: member["name"] for member in states}
    transitions = []
    for member in request.get("members", []):
        target = by_value.get(member["value"], f"UNDEFINED_{member['value']}")
        transitions.append(
            {
                "from": "ANY",
                "to": target,
                "trigger": member["name"],
                "source_ref": _ref(path, repo_root, _line_for(text, "void AgentTaskSupervisorNode::_changeTaskStateService_callback")),
            }
        )
    return {
        "id": "edge_task_lifecycle",
        "name": "Edge task lifecycle",
        "description": "The edge service copies TaskRequestState's numeric value directly into TaskState.",
        "states": states,
        "transitions": transitions,
        "request_mappings": [{"request": item["trigger"], "state": item["to"], "source_ref": item["source_ref"]} for item in transitions],
        "notes": [
            "Contract mismatch: DELETE=3 in TaskRequestState is copied directly, but TaskState value 3 means COMPLETED; DELETED is value 5."
        ],
        "source_refs": [_ref(path, repo_root, _line_for(text, "void AgentTaskSupervisorNode::_changeTaskStateService_callback"))],
    }


def _first_enum(repo_root: Path, name: str, preferred: str = "") -> dict[str, Any]:
    definitions = _python_enums(repo_root) + _cpp_enums(repo_root)
    return _definition(definitions, name, preferred)


def _definition(definitions: list[dict[str, Any]], name: str, preferred: str = "") -> dict[str, Any]:
    matches = [item for item in definitions if item["name"] == name]
    preferred_matches = [item for item in matches if preferred and preferred in item["qualified_name"]]
    return (preferred_matches or matches or [{}])[0]


def compare_backend_to_legacy(repo_root: Path) -> dict[str, Any]:
    backend = _comparable_files(repo_root / "backend")
    legacy = _comparable_files(repo_root / "legacy_ros")
    backend_only = sorted(set(backend) - set(legacy))
    legacy_only = sorted(set(legacy) - set(backend))
    changed = sorted(path for path in set(backend) & set(legacy) if backend[path] != legacy[path])
    return {
        "summary": {
            "backend_files": len(backend),
            "legacy_files": len(legacy),
            "changed": len(changed),
            "backend_only": len(backend_only),
            "legacy_only": len(legacy_only),
            "identical": len(set(backend) & set(legacy)) - len(changed),
        },
        "changed": changed,
        "backend_only": backend_only,
        "legacy_only": legacy_only,
    }


def _comparable_files(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    if not root.exists():
        return result
    suffixes = {".py", ".cpp", ".hpp", ".h", ".msg", ".srv", ".json", ".yaml", ".yml", ".sh", ".xml"}
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in suffixes or _ignored_source(path):
            continue
        relative = str(path.relative_to(root))
        result[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def _ignored_source(path: Path) -> bool:
    ignored = {".git", ".devcontainer", "build", "install", "log", "__pycache__", ".pytest_cache"}
    return bool(ignored.intersection(path.parts))


def _line_for(text: str, needle: str) -> int:
    index = text.find(needle)
    return text[:index].count("\n") + 1 if index >= 0 else 1


def _ref(path: Path, repo_root: Path, line: int) -> dict[str, Any]:
    return {"path": _relative(path, repo_root), "line": line}


def _relative(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except (OSError, ValueError):
        return str(path)
