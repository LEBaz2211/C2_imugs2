FROM ros:galactic
ENV RMW_IMPLEMENTATION="rmw_fastrtps_dynamic_cpp"

RUN echo 'source /opt/ros/$ROS_DISTRO/setup.bash' >> ~/.bashrc

RUN apt-get update -y
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y nano curl python3 python3-pip
RUN apt install -y ros-$ROS_DISTRO-rmw-fastrtps-cpp ros-$ROS_DISTRO-rmw-fastrtps-dynamic-cpp ros-$ROS_DISTRO-nav2-msgs ros-$ROS_DISTRO-geographic-msgs
RUN apt install -y build-essential gdb