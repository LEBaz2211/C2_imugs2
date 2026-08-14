# /multi_robot/mission_init_response

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

ROS topic `/multi_robot/mission_init_response`

| Property | Extracted value |
|---|---|
| Kind | `ros_topic` |
| Interface | `/multi_robot/mission_init_response` |
| Type | `c2_msgs/msg/InitMissionResponse` |

## Fields

| Section | Type | Name |
|---|---|---|
| message | `unique_identifier_msgs/UUID` | `mission_id` |
| message | `string<=10000` | `mission_feedback` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| publishes | `c2_msgs/msg/InitMissionResponse` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:55`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L55) |
| subscribes | `c2_msgs/msg/InitMissionResponse` | [`backend/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/c2_rest.cpp:54`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/c2_rest.cpp#L54) |

## Definition evidence

- [`backend/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/c2_rest.cpp:54`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/c2_rest.cpp#L54)
- [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:55`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L55)
