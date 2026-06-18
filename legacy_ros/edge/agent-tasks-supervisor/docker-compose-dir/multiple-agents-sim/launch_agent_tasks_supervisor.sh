. /opt/ros/galactic/setup.bash
. ros2ws/install/local_setup.bash 

# Replace agent_id_key of config file with node name
cp /app/config.yaml /app/new_config.yaml
sed -i 's@agent_id_key@'"agent_$AGENT_ID"'@' /app/new_config.yaml

ros2 run agent_tasks_supervisor swarm_edge_executable agent_$AGENT_ID --ros-args --params-file /app/new_config.yaml