export AUTONOMY_TOPIC_PREFIX=Themis_Fr

. /opt/ros/galactic/setup.bash
. install/local_setup.bash 

export RMW_IMPLEMENTATION="rmw_fastrtps_dynamic_cpp"
export ROS_DOMAIN_ID=112

ros2 run agent_tasks_supervisor test_autonomy_sim autonomy_test_node_$AUTONOMY_TOPIC_PREFIX --ros-args --params-file config_autonomy.yaml