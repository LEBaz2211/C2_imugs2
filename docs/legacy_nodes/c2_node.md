# `/c2_node`

## Purpose

`/c2_node` is the old REST-to-ROS bridge. It listens on `http://localhost:5001/mission_control`, accepts mission commands as HTTP JSON, and republishes them as old C2 ROS messages.

Source:

```text
legacy_ros/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/main.cpp
legacy_ros/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/MissionHandler.cpp
legacy_ros/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/c2_rest.cpp
```

## Inputs

| Input | Type | Meaning |
| --- | --- | --- |
| `POST /mission_control` with `action="initialize"` | HTTP JSON | Start a mission init request |
| `POST /mission_control` with `action="change_status"` | HTTP JSON | Request mission APPROVE, START, PAUSE, STOP, or DELETE |
| `/multi_robot/mission_init_response` | `c2_msgs/msg/InitMissionResponse` | Optional init response from fog |
| `/multi_robot/change_mission_status_response` | `c2_msgs/msg/ChangeMissionStatusResponse` | Status-change response from mission manager |

For `initialize`, the REST handler expects `mission_config` to be a JSON string, not a nested JSON object.

## Outputs

| Output | Type | Payload |
| --- | --- | --- |
| `/multi_robot/mission_init_request` | `c2_msgs/msg/InitMissionRequest` | `mission_id UUID`, `mission_config string<=10000` |
| `/multi_robot/change_mission_status_request` | `c2_msgs/msg/ChangeMissionStatusRequest` | `mission_id UUID`, `mission_request_status uint8` |

## Internal Behavior

The REST handler extracts `action`. On `initialize`, it parses the `mission_config` string into JSON, calls `C2::setMissionConfig()`, then publishes `InitMissionRequest`. On `change_status`, it publishes `ChangeMissionStatusRequest` using the mission id stored by the last initialization.

The node does not do planning, validation, or mission state transitions. It is a bridge only.

## Workflow Examples

### 1. Initialize One Robot Mission

HTTP request:

```json
{
  "action": "initialize",
  "mission_id": "11111111-2222-4333-8444-555555555555",
  "mission_config": "{\"mission_id\":\"11111111-2222-4333-8444-555555555555\",\"behavior\":0,\"vehicles\":[\"f9992bb3-9871-451f-90a0-9207eb9fe6c5\"],\"objective\":{\"geometries\":[{\"geometry\":{\"geometry_type\":\"Point\",\"coordinates\":[4.392430,50.844050]}}]},\"transit\":{\"optimalization\":{\"road_usage\":1.0},\"desired_vehicle_constraints\":{\"max_speed\":1.3}}}"
}
```

ROS message published:

```yaml
topic: /multi_robot/mission_init_request
type: c2_msgs/msg/InitMissionRequest
mission_id: 11111111-2222-4333-8444-555555555555
mission_config: "{...same mission JSON string...}"
```

### 2. Approve The Planned Mission

HTTP request:

```json
{
  "action": "change_status",
  "requested_state": 1
}
```

ROS message published:

```yaml
topic: /multi_robot/change_mission_status_request
mission_id: 11111111-2222-4333-8444-555555555555
mission_request_status: 1
```

The status code `1` means `APPROVE`. The dynamic mission manager later converts that to mission status `ACCEPTED=4`.

### 3. Start The Accepted Mission

HTTP request:

```json
{
  "action": "change_status",
  "requested_state": 2
}
```

ROS message published:

```yaml
topic: /multi_robot/change_mission_status_request
mission_id: 11111111-2222-4333-8444-555555555555
mission_request_status: 2
```

The status code `2` means `START`. Downstream, the mission manager asks the fleet manager to set edge task state to `EXECUTE=1`.

## Gotchas

- The REST `mission_id` field is read, but `C2::setMissionConfig()` stores the mission id from inside `mission_config`.
- `change_status` uses the one mission id currently stored in the node. It is not a multi-mission REST session manager.
- The HTTP response only confirms that the request was published to ROS; it does not mean the mission was planned or started.

