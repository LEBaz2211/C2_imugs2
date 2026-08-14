# /multi_robot/mission_init_request

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

ROS topic `/multi_robot/mission_init_request`

| Property | Extracted value |
|---|---|
| Kind | `ros_topic` |
| Interface | `/multi_robot/mission_init_request` |
| Type | `c2_msgs/msg/InitMissionRequest` |

## Fields

| Section | Type | Name |
|---|---|---|
| message | `unique_identifier_msgs/UUID` | `mission_id` |
| message | `string<=10000` | `mission_config` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| publishes | `c2_msgs/msg/InitMissionRequest` | [`backend/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/c2_rest.cpp:55`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/c2_rest.cpp#L55) |
| subscribes | `c2_msgs/msg/InitMissionRequest` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:54`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L54) |

## Verified one-robot navigation data

These payloads come from the [runtime-verified one-robot Point-navigation example](../examples/single-robot-point-navigation.md) using mission `44444444-5555-4666-8777-888888888888` and `Themis Fr`.

### Mission initialization on ROS

!!! success "Verified Flow"
    Phase: INIT.

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
  "mission_config": "{\"mission_id\":\"44444444-5555-4666-8777-888888888888\",\"behavior\":0,\"vehicles\":[\"f9992bb3-9871-451f-90a0-9207eb9fe6c5\"],\"objective\":{\"geometries\":[{\"geometry\":{\"geometry_type\":\"Point\",\"coordinates\":[4.39167,50.84417]}}]},\"transit\":{\"optimalization\":{\"road_usage\":1.0},\"desired_vehicle_constraints\":{\"max_speed\":1.3}}}"
}
```

- mission_config is a JSON-encoded string and uses the legacy key optimalization.
- The UUID byte array decodes to 44444444-5555-4666-8777-888888888888.

Example evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:108`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L108)

## Definition evidence

- [`backend/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/c2_rest.cpp:55`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/c2_rest.cpp#L55)
- [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:54`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L54)
