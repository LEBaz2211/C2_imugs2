# /multi_robot/change_mission_vehicle_response

ROS topic `/multi_robot/change_mission_vehicle_response`

| Property | Extracted value |
|---|---|
| Kind | `ros_topic` |
| Interface | `/multi_robot/change_mission_vehicle_response` |
| Type | `c2_msgs/msg/ChangeMissionVehicleResponse` |

## Fields

| Section | Type | Name |
|---|---|---|
| message | `unique_identifier_msgs/UUID` | `mission_id` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| publishes | `c2_msgs/msg/ChangeMissionVehicleResponse` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:61`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L61) |

## Definition evidence

- [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:61`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L61)
