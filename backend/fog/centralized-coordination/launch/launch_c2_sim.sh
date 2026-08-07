. /opt/ros/galactic/setup.bash
. ../install/local_setup.bash 

export C2_INTERFACE_AVOID_ROS_PREFIX=TRUE
export RMW_IMPLEMENTATION="rmw_fastrtps_dynamic_cpp"
export ROS_DOMAIN_ID=112
export MISSION_ID="d346153c-b7e3-439a-d68e-9684b74568ab"

ros2 run centralized_coordination test_c2_sim