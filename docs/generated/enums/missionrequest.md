# MissionRequest

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

## c2_imugs2.domain.MissionRequest

Language: **Python** · Evidence: [`src/c2_imugs2/domain.py:38`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/domain.py#L38)

| Value | Member | Source comment |
|---:|---|---|
| `0` | `INIT` |  |
| `1` | `APPROVE` |  |
| `2` | `START` |  |
| `3` | `PAUSE` |  |
| `4` | `STOP` |  |
| `5` | `DELETE` |  |

## Values used by the verified navigation run

The [one-robot Point-navigation run](../examples/single-robot-point-navigation.md) exercised these values:

| Value | Member | Where it appeared |
|---:|---|---|
| `0` | `INIT` | initialize |
| `1` | `APPROVE` | install stopped task |
| `2` | `START` | execute task |

Example evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:11`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L11)

