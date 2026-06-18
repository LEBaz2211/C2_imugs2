. /opt/ros/humble/setup.bash
. ../install/local_setup.bash 

export C2_INTERFACE_AVOID_ROS_PREFIX=TRUE
export RMW_IMPLEMENTATION="rmw_cyclonedds_cpp"
export ROS_DOMAIN_ID=112
export MISSION_ID="d346153c-b7e3-439a-d68e-9684b74568ab"

ros2 run c2_ros2_rest_api c2_ros2_rest_api