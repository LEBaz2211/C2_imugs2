# Use the ROS Humble base image
FROM ros:humble-ros-core-jammy


# Set the default shell for the subsequent instructions
SHELL ["/bin/bash", "-c"]

# Copy the script for installing dependencies to the container
COPY .config/install-dependencies.sh /
# Make the script executable
RUN chmod +x /install-dependencies.sh
# Run the script to install dependencies
RUN /install-dependencies.sh

# Set environment variable for the FastRTPS implementation to use
ENV RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
# Set the current prefix for colcon to /app
ENV COLCON_CURRENT_PREFIX=/app
# Set the working directory to /app
WORKDIR /app


# Copy the c2_ros2_rest_api package source code to the container
COPY ros2_ws/src/ c2_ros2_rest_api/ros2_ws/src/

# Copy the testing files for the c2_ros2_rest_api package to the container
COPY test/ c2_ros2_rest_api/test/

# Build ros2 message packages
COPY ros2_ws/src/message_packages c2_ros2_rest_api/ros2_ws/src/message_packages
COPY ros2_ws/src/c2_ros2_rest_api c2_ros2_rest_api/ros2_ws/src/c2_ros2_rest_api
RUN cd c2_ros2_rest_api && \
    . /opt/ros/humble/setup.bash && \
    # . install/setup.bash && \
    colcon build --merge-install --cmake-args '-DCMAKE_BUILD_TYPE=RelWithDebInfo' -Wall -Wextra -Wpedantic

# Copy the entrypoint script to the container
COPY ros2_entrypoint.sh /ros2_entrypoint.sh 
# Make the entrypoint script executable
RUN chmod +x /ros2_entrypoint.sh
# Set the entrypoint of the container to the entrypoint script
ENTRYPOINT ["/ros2_entrypoint.sh"] 

# Set the default command to run bash
CMD ["bash"]