cmake_minimum_required(VERSION 3.8)
project(centralized_coordination)

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
find_package(nav_msgs REQUIRED)

find_package(c2_msgs REQUIRED)
find_package(task_msgs REQUIRED)
find_package(centralized_msgs REQUIRED)
find_package(environment_msgs REQUIRED)

find_package(mongocxx REQUIRED)
find_package(bsoncxx REQUIRED)
find_package(nlohmann_json REQUIRED)

# Include directories
include_directories(
  include
  /usr/include/mongocxx/v_noabi
  /usr/include/bsoncxx/v_noabi
  /usr/local/bin/include
  /opt/ros/humble/include
  ${c2_msgs_INCLUDE_DIRS}
  ${CMAKE_SOURCE_DIR}/install/c2_msgs/include
  ${CMAKE_SOURCE_DIR}/install/centralized_msgs/include
)

# Executable definition
add_executable(centralized_coordination_executable 
  src/executor 
  src/orchestrator_node.cpp 
  src/fleet_manager_node.cpp 
  src/c2_interface_node.cpp 
  src/mission_manager.cpp
)

# Target include directories
target_include_directories(centralized_coordination_executable PUBLIC
  $<BUILD_INTERFACE:${CMAKE_SOURCE_DIR}/src/centralized_coordination/include>
  $<INSTALL_INTERFACE:include>
  ${CMAKE_SOURCE_DIR}/install/c2_msgs/include
  ${CMAKE_SOURCE_DIR}/install/c2_msgs/include/c2_msgs
)

ament_target_dependencies(centralized_coordination_executable
  rclcpp
  c2_msgs
  nav_msgs
)


# Link necessary libraries
target_link_libraries(centralized_coordination_executable 
  mongocxx 
  bsoncxx 
  nlohmann_json
)

# Set compile features (C++17 and C99)
target_compile_features(centralized_coordination_executable PUBLIC c_std_99 cxx_std_17)

# Ament dependencies for the executable
ament_target_dependencies(
  centralized_coordination_executable
  rclcpp
  rclpy

  environment_msgs
  c2_msgs
  task_msgs
  centralized_msgs

  std_msgs
  std_srvs
  geometry_msgs
  nav_msgs
  mongocxx
  bsoncxx
  nlohmann_json
)

# Simulating nodes for testing
#---------------------------------

# Test node 1: C2 Simulator
add_executable(test_c2_sim test/test_c2.cpp)
target_include_directories(test_c2_sim PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)
target_compile_features(test_c2_sim PUBLIC c_std_99 cxx_std_17)
ament_target_dependencies(
  test_c2_sim
  rclcpp
  rclpy
  
  environment_msgs
  c2_msgs
  centralized_msgs

  nlohmann_json
)

# Test node 2: Swarm Planner Simulator
add_executable(test_planner_sim test/test_planner.cpp)
target_include_directories(test_planner_sim PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)
target_compile_features(test_planner_sim PUBLIC c_std_99 cxx_std_17)
ament_target_dependencies(
  test_planner_sim
  rclcpp
  rclpy

  environment_msgs
  c2_msgs
  task_msgs
  centralized_msgs

  nlohmann_json
)

# Install directives
install(
  DIRECTORY launch
  DESTINATION share/${PROJECT_NAME}
)

install(
  TARGETS centralized_coordination_executable test_c2_sim test_planner_sim
  DESTINATION lib/${PROJECT_NAME}
)

# Optional testing setup
if(BUILD_TESTING)
  # Add testing dependencies here
endif()

# Finalize package
ament_package()


