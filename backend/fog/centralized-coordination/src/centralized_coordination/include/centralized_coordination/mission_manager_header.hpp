/****************************************************************/
// Central Coordination - Mission Manager header
// Alexandre La Grappe & Emile Le Flecher  - RMA - alexandre.lagrappe@mil.be or emile.leflecher@mil.be 
// 03.12.2024 - V1.0
/****************************************************************/

#ifndef RUNTIME_SWARM_H
#define RUNTIME_SWARM_H

// standard ros include
#include <cstdio>
#include "rclcpp/rclcpp.hpp"
#include <chrono>
#include <stdexcept>
#include <unistd.h> // to use sleep
#include <boost/range/irange.hpp>
#include <boost/uuid/uuid.hpp>            // uuid class
#include <boost/uuid/uuid_generators.hpp> // generators
#include <boost/uuid/uuid_io.hpp>         // streaming operators etc.

// Custom libraries 
#include <custom_libraries/mongodb_handler.hpp>
#include <custom_libraries/uuid_library.hpp>
#include <custom_libraries/json_parser.hpp>

// Standard messages & services
#include <std_srvs/srv/trigger.hpp>
#include <std_msgs/msg/string.hpp>
#include <std_msgs/msg/int8.hpp>
#include <std_msgs/msg/empty.hpp>

#include <geometry_msgs/msg/pose.hpp>
#include <geometry_msgs/msg/twist.hpp>

// Custom messages & services
// Swarm manager msgs
#include <c2_msgs/json/MissionFeedback.hpp>
#include <c2_msgs/json/MissionConfig.hpp>
#include <c2_msgs/json/EnumsTools.hpp>
#include <c2_msgs/msg/mission_feedback.hpp>
#include <centralized_msgs/srv/get_agents.hpp>
#include <c2_msgs/msg/swarm_log.hpp>
#include <c2_msgs/srv/init_mission.hpp>
#include <c2_msgs/srv/change_mission_status.hpp>
#include <c2_msgs/msg/change_mission_status_response.hpp>

// Swarm planner msgs
#include <centralized_msgs/srv/get_plan.hpp>
#include <centralized_msgs/srv/create_planner.hpp>
#include <centralized_msgs/srv/update_planner_agents.hpp>
#include <centralized_msgs/msg/plan_calculated.hpp>

// Swarm client msgs
#include <task_msgs/msg/feedback.hpp>
#include <task_msgs/msg/task_feedback.hpp>



using namespace std::chrono_literals;
using std::placeholders::_1;
using std::placeholders::_2;


class MissionManager : public rclcpp::Node
{
public:
  /************** PUBLIC METHODS **************/
  MissionManager(std::string mission_id, bool existing_mission);
  ~MissionManager();


private:
  std::vector<std::string> _finished_vehicles;
  std::vector<std::string> _mission_vehicles;

  RuntimeDatabase::MongoDbHandler _runtime_database;
  FeedbackDatabase::MongoDbHandler _feedback_database;

  // for testing:
  centralized_coordination::json_lib::JsonParser _json_parser;
  c2_msgs::json::MissionFeedback _mission_feedback;

  /************** PRIVATE METHODS **************/

  // General
  void _initPlannerInterface();
  void _initC2Interface(std::string mission_id);
  void _initCmdServices();
  void _initIntraProcessComms();
  void _initPublishers();

  void _getMissionConfig();
  void _getPlanning_try();
  void setInitialMissionStatus(bool existing_mission);

  // Request Planning
  void _createPlanner();
  void _requestPlanning();
  void _planner_state_subscriber_callback(const std_msgs::msg::String::SharedPtr msg);
  // void _agent_task_completed_subscriber_callback(const std_msgs::msg::String::SharedPtr msg);
  void _planning_subscriber_callback(const centralized_msgs::msg::PlanCalculated::SharedPtr msg);
  void _register_planning_result(std::string planning);
  void _swarm_planner_connection_timer_callback();
  void _setConnectedToSwarmPlanner();
  void _plannification_timer_callback();

  std::vector<centralized_msgs::msg::Agent> _getAgentsFromEdgeManager(std::vector<std::string> vehicles);
  void _edge_feedback_subscriber_callback(const task_msgs::msg::Feedback::SharedPtr msg);

  // State Machine
  void _stateMachineCallback();
  void _stateMachineActions();

  void _changeAgentTaskStatuses(int task_status);
  void _sendAgentTasks();
  // Swarm Log (publisher)
  void _publishSwarmLog(int log_type, std::string mission_id, std::string log_message);
  // Mission Feedback (publisher)
  void _publishMissionFeedback();
  // Delete mission (publisher)
  void _deleteMission();
  // Change possible transiions based on new runtime state
  void _updateAllowedTransitions(int new_state);
  int _convert_requested_status_to_mission_status(int mission_request_status);
  std::string _get_status_string(int status);

  // Callbacks
  //  Runtime state change (Server)

  void _changeMissionStatus_callback(const c2_msgs::srv::ChangeMissionStatus::Request::SharedPtr request, c2_msgs::srv::ChangeMissionStatus::Response::SharedPtr response);
  // void _changeMissionStatus_callback(std_msgs::msg::Int8::UniquePtr msg);

