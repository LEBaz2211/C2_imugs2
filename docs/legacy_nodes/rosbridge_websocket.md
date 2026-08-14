# `/rosbridge_websocket`

> **Documentation label: REFERENCE** — frozen comparison-runtime gateway evidence.

## Purpose

`/rosbridge_websocket` exposes the ROS graph over WebSocket on `ws://localhost:9090`. In this project it is a diagnostics and live-read gateway. The browser UI should still send mission commands through the FastAPI adapter and old REST bridge, not construct ROS mission messages directly.

Source/runtime:

```text
docker-compose.legacy-ros.yml
ros2 launch rosbridge_server rosbridge_websocket_launch.xml
```

## Inputs

| Input | Type | Meaning |
| --- | --- | --- |
| WebSocket messages | rosbridge protocol JSON | Subscribe/unsubscribe/publish/call_service requests |
| ROS graph | ROS topics/services | All visible topics/services in `ROS_DOMAIN_ID=112` |

## Outputs

| Output | Type | Meaning |
| --- | --- | --- |
| WebSocket messages | rosbridge protocol JSON | Topic messages, service responses, status/errors |

## Internal Behavior

Rosbridge is generic middleware. It does not understand missions, planners, agents, or task states. It serializes ROS messages to JSON and sends them over a WebSocket. Its value here is that the UI/backend can inspect live legacy topics such as mission feedback, planner state, and edge feedback without embedding a ROS 2 client in the browser.

## Workflow Examples

### 1. Subscribe To Mission Feedback

WebSocket request:

```json
{
  "op": "subscribe",
  "topic": "/multi_robot/mission_feedback",
  "type": "c2_msgs/msg/MissionFeedback"
}
```

Example message:

```json
{
  "op": "publish",
  "topic": "/multi_robot/mission_feedback",
  "msg": {
    "mission_id": {"uuid": [17, 17, 17, 17, 34, 34, 67, 51, 132, 68, 85, 85, 85, 85, 85, 85]},
    "mission_feedback": "{\"mission_id\":\"11111111-2222-4333-8444-555555555555\",\"behavior\":0,\"status\":1,\"requested_status\":0,\"date\":\"2026-07-01T12:00:00Z\",\"tasks\":[{\"vehicle_id\":\"f9992bb3-9871-451f-90a0-9207eb9fe6c5\",\"waypoints\":[{\"coordinates\":[50.844050,4.392430],\"average_speed\":1.3,\"eta\":\"2026-07-01T12:01:00Z\"}]}]}"
  }
}
```

The useful payload is the nested JSON string in `mission_feedback`.

### 2. Subscribe To Planner State

WebSocket request:

```json
{
  "op": "subscribe",
  "topic": "/multi_robot/planner/state",
  "type": "std_msgs/msg/String"
}
```

Example message:

```json
{
  "op": "publish",
  "topic": "/multi_robot/planner/state",
  "msg": {
    "data": "{\"planners\":[{\"mission_id\":\"11111111-2222-4333-8444-555555555555\",\"state\":2}]}"
  }
}
```

Planner state `2` means the planner says a cached plan is ready. It is not by itself proof that mission feedback contains usable waypoint tasks.

### 3. Subscribe To Edge Feedback

WebSocket request:

```json
{
  "op": "subscribe",
  "topic": "/multi_robot/edge/feedback",
  "type": "task_msgs/msg/Feedback"
}
```

Example message:

```json
{
  "op": "publish",
  "topic": "/multi_robot/edge/feedback",
  "msg": {
    "agent_id": "f9992bb3-9871-451f-90a0-9207eb9fe6c5",
    "state": 1,
    "tasks": [
      {
        "task_id": "6d2f54a2-a6fd-439a-b5af-a771e53c6e11",
        "task_state": 1,
        "current_objective_id": "31f65b58-e010-4838-9b79-cfb31ef8a84f"
      }
    ],
    "odometry": {
      "header": {"frame_id": "map"},
      "pose": {"pose": {"position": {"x": 4.392500, "y": 50.844150, "z": 0.0}}}
    }
  }
}
```

## Gotchas

- Rosbridge is not the mission brain. It should not replace the backend adapter or old REST bridge for mission commands.
- UUIDs can appear as byte arrays in rosbridge JSON, while many JSON payload strings use normal UUID strings.
- Several ROS messages contain nested JSON strings. The receiver often needs to parse twice.
- If rosbridge shows no messages, first confirm the legacy containers share the expected `ROS_DOMAIN_ID=112` and `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`.
