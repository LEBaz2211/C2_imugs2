/****************************************************************/
// Node oRCHE - Mission & vehicles management module
// Emile Le Flecher - RMA - emile.leflecher@mil.be 
// 21.02.2022 - V0.1
/****************************************************************/

#ifndef ORCHESTRATOR_HEADER_HPP
#define ORCHESTRATOR_HEADER_HPP

// standard ros include
#include <cstdio>
#include <rclcpp/rclcpp.hpp>

#include <chrono> // to use sleep_for
#include <unistd.h> // to use sleep
#include <ctime>
#include <rclcpp/callback_group.hpp>


// Other header files:
#include <centralized_coordination/mission_manager_header.hpp>
#include <centralized_coordination/c2_interface_header.hpp>


// Custom libraries 
#include <custom_libraries/mongodb_handler.hpp>
#include <custom_libraries/json_parser.hpp>

// Standard messages
#include <std_msgs/msg/int8.hpp>

// Custom messages & services
// Swarm manager msgs
#include <c2_msgs/json/MissionConfig.hpp>
#include <c2_msgs/msg/mission_feedback.hpp>
#include <c2_msgs/msg/swarm_log.hpp>
#include <centralized_msgs/srv/create_planner.hpp>
#include <centralized_msgs/srv/delete_planner.hpp>

// Custom structures
#include "models.hpp"

using namespace std::chrono_literals;


class Interface;
class OrchestratorNode : public rclcpp::Node
{
private:
  /************** PRIVATE ATTRIBUTES **************/


  // Quality of Service 
  std::string C2_INTERFACE_AVOID_ROS_PREFIX = std::getenv("C2_INTERFACE_AVOID_ROS_PREFIX");
  bool _c2_qos_avoid_ros_prefix = (C2_INTERFACE_AVOID_ROS_PREFIX=="TRUE") ? true : false;

  // for database handling:
  RuntimeDatabase::MongoDbHandler mission_database;
  LogDatabase::MongoDbHandler log_database;
  FeedbackDatabase::MongoDbHandler feedback_database;

  // for testing: 
  centralized_coordination::json_lib::JsonParser _json_parser;
  // nlohmann::json _mission_config_example = this->_json_parser.readJsonFile("src/centralized_coordination/test/json_example/", "mission_config.json");
  // nlohmann::json _mission_feedback = this->_json_parser.readJsonFile("src/centralized_coordination/test/json_example/", "mission_feedback.json");

  
  rclcpp::CallbackGroup::SharedPtr _cb_grp_int;  // callback group for internal processes
  rclcpp::CallbackGroup::SharedPtr _cb_grp_ext;  // callback group for external processes

    // Request Planner creation/deletion (client)
  // rclcpp::Client<centralized_msgs::srv::CreatePlanner>::SharedPtr _create_planner_client;
  rclcpp::Client<centralized_msgs::srv::DeletePlanner>::SharedPtr _delete_planner_client;


  // For Intra process comms with multi agent mission service
  struct clientStructure {
	std::string mission_id;
	rclcpp::Client<c2_msgs::srv::ChangeMissionStatus>::SharedPtr change_mission_status_client_;
  rclcpp::Client<std_srvs::srv::Trigger>::SharedPtr environment_change_client_; 
  rclcpp::Client<std_srvs::srv::Trigger>::SharedPtr vehicle_change_client_;  
  };

  std::list<clientStructure> _clients_struct_list;

  rclcpp::Publisher<c2_msgs::msg::SwarmLog>::SharedPtr _swarm_log_publisher;
  rclcpp::Subscription<c2_msgs::msg::SwarmLog>::SharedPtr _swarm_log_subscriber;


  rclcpp::Service<c2_msgs::srv::ChangeMissionStatus>::SharedPtr _delete_mission_server;
  rclcpp::Service<std_srvs::srv::Trigger>::SharedPtr _cmd_server;


  std::shared_ptr<OrchestratorNode> _swarm_manager_node_ptr;
  std::shared_ptr<Interface> _interface_node_ptr;

  rclcpp::TimerBase::SharedPtr _timer;
  std::list<std::string> _list_active_mission;
  std::vector<std::string> _initialized_missions;

  bool _firstloop = true; // Flag for first timer loop callback

  
   /************** PRIVATE METHODS **************/
  void _initRosParameters();
  void _initIntraProcessComms();
  void _initPlannerInterface();
  void _init_C2_interface();
  void _initCmdServices();

  void _TimerLoop();
  InterfaceC2State _updateC2InterfaceState();
  void _managerActions(InterfaceC2State c2_interface);

  void _createMissionManagerNode(std::string mission_id, bool existing_mission);
  void _spinNode(std::shared_ptr<MissionManager> MissionManager_node);
  void _recoverMissionsFromDatabase();
  void _addMission(nlohmann::json mission_config);
  void _addMission(const std::string mission_id, const c2_msgs::json::MissionConfig mission_config);
  void _deletePlanner(std::string mission_id);
  void _addVehiclesToMission(std::string mission_id, std::vector<std::string> vehicles);
  void _deleteVehiclesFromMission(std::string mission_id, std::vector<std::string> vehicles);
  void _commandService_callback(const std_srvs::srv::Trigger::Request::SharedPtr request, std_srvs::srv::Trigger::Response::SharedPtr response);
  void _deleteMission_callback(const c2_msgs::srv::ChangeMissionStatus::Request::SharedPtr request, c2_msgs::srv::ChangeMissionStatus::Response::SharedPtr response);
  void _changeMissionStatus(std::string mission_id, int requested_status);
  
  void _vehicleChange(std::string mission_id);
  void _publishSwarmLog(int log_type, std::string mission_id, std::string log_message);
  void _swarm_log_subscriber_callback(const c2_msgs::msg::SwarmLog::SharedPtr msg);
  void _createMissionFeedback(const std::string mission_id, const c2_msgs::json::MissionConfig mission_config);

  clientStructure _getClientStructure(std::string mission_id);
  

public:
  /************** PUBLIC METHODS **************/
  OrchestratorNode();
  ~OrchestratorNode();
  void print_from_manager(std::string message);
  void setRequestMissionChangeStatus(const std::string mission_id, const c2_msgs::json::enums::MissionStatusRequest status_request);
  int getMissionStatus(const std::string mission_id);
  void _environmentChange();
  std::vector<std::string> getFeedbacks();
  void setInterfacePtr(std::shared_ptr<Interface> ptr);
  std::shared_ptr<OrchestratorNode> get_ptr();
  
};



#endif // ORCHESTRATOR_HEADER_HPP
