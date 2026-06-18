from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass
from typing import Any

import websockets


REQUIRED_NODES = {
    "/c2_node",
    "/c2_interface_node",
    "/orchestrator_node",
    "/fleet_manager_node",
    "/planner_node",
    "/rosbridge_websocket",
    "/agent_f9992bb3_9871_451f_90a0_9207eb9fe6c5",
    "/autonomy_test_node_Themis_Fr",
}

REQUIRED_TOPICS = {
    "/multi_robot/mission_init_request",
    "/multi_robot/mission_feedback",
    "/multi_robot/edge/feedback",
    "/multi_robot/planner/state",
}

LIVE_TOPICS = (
    "/multi_robot/mission_feedback",
    "/multi_robot/edge/feedback",
    "/multi_robot/planner/state",
)


@dataclass(frozen=True)
class RosbridgeCallResult:
    ok: bool
    values: dict[str, Any]
    error: str = ""


class RosbridgeClient:
    def __init__(self, url: str = "ws://localhost:9090", timeout_seconds: float = 3.0):
        self.url = url
        self.timeout_seconds = timeout_seconds

    async def call_service(self, service: str, args: dict[str, Any] | None = None) -> RosbridgeCallResult:
        call_id = str(uuid.uuid4())
        payload = {"op": "call_service", "service": service, "args": args or {}, "id": call_id}
        try:
            async with websockets.connect(self.url, open_timeout=self.timeout_seconds) as websocket:
                await websocket.send(json.dumps(payload))
                while True:
                    raw = await asyncio.wait_for(websocket.recv(), timeout=self.timeout_seconds)
                    message = json.loads(raw)
                    if message.get("id") != call_id:
                        continue
                    if message.get("op") == "service_response":
                        return RosbridgeCallResult(bool(message.get("result", False)), dict(message.get("values") or {}))
        except Exception as exc:
            return RosbridgeCallResult(False, {}, str(exc))

    async def diagnostics(self) -> dict[str, Any]:
        nodes_result, topics_result, services_result = await asyncio.gather(
            self.call_service("/rosapi/nodes"),
            self.call_service("/rosapi/topics"),
            self.call_service("/rosapi/services"),
        )
        nodes = list(nodes_result.values.get("nodes", []))
        topics = list(topics_result.values.get("topics", []))
        services = list(services_result.values.get("services", []))

        checks = [
            _check("rosbridge.websocket", nodes_result.ok or topics_result.ok or services_result.ok, "rosbridge reachable", nodes_result.error or topics_result.error or services_result.error),
            _check("ros.nodes.required", REQUIRED_NODES.issubset(set(nodes)), "required ROS nodes visible", f"missing {sorted(REQUIRED_NODES - set(nodes))}"),
            _check("ros.topics.required", REQUIRED_TOPICS.issubset(set(topics)), "required ROS topics visible", f"missing {sorted(REQUIRED_TOPICS - set(topics))}"),
        ]
        return {
            "rosbridge_url": self.url,
            "nodes": nodes,
            "topics": topics,
            "services": services,
            "checks": checks,
        }

    async def topic_messages(self, topics: tuple[str, ...] = LIVE_TOPICS):
        try:
            async with websockets.connect(self.url, open_timeout=self.timeout_seconds) as websocket:
                for topic in topics:
                    await websocket.send(json.dumps({"op": "subscribe", "topic": topic, "throttle_rate": 250}))
                async for raw in websocket:
                    message = json.loads(raw)
                    if message.get("op") == "publish" and message.get("topic") in topics:
                        yield {"topic": message["topic"], "msg": message.get("msg") or {}}
        except Exception as exc:
            yield {"topic": "rosbridge.error", "msg": {"error": str(exc)}}


def _check(check_id: str, ok: bool, ok_message: str, fail_message: str) -> dict[str, str]:
    return {"id": check_id, "status": "ok" if ok else "error", "message": ok_message if ok else fail_message}
