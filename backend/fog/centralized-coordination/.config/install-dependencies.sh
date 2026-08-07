#!/bin/bash
set -euxo

# Update package list
apt-get update -y

# Install ROS FastRTPS implementation and other ROS dependencies
apt install -y ros-$ROS_DISTRO-rmw-fastrtps-cpp ros-$ROS_DISTRO-rmw-fastrtps-dynamic-cpp ros-$ROS_DISTRO-rmw-cyclonedds-cpp

# Install necessary packages for Conan and Boost
apt-get install -y libboost-all-dev wget

# Install Python and pip
apt-get install -y python3 python3-pip

# Install nlohmann-json3-dev
apt-get install -y nlohmann-json3-dev curl

# Install Conan and curl
python3 -m pip install conan


#!/bin/bash

# Download and install mongo-c-driver
curl -LO https://github.com/KenN7/mongo-builder/releases/download/20240119-c75938f/mongo-c-driver_1.25.4-1_amd64.deb
curl -LO https://github.com/KenN7/mongo-builder/releases/download/20240119-c75938f/mongo-cxx-driver_3.8.1-1_amd64.deb

dpkg -i mongo-c-driver_1.25.4-1_amd64.deb
dpkg -i mongo-cxx-driver_3.8.1-1_amd64.deb
# sudo apt-get -f install  # Install dependencies

# Install additional dependencies
apt-get --yes --force-yes install cmake libssl-dev libsasl2-dev zlib1g-dev systemd

# Clean up downloaded .deb file (optional)
rm mongo-cxx-driver_3.8.1-1_amd64.deb
rm mongo-c-driver_1.25.4-1_amd64.deb

# Install MongoDB C++ driver
# apt-get --yes --force-yes install libmongoc-1.0-0 libbson-1.0 cmake libssl-dev libsasl2-dev zlib1g-dev systemd

# wget https://github.com/mongodb/mongo-c-driver/archive/refs/tags/1.25.4.tar.gz
# tar xzf 1.25.4.tar.gz
# cd mongo-c-driver-1.25.4
# mkdir cmake-build
# cd cmake-build
# cmake -DENABLE_AUTOMATIC_INIT_AND_CLEANUP=OFF ..
# make install

# git clone https://github.com/mongodb/mongo-cxx-driver.git --branch releases/stable --depth 1
# cd mongo-cxx-driver/build
# cmake .. -DCMAKE_BUILD_TYPE=Release -DBSONCXX_POLY_USE_MNMLSTC=1 -DCMAKE_INSTALL_PREFIX=/usr/local
# make
# make install
# cd -
# rm -rf mongo-c-driver-1.25.4*


# Install curl and nano and colcon 
apt-get install -y nano python3-colcon-common-extensions ros-humble-geographic-msgs ros-humble-geometry-msgs ros-humble-nav-msgs
