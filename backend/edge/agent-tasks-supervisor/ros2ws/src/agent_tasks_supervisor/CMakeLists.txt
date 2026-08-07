cmake_minimum_required(VERSION 3.8)
project(agent_tasks_supervisor)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()


include_directories(include
                    /usr/local/include/nlohmann
                    /opt/ros/humble/include/
                    lib)
# find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclpy REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(std_msgs REQUIRED)
find_package(std_srvs REQUIRED)

find_package(task_msgs REQUIRED)
find_package(autonomy_msgs REQUIRED)

find_package(unique_identifier_msgs REQUIRED)
find_package(geographic_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
# find_package(autonomy_srv_msg_pkg REQUIRED)
# find_package(utils REQUIRED)


add_executable(swarm_edge_executable src/agent_tasks_supervisor_node.cpp)



target_include_directories(swarm_edge_executable PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>)
target_compile_features(swarm_edge_executable PUBLIC c_std_99 cxx_std_17)  # Require C99 and C++17
ament_target_dependencies(
  swarm_edge_executable
  "rclcpp"
  "rclpy"

  "task_msgs"
  "autonomy_msgs"

  "std_srvs"
  "std_msgs"
  "geometry_msgs"
  "geographic_msgs"
  "nav_msgs"
  "unique_identifier_msgs"
)

# Simulating nodes for testing:
#---------------------------------

add_executable(test_autonomy_sim src/test/test_autonomy.cpp)
target_include_directories(test_autonomy_sim PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>)

target_compile_features(test_autonomy_sim PUBLIC c_std_99 cxx_std_17)  # Require C99 and C++17
ament_target_dependencies(
  test_autonomy_sim
  "rclcpp"
  "rclpy"

  "task_msgs"
  "autonomy_msgs"


  "std_srvs"
  "std_msgs"
  "geographic_msgs"
  "nav_msgs"
  "unique_identifier_msgs"
)

install(TARGETS swarm_edge_executable test_autonomy_sim
  DESTINATION lib/${PROJECT_NAME})

install(
  FILES bridge_mapping_rules.yaml
  DESTINATION share/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)

  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
