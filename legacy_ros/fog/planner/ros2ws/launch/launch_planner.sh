export ROS_DOMAIN_ID=112
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
. ../install/local_setup.bash
ros2 run planner planner_node --ros-args --params-file config_planner.yaml