# /multi_robot/change_mission_status_response

ROS topic `/multi_robot/change_mission_status_response`

| Property | Extracted value |
|---|---|
| Kind | `ros_topic` |
| Interface | `/multi_robot/change_mission_status_response` |
| Type | `c2_msgs/msg/ChangeMissionStatusResponse` |

## Fields

| Section | Type | Name |
|---|---|---|
| message | `unique_identifier_msgs/UUID` | `mission_id` |
| message | `uint8` | `mission_status` |
| message | `string<=2000` | `error_message` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| publishes | `c2_msgs/msg/ChangeMissionStatusResponse` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:58`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L58) |
| publishes | `c2_msgs/msg/ChangeMissionStatusResponse` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:137`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L137) |
| subscribes | `c2_msgs/msg/ChangeMissionStatusResponse` | [`backend/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/c2_rest.cpp:57`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/c2_rest.cpp#L57) |

## Definition evidence

- [`backend/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/c2_rest.cpp:57`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/c2_rest.cpp#L57)
- [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:137`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L137)
- [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:58`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L58)
