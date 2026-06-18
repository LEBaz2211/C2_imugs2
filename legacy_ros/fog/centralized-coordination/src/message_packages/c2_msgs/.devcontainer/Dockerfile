FROM ros:galactic
ENV RMW_IMPLEMENTATION="rmw_fastrtps_dynamic_cpp"

RUN echo 'source /opt/ros/$ROS_DISTRO/setup.bash' >> ~/.bashrc

RUN apt update
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y nano curl python3 python3-pip

RUN curl -s https://packagecloud.io/install/repositories/dotocean/imugs/script.deb.sh | sudo bash

RUN apt update
RUN apt install -y ros-$ROS_DISTRO-rmw-fastrtps-cpp ros-$ROS_DISTRO-rmw-fastrtps-dynamic-cpp ros-$ROS_DISTRO-nav2-msgs
RUN apt install -y build-essential gdb
RUN apt install -y ros-$ROS_DISTRO-swarm-planner-msgs ros-$ROS_DISTRO-swarm-client-msgs

