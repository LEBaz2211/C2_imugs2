FROM ros:humble-ros-core-jammy


# Set the default shell for the subsequent instructions
SHELL ["/bin/bash", "-c"]

# Copy the script for installing dependencies to the container
COPY .config/install-dependencies.sh /
# Make the script executable
RUN chmod +x /install-dependencies.sh
# Run the script to install dependencies
RUN /install-dependencies.sh


ENV RMW_IMPLEMENTATION="rmw_cyclonedds_cpp"

# Set the current prefix for colcon to /app
ENV COLCON_CURRENT_PREFIX=/app
# Set the working directory to /app
WORKDIR /app

# Build ros2 message packages
COPY ros2ws/src ros2ws/src
RUN cd ros2ws && \
    . /opt/ros/humble/setup.bash && \
    colcon build --merge-install --cmake-args '-DCMAKE_BUILD_TYPE=RelWithDebInfo' -Wall -Wextra -Wpedantic

# setup entrypoint
COPY ros_entrypoint.sh / 
RUN chmod +x /ros_entrypoint.sh
ENTRYPOINT ["/ros_entrypoint.sh"] 

CMD ["bash"]