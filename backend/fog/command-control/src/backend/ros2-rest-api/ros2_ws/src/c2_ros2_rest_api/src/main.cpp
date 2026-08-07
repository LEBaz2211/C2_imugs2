#include <rclcpp/rclcpp.hpp>
#include <iostream>
#include "MissionHandler.cpp"
#include "c2_ros2_rest_api/c2_rest.hpp"

int main(int argc, char *argv[]) {
    // Initialize ROS 2
    rclcpp::init(argc, argv);
    
    // Create an rclcpp::Node instance for the C2 node
    auto c2_node = std::make_shared<C2>();
    
    // Set up the REST API URL
    utility::string_t url = U("http://localhost:5001/mission_control");

    // Create the mission handler with the REST listener
    MissionHandler handler(url, c2_node.get());

    // Log the status of the node
    RCLCPP_INFO(c2_node->get_logger(), "Server is running...");

    // Spin the node (this keeps the node running)
    rclcpp::spin(c2_node);

    // Shutdown ROS 2 gracefully
    rclcpp::shutdown();
    return 0;
}
