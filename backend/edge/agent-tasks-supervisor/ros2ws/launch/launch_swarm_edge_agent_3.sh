export AGENT_ID=2f773e13_5bd9_4829_9816_4c93c0df8b4b
export AUTONOMY_TOPIC_PREFIX=Themis_Es

. /opt/ros/humble/setup.bash
. install/local_setup.bash 

export RMW_IMPLEMENTATION="rmw_fastrtps_dynamic_cpp"
export ROS_DOMAIN_ID=112

ros2 run agent_tasks_supervisor swarm_edge_executable agent_$AGENT_ID --ros-args --params-file config_swarm_edge.yaml