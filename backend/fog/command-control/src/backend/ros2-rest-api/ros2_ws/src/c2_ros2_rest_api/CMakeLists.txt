cmake_minimum_required(VERSION 3.8)
project(c2_ros2_rest_api)


# Compiler settings
if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic -std=c++17)
endif()

# Find dependencies
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_ros REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclpy REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(std_msgs REQUIRED)
find_package(std_srvs REQUIRED)
find_package(c2_msgs REQUIRED)
find_package(environment_msgs REQUIRED)
find_package(nlohmann_json REQUIRED)



find_package(Boost REQUIRED)
find_package(cpprestsdk REQUIRED)
find_package(OpenSSL REQUIRED)

# Include directories
include_directories(
  include
  /usr/local/bin/include
  /opt/ros/humble/include
  ${CMAKE_SOURCE_DIR}/install/c2_msgs/include
  ${CMAKE_SOURCE_DIR}/install/centralized_msgs/include
  ${CMAKE_SOURCE_DIR}/install/swarm_client_msgs/include
)


# Add executable
add_executable(c2_ros2_rest_api
  src/main.cpp
  src/c2_rest.cpp
  src/MissionHandler.cpp
)
target_include_directories(c2_ros2_rest_api PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)
# target_link_libraries(${PROJECT_NAME} )
target_link_libraries(${PROJECT_NAME} cpprest OpenSSL::SSL OpenSSL::Crypto)

# Link against ROS 2 libraries and cpprestsdk
ament_target_dependencies(c2_ros2_rest_api
  rclcpp
  cpprestsdk
  Boost
  rclpy
  c2_msgs
  environment_msgs
  nlohmann_json
)
# target_link_libraries(${PROJECT_NAME} PRIVATE cpprestsdk::cpprestsdk)

# Install targets
install(TARGETS c2_ros2_rest_api
  DESTINATION lib/${PROJECT_NAME})

# Add ament_cmake
ament_package()
