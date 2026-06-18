#!/bin/bash
set -euxo pipefail

# ROS INSTALLATION
# -----------------
echo "Installing ROS dependencies..."
apt-get update -y
apt-get install -y \
  ros-$ROS_DISTRO-rmw-cyclonedds-cpp \
  ros-$ROS_DISTRO-geographic-msgs \
  ros-$ROS_DISTRO-rosbridge-server \
  libboost-all-dev \
  python3-colcon-common-extensions \
  python3 \
  python3-pip \
  nlohmann-json3-dev \
  libcpprest-dev

echo "Installing Python dependencies..."
python3 -m pip install --no-cache-dir --upgrade pip
python3 -m pip install conan netifaces pymongo tornado pillow

apt-get clean && rm -rf /var/lib/apt/lists/*

echo "Installation complete."
