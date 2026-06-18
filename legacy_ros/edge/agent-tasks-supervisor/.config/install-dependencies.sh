#!/bin/bash

export DEBIAN_FRONTEND=noninteractive

# Update package list
apt-get update -y

# Install ROS FastRTPS implementation 
apt install -y ros-$ROS_DISTRO-rmw-fastrtps-cpp ros-$ROS_DISTRO-rmw-fastrtps-dynamic-cpp ros-$ROS_DISTRO-rmw-cyclonedds-cpp

# Install other ROS dependencies
apt-get install -y ros-$ROS_DISTRO-geographic-msgs ros-$ROS_DISTRO-nav-msgs

# Install Python, pip and boost
apt-get install -y python3 python3-pip libboost-all-dev

# Install nlohmann-json3-dev
apt-get install -y nlohmann-json3-dev

# Install curl and nano
apt-get install -y curl nano python3-colcon-common-extensions

# clean up the local package index files
rm -rf /var/lib/apt/lists/* 