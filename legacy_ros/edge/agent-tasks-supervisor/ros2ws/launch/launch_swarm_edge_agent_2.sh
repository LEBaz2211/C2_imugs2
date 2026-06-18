export AGENT_ID=88fda1d0_7c6a_44a7_9e64_c923a1a5c091
export AUTONOMY_TOPIC_PREFIX=Themis_Ge

. /opt/ros/humble/setup.bash
. install/local_setup.bash 

export RMW_IMPLEMENTATION="rmw_fastrtps_dynamic_cpp"
export ROS_DOMAIN_ID=112

# Replace agent_id_key of config file with node name
cp /app/config.yaml /app/new_config.yaml
sed -i 's@agent_id_key@'"agent_$AGENT_ID"'@' /app/new_config.yaml

echo $AGENT_ID
cat config_swarm_edge.yaml
ros2 run agent_tasks_supervisor swarm_edge_executable agent_$AGENT_ID --ros-args --params-file config_swarm_edge.yaml