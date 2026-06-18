export AGENT_ID=97ebe7c2_012a_4a3d_b6a5_0e1a355543d0
export AUTONOMY_TOPIC_PREFIX=Themis_Fr

. /opt/ros/humble/setup.bash
. install/local_setup.bash 

export RMW_IMPLEMENTATION="rmw_fastrtps_dynamic_cpp"
export ROS_DOMAIN_ID=112

ros2 run agent_tasks_supervisor swarm_edge_executable agent_$AGENT_ID --ros-args --params-file config_swarm_edge.yaml