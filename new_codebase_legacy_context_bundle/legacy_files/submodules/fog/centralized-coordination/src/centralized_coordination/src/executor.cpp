/****************************************************************/
// Central Coordination - Executor
// Alexandre La Grappe & Emile Le Flecher  - RMA - alexandre.lagrappe@mil.be or emile.leflecher@mil.be 
// 03.12.2024 - V1.0
/****************************************************************/

// Header Files:
#include <centralized_coordination/orchestrator_header.hpp>
#include <centralized_coordination/c2_interface_header.hpp>
#include <centralized_coordination/fleet_manager_header.hpp>

// Custom libraries:
#include <custom_libraries/mongodb_handler.hpp>

int main(int argc, char **argv)
{
  // Initialize ROS
  rclcpp::init(argc, argv);
  std::cout << "Centralized Coordination Executor -----> Initialization" << std::endl;

  // Initialize MongoDB
  mongocxx::instance instance;

  // Create a MultiThreadedExecutor to run multiple nodes in parallel
  auto executor_ptr = std::make_shared<rclcpp::executors::MultiThreadedExecutor>();

  // Create the three nodes that make up the Centralized Coordination
  auto swarm_manager_node = std::make_shared<OrchestratorNode>();
  auto interface_node = std::make_shared<Interface>();
  auto fleet_manager_node = std::make_shared<FleetManagerNode>();

  // Set up pointers between the nodes
  swarm_manager_node->setInterfacePtr(interface_node);
  interface_node->setOrchestratorPtr(swarm_manager_node);

  // Add the nodes to the executor
  executor_ptr->add_node(interface_node);
  executor_ptr->add_node(swarm_manager_node);
  executor_ptr->add_node(fleet_manager_node);

  // Start the executor
  executor_ptr->spin();

  // Clean up and shut down ROS
  std::cout << "Centralized Coordination Executor -----> shutdown" << std::endl;
  rclcpp::shutdown();

  return 0;
}