# /multi_robot/change_mission_status_request

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

ROS topic `/multi_robot/change_mission_status_request`

| Property | Extracted value |
|---|---|
| Kind | `ros_topic` |
| Interface | `/multi_robot/change_mission_status_request` |
| Type | `c2_msgs/msg/ChangeMissionStatusRequest` |

## Fields

| Section | Type | Name |
|---|---|---|
| message | `unique_identifier_msgs/UUID` | `mission_id` |
| message | `uint8` | `mission_request_status` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| publishes | `c2_msgs/msg/ChangeMissionStatusRequest` | [`backend/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/c2_rest.cpp:58`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/c2_rest.cpp#L58) |
| subscribes | `c2_msgs/msg/ChangeMissionStatusRequest` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:57`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L57) |

## Verified one-robot navigation data

These payloads come from the [runtime-verified one-robot Point-navigation example](../examples/single-robot-point-navigation.md) using mission `44444444-5555-4666-8777-888888888888` and `Themis Fr`.

### APPROVE status request

!!! success "Verified Flow"
    Phase: APPROVE.

```json
{
  "mission_id": {
    "uuid": [
      68,
      68,
      68,
      68,
      85,
      85,
      70,
      102,
      135,
      119,
      136,
      136,
      136,
      136,
      136,
      136
    ]
  },
  "mission_request_status": 1
}
```

Example evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:718`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L718)

### START status request

!!! success "Verified Flow"
    Phase: START.

```json
{
  "mission_id": {
    "uuid": [
      68,
      68,
      68,
      68,
      85,
      85,
      70,
      102,
      135,
      119,
      136,
      136,
      136,
      136,
      136,
      136
    ]
  },
  "mission_request_status": 2
}
```

Example evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:796`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L796)

## Definition evidence

- [`backend/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/c2_rest.cpp:58`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/c2_rest.cpp#L58)
- [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:57`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L57)