  // Environment change (Server)
  void _environmentChange_callback(const std_srvs::srv::Trigger::Request::SharedPtr request, std_srvs::srv::Trigger::Response::SharedPtr response);
  void _vehicleChange_callback(const std_srvs::srv::Trigger::Request::SharedPtr request, std_srvs::srv::Trigger::Response::SharedPtr response);

  void _updatePlannerAgents();

  void _agent_task_completed(std::string agent_id);

  // Centralized Coordinationcommand (server)
  void _commandService_callback(const std_srvs::srv::Trigger::Request::SharedPtr request, std_srvs::srv::Trigger::Response::SharedPtr response);

  /************** PRIVATE ATTRIBUTES **************/

  // Quality of Service
  std::string C2_INTERFACE_AVOID_ROS_PREFIX = std::getenv("C2_INTERFACE_AVOID_ROS_PREFIX");
  bool _c2_qos_avoid_ros_prefix = (C2_INTERFACE_AVOID_ROS_PREFIX == "TRUE") ? true : false;

  // General
  std::string _mission_id;
  std::string _mission_id_underscores;
  std::string _mission_config_str;
  nlohmann::json _mission_config;
  nlohmann::json _planning_json;
  // c2_msgs::json::MissionConfig _mission_config;
  std::vector<centralized_msgs::msg::Agent> _mission_agents;
  std::vector<std::string> _planned_mission_vehicles;

  // State Machine
  int _state;
  int _new_mission_status;
  std::vector<bool> _allowed_transitions;

  // Planner
  int _planner_service_state = 0;
  int _planner_connection_counter = 0;

  // Flags
  bool _active_mission = true;
  bool _change_mission_status_flag = false;
  bool _plannification_needed_flag = false;
  bool _replannification_needed_flag = false;
  bool _waiting_for_planner_response = false;
  bool _agents_need_task_updates_flag = false;
  bool _planner_created_flag = false;
  bool _plan_calculated_flag = false;
  bool _connected_to_swarm_planner = false;

  bool _waiting_location = false;

  rclcpp::Node::SharedPtr _mission_manager_node_ptr;

  rclcpp::TimerBase::SharedPtr _timer_state_machine; // timer for the state machine callback
  rclcpp::TimerBase::SharedPtr _timer_planner_connection;
  rclcpp::TimerBase::SharedPtr _timer_replannification;
  rclcpp::TimerBase::SharedPtr _timer_mission_feedback; // timer for the mission feedback publisher
  rclcpp::CallbackGroup::SharedPtr _cb_grp_int;         // callback group for internal processes

  // Request Planning calculation (client)
  rclcpp::Client<centralized_msgs::srv::GetPlan>::SharedPtr _get_plan_client;
  // Planning result (subscriber)
  rclcpp::Client<centralized_msgs::srv::CreatePlanner>::SharedPtr _create_planner_client;
  rclcpp::Client<centralized_msgs::srv::UpdatePlannerAgents>::SharedPtr _update_planner_agents_client;
  rclcpp::Subscription<centralized_msgs::msg::PlanCalculated>::SharedPtr _planning_subscriber;
  rclcpp::Subscription<std_msgs::msg::String>::SharedPtr _planner_state_subscriber;

  // rclcpp::Subscription<std_msgs::msg::String>::SharedPtr _agent_task_completed_subscriber;
  rclcpp::Subscription<task_msgs::msg::Feedback>::SharedPtr _edge_feedback_subscriber;

  // Request mission deletion to centralized_coordination (client)
  rclcpp::Client<c2_msgs::srv::ChangeMissionStatus>::SharedPtr _delete_mission_client;

  // Request agent information to fleet_manager (client)
  rclcpp::Client<centralized_msgs::srv::GetAgents>::SharedPtr _get_agent_client;

  rclcpp::Client<c2_msgs::srv::InitMission>::SharedPtr _send_tasks_client;
  rclcpp::Client<c2_msgs::srv::ChangeMissionStatus>::SharedPtr _change_agent_task_status_client; // To inform edge about mission status change (pause/stop/RUN/...)
  rclcpp::Publisher<c2_msgs::msg::ChangeMissionStatusResponse>::SharedPtr _change_mission_status_pub_ptr;

  // Log (publisher)
  rclcpp::Publisher<c2_msgs::msg::SwarmLog>::SharedPtr _swarm_log_publisher;

  // Mission Feedback (publisher)
  rclcpp::Publisher<c2_msgs::msg::MissionFeedback>::SharedPtr _mission_feedback_publisher;

  // Service for changing the mission status
  rclcpp::Service<c2_msgs::srv::ChangeMissionStatus>::SharedPtr _change_mission_status_server;

  rclcpp::Service<std_srvs::srv::Trigger>::SharedPtr _environment_change_server;
  rclcpp::Service<std_srvs::srv::Trigger>::SharedPtr _vehicle_change_server;

  // Command to mission runtime
  rclcpp::Service<std_srvs::srv::Trigger>::SharedPtr _cmd_server;
};

#endif
