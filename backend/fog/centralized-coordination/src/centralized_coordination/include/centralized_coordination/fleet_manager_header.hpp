/****************************************************************/
// Central Coordination - Fleet manager header
// Alexandre La Grappe & Emile Le Flecher  - RMA - alexandre.lagrappe@mil.be or emile.leflecher@mil.be 
// 03.12.2024 - V1.0
/****************************************************************/

#ifndef EDGE_MANAGER_HEADER_HPP
#define EDGE_MANAGER_HEADER_HPP

// standard ros include
#include <cstdio>
#include <rclcpp/rclcpp.hpp>
#include <rclcpp/callback_group.hpp>
#include <chrono> // to use sleep_for
#include <algorithm>
#include <unistd.h>

// Header file
#include <centralized_coordination/mission_manager_header.hpp>
#include <centralized_coordination/c2_interface_header.hpp>


// Custom libraries 
#include <custom_libraries/mongodb_handler.hpp>
#include <custom_libraries/uuid_library.hpp>
#include <custom_libraries/json_parser.hpp>


#include <std_msgs/msg/int8.hpp>

// Custom messages & services
// Swarm manager msgs
#include <c2_msgs/msg/mission_feedback.hpp>
#include <c2_msgs/srv/init_mission.hpp>
#include <c2_msgs/msg/swarm_log.hpp>

// Swarm client msgs
#include <task_msgs/srv/add_task.hpp>
#include <task_msgs/srv/change_state.hpp>
#include <task_msgs/srv/change_task_state.hpp>
#include <task_msgs/msg/feedback.hpp>


// Custom structures
#include "models.hpp"

// Custom tools
#include "tools.hpp"

using namespace std::chrono_literals;

class Interface;
class FleetManagerNode : public rclcpp::Node
{
private:
  /************** PRIVATE ATTRIBUTES **************/

  // Quality of Service
  std::string C2_INTERFACE_AVOID_ROS_PREFIX = std::getenv("C2_INTERFACE_AVOID_ROS_PREFIX");
  bool _c2_qos_avoid_ros_prefix = (C2_INTERFACE_AVOID_ROS_PREFIX == "TRUE") ? true : false;

  bool _send_tasks_flag = false;
  bool _change_agent_task_status_flag = false;

  int _edge_connection_timeout = 5;

  int _requested_task_status;
  std::string _targeted_mission_id;

  // Configuration parameters
  bool use_high_level_collision_avoidance = false;
  double tolerance_distance = 10;
  double vicinity_radius = 30;
  double max_deceleration_factor = 0.10;

  // for database handling:
  VehicleDatabase::MongoDbHandler _vehicle_database;
  RuntimeDatabase::MongoDbHandler _runtime_database;

  // Custom parser:
  centralized_coordination::json_lib::JsonParser _json_parser;
  // nlohmann::json agent_profile_example = this->_json_parser.readJsonFile("src/centralized_coordination/test/json_example/", "agent_profile.json");

  rclcpp::CallbackGroup::SharedPtr cb_grp_int_; // callback group for internal processes
  rclcpp::CallbackGroup::SharedPtr cb_grp_ext_; // callback group for internal processes

  // Agent lists
  std::list<Agent> _detected_agent_list;
  std::list<Agent> _modulated_agent_list;

  // Service for giving agent information
  rclcpp::Service<centralized_msgs::srv::GetAgents>::SharedPtr get_agents_server_;
  rclcpp::Service<c2_msgs::srv::InitMission>::SharedPtr _send_tasks_server;
  rclcpp::Service<c2_msgs::srv::ChangeMissionStatus>::SharedPtr _change_agent_task_status_server;

  rclcpp::Subscription<std_msgs::msg::String>::SharedPtr delete_mission_subscriber_;
  rclcpp::Subscription<task_msgs::msg::Feedback>::SharedPtr _edge_feedback_subscriber;
  rclcpp::Subscription<std_msgs::msg::String>::SharedPtr _agent_profile_subscriber;

  rclcpp::Publisher<c2_msgs::msg::SwarmLog>::SharedPtr _swarm_log_publisher;
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr _edge_connection_check_publisher;

  rclcpp::Publisher<centralized_msgs::msg::Agent>::SharedPtr _agent_publisher;

  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr _agent_task_completed_publisher;

  std::shared_ptr<FleetManagerNode> _swarm_manager_node_ptr;
  std::shared_ptr<Interface> _interface_node_ptr;

  rclcpp::TimerBase::SharedPtr timer_;
  rclcpp::TimerBase::SharedPtr timer_edge_connection;
  rclcpp::TimerBase::SharedPtr timer_collision_avoidance;

  /************** PRIVATE METHODS **************/

  void initIntraProcessComms_();
  void _initEdgeInterface();
  void _init_C2_interface();
  void _ReadConfigurationFile();
  void _initAgent(std::string agent_id, std::string agent_profile_str);


  void _TimerLoop_callback();
  void _EdgeConnection_timer_callback();
  void _HighLevelCollisionAvoidance_timer_callback();
  bool _check_collision(double vicinity_radius,  double tolerance_distance);
  void _recover_agent_task_callback(); // re-send task to agent if edge node was restarted;
  void GetAgents_callback(const centralized_msgs::srv::GetAgents::Request::SharedPtr request, centralized_msgs::srv::GetAgents::Response::SharedPtr response);
  void SendTasks_callback(const c2_msgs::srv::InitMission::Request::SharedPtr request, c2_msgs::srv::InitMission::Response::SharedPtr response);
  void ChangeMissionTaskStatuses_callback(const c2_msgs::srv::ChangeMissionStatus::Request::SharedPtr request, c2_msgs::srv::ChangeMissionStatus::Response::SharedPtr response);

  EdgeClient _createEdgeClient(std::string agent_id);
  void _sendAgentTask(std::string agent_id, nlohmann::json agent_task_json);
  void _sendAllTasksForMission(std::string mission_id);
  void _setAgentTasksFromPlanning(std::string mission_id);
  void _changeMissionTaskStatuses(std::string mission_id, int requested_agent_task_status);
  void _changeAgentTaskStatus(std::string agent_id, std::string task_id,  int requested_agent_task_status);
  void _runMissionTasks(std::string mission_id);
  void _pauseMissionTasks(std::string mission_id);
  void _publishSwarmLog(int log_type, std::string mission_id, std::string log_message);

  void changeMissionStatus(std::string mission_id, int requested_status);
  void environmentChange(std::string mission_id);

  void _agent_profile_subscriber_callback(const std_msgs::msg::String::SharedPtr msg);
  void _edge_feedback_subscriber_callback(const task_msgs::msg::Feedback::SharedPtr msg);

  Agent* getAgent(const std::string& agent_id);

  // Converters
  centralized_msgs::msg::Agent toPlannerAgentMsg(Agent* agent);
  std::string _taskStatusToString(int task_status);

public:
  /************** PUBLIC METHODS **************/
  FleetManagerNode();
  ~FleetManagerNode();
};

#endif // SWARM_MANAGER_HEADER_HPP
