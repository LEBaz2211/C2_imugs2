FROM ros:humble-ros-core-jammy

WORKDIR /app

# Copy the script for installing dependencies to the container
COPY .config/install_dependencies.sh /
# Make the script executable
RUN chmod +x /install_dependencies.sh
# Run the script to install dependencies
RUN /install_dependencies.sh


# set ROS RMW implementation
ENV RMW_IMPLEMENTATION="rmw_cyclonedds_cpp"

COPY ros2ws/src /app/ros2ws/src
# Build path planning library
RUN chmod +x /app/ros2ws/src/path_planning_lib/build_lib.sh && /app/ros2ws/src/path_planning_lib/build_lib.sh
# Build ros2 workspace
RUN . /opt/ros/humble/setup.sh && \ 
cd /app/ros2ws && \
colcon build

# Copy the entrypoint script to the container
COPY ros2_entrypoint.sh /ros2_entrypoint.sh 
# Make the entrypoint script executable
RUN chmod +x /ros2_entrypoint.sh
# Set the entrypoint of the container to the entrypoint script
ENTRYPOINT ["/ros2_entrypoint.sh"] 

# Set the default command to run bash
CMD ["bash"]
