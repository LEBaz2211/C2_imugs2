. /opt/ros/galactic/setup.bash
. ros2ws/install/local_setup.bash 

cp /app/autonomy_config.yaml /app/new_autonomy_config.yaml
sed -i 's@autonomy_id_key@'"autonomy_test_node_$AUTONOMY_TOPIC_PREFIX"'@' /app/new_autonomy_config.yaml

ros2 run agent_tasks_supervisor test_autonomy_sim autonomy_test_node_$AUTONOMY_TOPIC_PREFIX --ros-args --params-file /app/new_autonomy_config.yaml
