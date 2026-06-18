cmake_minimum_required(VERSION 3.8)
project(environment_msgs)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic -std=c++2a)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(std_msgs REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(unique_identifier_msgs REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/EnvironmentDataResetRequest.msg"
  "msg/EnvironmentDataResetResponse.msg"
  "msg/EnvironmentDataGetVersionRequest.msg"
  "msg/EnvironmentDataGetVersionResponse.msg"
  "msg/EnvironmentDataUploadRequest.msg"
  "msg/EnvironmentDataUploadResponse.msg"

  "srv/EnvironmentDataReset.srv"
  "srv/EnvironmentDataGetVersion.srv"
  "srv/EnvironmentDataUpload.srv"

  DEPENDENCIES unique_identifier_msgs
)

# install json parsing headers
# INSTALL(DIRECTORY ${CMAKE_CURRENT_LIST_DIR}/json/ DESTINATION /opt/ros/$ENV{ROS_DISTRO}/include/${PROJECT_NAME}/json
#         FILES_MATCHING PATTERN "*.h*")
# INSTALL(DIRECTORY ${CMAKE_CURRENT_LIST_DIR}/json/ DESTINATION include/${PROJECT_NAME}/json
#         FILES_MATCHING PATTERN "*.h*")

install(DIRECTORY json/
  DESTINATION /usr/local/include/${PROJECT_NAME}/json
  # FILES_MATCHING PATTERN "*.hpp"
)


if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  # the following line skips the linter which checks for copyrights
  # uncomment the line when a copyright and license is not present in all source files
  set(ament_cmake_copyright_FOUND TRUE)
  set(ament_cmake_flake8_FOUND TRUE)
  set(ament_cmake_pep257_FOUND TRUE)
  set(ament_cmake_cppcheck_FOUND TRUE)
  set(ament_cmake_cpplint_FOUND TRUE)
  set(ament_cmake_lint_cmake_FOUND TRUE)
  set(ament_cmake_linter_FOUND TRUE)
  set(ament_cmake_xmllint_FOUND TRUE)
  set(ament_cmake_uncrustify_FOUND TRUE)

  # the following line skips cpplint (only works in a git repo)
  # uncomment the line when this package is not in a git repo
  #set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()

  # Add a gtest named ${PROJECT_NAME}_my_test
  # include_directories(test)
  # find_package(ament_cmake_gtest REQUIRED)
  # ament_add_gtest(test_unit_json_parse test/ParsingUnitTests.cpp)
endif()

ament_package()

