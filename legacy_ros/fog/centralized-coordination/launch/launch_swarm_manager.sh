. /opt/ros/galactic/setup.bash
. ../install/local_setup.bash 

export C2_INTERFACE_AVOID_ROS_PREFIX=FALSE
export MONGODB_CONNSTRING=mongodb://127.0.0.1:27017
export RMW_IMPLEMENTATION="rmw_fastrtps_dynamic_cpp"
export ROS_DOMAIN_ID=112

# sudo systemctl start mongod

ros2 run centralized_coordination centralized_coordination_executable --ros-args --params-file config_centralized_coordination.yaml 