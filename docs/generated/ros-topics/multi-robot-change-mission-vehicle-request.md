# /multi_robot/change_mission_vehicle_request

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

ROS topic `/multi_robot/change_mission_vehicle_request`

| Property | Extracted value |
|---|---|
| Kind | `ros_topic` |
| Interface | `/multi_robot/change_mission_vehicle_request` |
| Type | `c2_msgs/msg/ChangeMissionVehicleRequest` |

## Fields

| Section | Type | Name |
|---|---|---|
| message | `unique_identifier_msgs/UUID` | `mission_id` |
| message | `string[]` | `vehicule_id_list` |
| message | `uint8` | `vehicle_changes` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| subscribes | `c2_msgs/msg/ChangeMissionVehicleRequest` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:60`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L60) |

## Definition evidence

- [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:60`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L60)
