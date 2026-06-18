from __future__ import annotations

from copy import deepcopy
import json
from dataclasses import dataclass
from typing import Any
from urllib import error, request

from .domain import MissionRequest


LEGACY_STATUS_REQUESTS = {
    MissionRequest.APPROVE: 1,
    MissionRequest.START: 2,
    MissionRequest.PAUSE: 3,
    MissionRequest.STOP: 4,
    MissionRequest.DELETE: 5,
}


@dataclass(frozen=True)
class LegacyRestResponse:
    ok: bool
    status_code: int
    body: str


def to_legacy_mission_config(mission_config: dict[str, Any]) -> dict[str, Any]:
    """Translate canonical adapter fields back to the old REST/ROS ICD spellings."""
    legacy = deepcopy(mission_config)
    transit = legacy.get("transit")
    if isinstance(transit, dict) and "optimization" in transit:
        transit["optimalization"] = deepcopy(transit["optimization"])
        transit.pop("optimization", None)
    return legacy


class LegacyRestClient:
    def __init__(self, base_url: str = "http://localhost:5001/mission_control", timeout_seconds: float = 3.0):
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds

    def initialize_mission(self, mission_config: dict[str, Any]) -> LegacyRestResponse:
        legacy_config = to_legacy_mission_config(mission_config)
        return self._post(
            {
                "action": "initialize",
                "mission_id": legacy_config["mission_id"],
                "mission_config": json.dumps(legacy_config),
            }
        )

    def change_status(self, requested_status: MissionRequest) -> LegacyRestResponse:
        if requested_status not in LEGACY_STATUS_REQUESTS:
            raise ValueError(f"Unsupported legacy mission request: {requested_status.name}")
        return self._post({"action": "change_status", "requested_state": LEGACY_STATUS_REQUESTS[requested_status]})

    def health(self) -> LegacyRestResponse:
        # The old listener only supports POST/OPTIONS. OPTIONS is the least invasive reachability check.
        req = request.Request(self.base_url, method="OPTIONS")
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                return LegacyRestResponse(True, response.status, response.read().decode("utf-8", errors="replace"))
        except error.HTTPError as exc:
            return LegacyRestResponse(False, exc.code, exc.read().decode("utf-8", errors="replace"))
        except OSError as exc:
            return LegacyRestResponse(False, 0, str(exc))

    def _post(self, payload: dict[str, Any]) -> LegacyRestResponse:
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            self.base_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                return LegacyRestResponse(True, response.status, response.read().decode("utf-8", errors="replace"))
        except error.HTTPError as exc:
            return LegacyRestResponse(False, exc.code, exc.read().decode("utf-8", errors="replace"))
        except OSError as exc:
            return LegacyRestResponse(False, 0, str(exc))
