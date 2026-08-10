# /multi_robot/planner/agent

ROS topic `/multi_robot/planner/agent`

| Property | Extracted value |
|---|---|
| Kind | `ros_topic` |
| Interface | `/multi_robot/planner/agent` |
| Type | `centralized_msgs/msg/Agent` |

## Fields

| Section | Type | Name |
|---|---|---|
| message | `string` | `agent_id` |
| message | `string` | `agent_profile` |
| message | `nav_msgs/Odometry` | `odometry` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| publishes | `centralized_msgs/msg/Agent` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:67`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L67) |
| subscribes | `centralized_msgs/msg/Agent` | [`backend/fog/planner/ros2ws/src/planner/planner/planner_node.py:134`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/planner/planner/planner_node.py#L134) |

## Definition evidence

- [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:67`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L67)
- [`backend/fog/planner/ros2ws/src/planner/planner/planner_node.py:134`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/planner/planner/planner_node.py#L134)
