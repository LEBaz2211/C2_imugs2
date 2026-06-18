#!/bin/bash
set -euxo

# Update package list
apt-get update -y

# Install ROS FastRTPS implementation and other ROS dependencies
apt install -y ros-$ROS_DISTRO-rmw-fastrtps-cpp ros-$ROS_DISTRO-rmw-fastrtps-dynamic-cpp ros-$ROS_DISTRO-rmw-cyclonedds-cpp

apt-get install -y python3 python3-pip libboost-all-dev wget nlohmann-json3-dev curl libcpprest-dev

# Install Conan and rosbridge_server requirements
pip3 install conan netifaces pymongo tornado pillow


#!/bin/bash

# Download and install mongo-c-driver
curl -LO https://github.com/KenN7/mongo-builder/releases/download/20240119-c75938f/mongo-c-driver_1.25.4-1_amd64.deb
curl -LO https://github.com/KenN7/mongo-builder/releases/download/20240119-c75938f/mongo-cxx-driver_3.8.1-1_amd64.deb

dpkg -i mongo-c-driver_1.25.4-1_amd64.deb
dpkg -i mongo-cxx-driver_3.8.1-1_amd64.deb
# sudo apt-get -f install  # Install dependencies

# Install additional dependencies
apt-get --yes --force-yes install cmake libssl-dev libsasl2-dev zlib1g-dev systemd

apt-get install -y nano python3-colcon-common-extensions ros-humble-geographic-msgs


# Clean up downloaded .deb file (optional)
rm mongo-cxx-driver_3.8.1-1_amd64.deb
rm mongo-c-driver_1.25.4-1_amd64.deb



