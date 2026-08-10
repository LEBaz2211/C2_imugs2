# /multi_robot/change_mission_status_request

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

## Definition evidence

- [`backend/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/c2_rest.cpp:58`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/c2_rest.cpp#L58)
- [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:57`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L57)
