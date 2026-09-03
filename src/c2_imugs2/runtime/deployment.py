"""Docker-facing helpers for launching one editable-backend deployment."""

from __future__ import annotations

import http.client
import json
import os
import re
import socket
from pathlib import Path
from typing import Any


EDGE_IMAGE = "c2-imugs2/backend-edge-agent-sim:local"
BACKEND_CONFIG_DIR = Path("backend/config")
LOCAL_CYCLONEDDS_URI = (
    "<CycloneDDS><Domain><Discovery><ParticipantIndex>auto</ParticipantIndex>"
    "<MaxAutoParticipantIndex>120</MaxAutoParticipantIndex></Discovery></Domain>"
    "</CycloneDDS>"
)


def launch_deployment(
    repo_root: Path,
    payload: dict[str, Any],
    *,
    host_repo_root: Path | None = None,
    docker_socket: str = "/var/run/docker.sock",
) -> dict[str, Any]:
    deployment_id = _safe_name(str(payload.get("deployment_id") or "deployment"))
    agents = payload.get("agents")
    if not isinstance(agents, list) or not agents:
        raise ValueError("deployment launch requires at least one deployment vehicle")

    launch_dir = repo_root / "data" / "runtime" / "deployment_launches" / deployment_id
    launch_dir.mkdir(parents=True, exist_ok=True)
    host_root = host_repo_root or repo_root
    host_launch_dir = host_root / "data" / "runtime" / "deployment_launches" / deployment_id

    containers = []
    for index, agent in enumerate(agents, start=1):
        if not isinstance(agent, dict):
            raise ValueError("deployment agents must be objects")
        agent_id = _agent_id(agent, index)
        prefix = _topic_prefix(agent, index)
        config_path = launch_dir / f"{prefix}_autonomy.yaml"
        config_path.write_text(_autonomy_config(prefix, agent), encoding="utf-8")
        container_name = f"c2-imugs2-backend-deployment-{deployment_id}-{_safe_name(agent_id)[:12]}"
        containers.append(
            {
                "agent_id": agent_id,
                "agent_env_id": agent_id.replace("-", "_"),
                "name": str(agent.get("name") or agent_id),
                "topic_prefix": prefix,
                "container_name": container_name,
                "autonomy_config": str(config_path),
                "host_autonomy_config": str(host_launch_dir / config_path.name),
            }
        )

    compose_path = launch_dir / "docker-compose.deployment.yml"
    compose_path.write_text(_compose_yaml(containers, host_root), encoding="utf-8")
    manifest = {
        "deployment_id": deployment_id,
        "name": payload.get("name") or deployment_id,
        "agent_count": len(containers),
        "containers": containers,
        "compose_file": str(compose_path),
        "host_command": f"docker compose -f {host_launch_dir / 'docker-compose.deployment.yml'} up -d",
    }
    (launch_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    result = {
        **manifest,
        "status": "generated",
        "message": "Deployment launch files generated.",
        "docker_started": False,
        "docker_socket": docker_socket,
    }
    if not Path(docker_socket).exists():
        result["message"] = "Deployment launch files generated; Docker socket is not available to the API service."
        return result

    try:
        started = _start_containers_with_docker_socket(docker_socket, containers, host_root)
    except OSError as exc:
        result["message"] = f"Deployment launch files generated; Docker start failed: {exc}"
        result["docker_error"] = str(exc)
        return result

    result["status"] = "started"
    result["docker_started"] = True
    result["started_containers"] = started
    result["message"] = f"Started {len(started)} deployment vehicle simulation container(s)."
    return result


def _agent_id(agent: dict[str, Any], index: int) -> str:
    raw = str(agent.get("agent_id") or "").strip()
    return raw if raw else f"deployment-agent-{index:02d}"


def _topic_prefix(agent: dict[str, Any], index: int) -> str:
    name = str(agent.get("name") or agent.get("agent_id") or f"vehicle-{index}")
    prefix = re.sub(r"[^A-Za-z0-9_]+", "_", name.strip()).strip("_")
    if not prefix:
        prefix = f"DeploymentVehicle{index}"
    if not prefix[0].isalpha():
        prefix = f"Vehicle_{prefix}"
    return prefix[:48]


def _safe_name(value: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "-", value.strip()).strip("-_.").lower()
    return safe[:48] or "deployment"


def _number(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _autonomy_config(prefix: str, agent: dict[str, Any]) -> str:
    constraints = agent.get("constraints") if isinstance(agent.get("constraints"), dict) else {}
    location = agent.get("current_location") if isinstance(agent.get("current_location"), list | tuple) else [4.392588, 50.844317]
    lon = _number(location[0] if len(location) > 0 else None, 4.392588)
    lat = _number(location[1] if len(location) > 1 else None, 50.844317)
    vehicle_type = str(agent.get("vehicle_type") or "ugv")
    return f"""autonomy_id_key:
  ros__parameters:
    vehicle_type: "{vehicle_type}"
    start_location: [{lon:.7f}, {lat:.7f}]
    coordinate_mode: 0
    active_autonomy_mode: 1
    max_speed: {_number(constraints.get("max_speed"), 4.0)}
    max_acceleration: {_number(constraints.get("max_acceleration"), 8.0)}
    max_weight: {_number(constraints.get("max_weight"), 16.0)}
    max_tilt_angle: {_number(constraints.get("max_tilt_angle"), 1.8)}
    fuel_status_pct: 100.0
    fuel_hours: 4.0
    battery_status_pct: 100.0
    battery_hours: 4.0
    vehicle_dimensions: [0.9, 0.6, 0.55]
"""


def _compose_yaml(containers: list[dict[str, Any]], host_root: Path) -> str:
    services = ["name: c2-imugs2-deployment-launch", "", "services:"]
    for container in containers:
        service = _safe_name(container["container_name"])
        services.extend(
            [
                f"  {service}:",
                f"    image: {EDGE_IMAGE}",
                f"    container_name: {container['container_name']}",
                "    network_mode: host",
                "    environment:",
                f"      ROS_DOMAIN_ID: \"{os.environ.get('ROS_DOMAIN_ID', '112')}\"",
                f"      RMW_IMPLEMENTATION: \"{os.environ.get('RMW_IMPLEMENTATION', 'rmw_cyclonedds_cpp')}\"",
                f"      ROS_LOCALHOST_ONLY: \"{os.environ.get('ROS_LOCALHOST_ONLY', '1')}\"",
                f"      CYCLONEDDS_URI: \"{os.environ.get('CYCLONEDDS_URI', LOCAL_CYCLONEDDS_URI)}\"",
                "      C2_INTERFACE_AVOID_ROS_PREFIX: \"FALSE\"",
                f"      AGENT_ID: {container['agent_env_id']}",
                f"      AUTONOMY_TOPIC_PREFIX: {container['topic_prefix']}",
                "    volumes:",
                f"      - {host_root / BACKEND_CONFIG_DIR / 'config_agent-tasks-supervisor.yaml'}:/app/config.yaml:ro",
                f"      - {container['host_autonomy_config']}:/app/autonomy_config.yaml:ro",
                f"      - {host_root / BACKEND_CONFIG_DIR / 'launch_agent_tasks_supervisor.sh'}:/app/launch_agent_tasks_supervisor.sh:ro",
                f"      - {host_root / BACKEND_CONFIG_DIR / 'launch_autonomy_sim.sh'}:/app/launch_autonomy_sim.sh:ro",
                f"      - {host_root / BACKEND_CONFIG_DIR / 'launch_edge_with_autonomy_sim.sh'}:/app/launch_edge_with_autonomy_sim.sh:ro",
                '    command: bash -lc "bash /app/launch_edge_with_autonomy_sim.sh"',
            ]
        )
    return "\n".join(services) + "\n"


class _DockerHTTPConnection(http.client.HTTPConnection):
    def __init__(self, socket_path: str):
        super().__init__("localhost")
        self.socket_path = socket_path

    def connect(self) -> None:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(self.socket_path)
        self.sock = sock


def _docker_request(socket_path: str, method: str, path: str, payload: dict[str, Any] | None = None) -> tuple[int, Any]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"} if body is not None else {}
    conn = _DockerHTTPConnection(socket_path)
    conn.request(method, path, body=body, headers=headers)
    response = conn.getresponse()
    # Docker log endpoints use an 8-byte multiplexing header around stdout and
    # stderr chunks. Preserve the text markers even when those framing bytes
    # are not valid UTF-8.
    raw = response.read().decode("utf-8", errors="replace")
    conn.close()
    try:
        parsed = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        parsed = raw
    return response.status, parsed


def _start_containers_with_docker_socket(socket_path: str, containers: list[dict[str, Any]], host_root: Path) -> list[str]:
    started = []
    binds_common = [
        f"{host_root / BACKEND_CONFIG_DIR / 'config_agent-tasks-supervisor.yaml'}:/app/config.yaml:ro",
        f"{host_root / BACKEND_CONFIG_DIR / 'launch_agent_tasks_supervisor.sh'}:/app/launch_agent_tasks_supervisor.sh:ro",
        f"{host_root / BACKEND_CONFIG_DIR / 'launch_autonomy_sim.sh'}:/app/launch_autonomy_sim.sh:ro",
        f"{host_root / BACKEND_CONFIG_DIR / 'launch_edge_with_autonomy_sim.sh'}:/app/launch_edge_with_autonomy_sim.sh:ro",
    ]
    for container in containers:
        name = container["container_name"]
        _docker_request(socket_path, "DELETE", f"/containers/{name}?force=true")
        config = {
            "Image": EDGE_IMAGE,
            "Cmd": ["bash", "-lc", "bash /app/launch_edge_with_autonomy_sim.sh"],
            "Labels": {
                "c2-imugs2.role": "deployment-agent",
                "c2-imugs2.agent-id": container["agent_id"],
            },
            "Env": [
                f"ROS_DOMAIN_ID={os.environ.get('ROS_DOMAIN_ID', '112')}",
                f"RMW_IMPLEMENTATION={os.environ.get('RMW_IMPLEMENTATION', 'rmw_cyclonedds_cpp')}",
                f"ROS_LOCALHOST_ONLY={os.environ.get('ROS_LOCALHOST_ONLY', '1')}",
                f"CYCLONEDDS_URI={os.environ.get('CYCLONEDDS_URI', LOCAL_CYCLONEDDS_URI)}",
                "C2_INTERFACE_AVOID_ROS_PREFIX=FALSE",
                f"AGENT_ID={container['agent_env_id']}",
                f"AUTONOMY_TOPIC_PREFIX={container['topic_prefix']}",
            ],
            "HostConfig": {
                "NetworkMode": "host",
                "Binds": [*binds_common, f"{container['host_autonomy_config']}:/app/autonomy_config.yaml:ro"],
            },
        }
        status, created = _docker_request(socket_path, "POST", f"/containers/create?name={name}", config)
        if status not in (201, 304):
            raise OSError(f"Docker create failed for {name}: {created}")
        status, started_payload = _docker_request(socket_path, "POST", f"/containers/{name}/start")
        if status not in (204, 304):
            raise OSError(f"Docker start failed for {name}: {started_payload}")
        started.append(name)
    return started
