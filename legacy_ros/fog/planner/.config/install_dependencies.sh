#!/bin/bash
set -euxo pipefail

apt-get update -y

# Install ROS FastRTPS implementation and other ROS dependencies
apt-get install -y ros-$ROS_DISTRO-rmw-fastrtps-cpp ros-$ROS_DISTRO-rmw-fastrtps-dynamic-cpp ros-$ROS_DISTRO-rmw-cyclonedds-cpp

# Install other ROS dependencies
apt-get install -y ros-$ROS_DISTRO-geographic-msgs ros-$ROS_DISTRO-nav-msgs


# Install Python and pip
apt-get install -y python3 python3-pip python3-colcon-common-extensions

apt update
apt install -y python3-opencv libopencv-dev ros-${ROS_DISTRO}-cv-bridge
python3 -m pip install --no-cache-dir --upgrade pip
python3 -m pip install --no-cache-dir "numpy<2" osmnx==1.9.2 libpysal==4.10 matplotlib==3.8.4 pymongo==4.10.1 gurobipy ortools
python3 -m pip install --no-cache-dir --force-reinstall "numpy<2"

# Fields2Cover Dependencies:
apt-get update
apt-get install -y --no-install-recommends software-properties-common
add-apt-repository ppa:ubuntugis/ppa
apt-get update
apt-get install -y --no-install-recommends build-essential ca-certificates cmake \
        doxygen g++ git libeigen3-dev libgdal-dev libpython3-dev python3 python3-pip \
        python3-matplotlib python3-tk lcov libgtest-dev libtbb-dev swig libgeos-dev \
        gnuplot libtinyxml2-dev nlohmann-json3-dev
python3 -m pip install gcovr
