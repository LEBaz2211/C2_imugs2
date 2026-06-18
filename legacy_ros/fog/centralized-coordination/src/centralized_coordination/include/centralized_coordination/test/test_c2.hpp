#ifndef TESTC2_HPP
#define TESTC2_HPP

#include <rclcpp/rclcpp.hpp>
#include <cstdio>
#include <fstream>

#include <nlohmann/json.hpp>

//srv
#include <c2_msgs/srv/init_mission.hpp>
#include <c2_msgs/msg/init_mission_request.hpp>
#include <c2_msgs/msg/init_mission_response.hpp>
#include <c2_msgs/msg/change_mission_status_request.hpp>
#include <c2_msgs/msg/change_mission_status_response.hpp>
#include <c2_msgs/msg/change_mission_vehicle_request.hpp>
#include <c2_msgs/msg/change_mission_vehicle_response.hpp>
#include <environment_msgs/msg/environment_data_reset_request.hpp>
#include <environment_msgs/msg/environment_data_upload_request.hpp>
#include <environment_msgs/msg/environment_data_get_version_request.hpp>
#include <environment_msgs/msg/environment_data_reset_response.hpp>
#include <environment_msgs/msg/environment_data_upload_response.hpp>
#include <environment_msgs/msg/environment_data_get_version_response.hpp>

#include <c2_msgs/srv/change_mission_status.hpp>
#include <c2_msgs/srv/change_mission_vehicle.hpp>

#include <environment_msgs/srv/environment_data_reset.hpp>
#include <environment_msgs/srv/environment_data_upload.hpp>
#include <environment_msgs/srv/environment_data_get_version.hpp>

#include <centralized_msgs/srv/create_planner.hpp>
#include <centralized_msgs/srv/delete_planner.hpp>

// msg
#include <c2_msgs/msg/mission_feedback.hpp>
#include <c2_msgs/msg/swarm_log.hpp>

// json parser
#include <c2_msgs/json/MissionConfig.hpp>
// #include <c2_msgs/json/include/picojson.h> // not used here
#include <custom_libraries/uuid_library.hpp>
#include <custom_libraries/json_parser.hpp>

// Enum lib
#include <c2_msgs/json/Enums.hpp> // Manager
#include <centralized_msgs/json/Enums.hpp> // Planner


using json = nlohmann::json;

using namespace std::chrono_literals;
using namespace std::placeholders;

/***********************************************************************/
class TestC2 : public rclcpp::Node
{
private:
  std::string _test_json_path = "test/json_input/c2_sim/";

  // Quality of Service 
  std::string C2_INTERFACE_AVOID_ROS_PREFIX = std::getenv("C2_INTERFACE_AVOID_ROS_PREFIX");
  bool _swarm_manager_qos_avoid_ros_prefix = (C2_INTERFACE_AVOID_ROS_PREFIX=="TRUE") ? true : false;


  centralized_coordination::json_lib::JsonParser _json_parser;
  nlohmann::json _mission_config;
  std::string _mission_config_str;
  std::string _mission_id = std::getenv("MISSION_ID");
  // file attributes
  c2_msgs::msg::MissionFeedback _mission_feedback_msg;
  c2_msgs::msg::SwarmLog log;

  // Enumeration
  c2_msgs::json::enums::VehicleChanges _vehicles_changes_enum;
  c2_msgs::json::enums::MissionStatus _enum_mission_status;
  // centralized_msgs::json::enums::PlanStatus _planner_state;

  
  // ros attributes
  rclcpp::CallbackGroup::SharedPtr _C2_callback_group_ptr;
  rclcpp::CallbackGroup::SharedPtr _planner_callback_group_ptr;

  // Clients
  std::shared_ptr<rclcpp::Client<c2_msgs::srv::InitMission>> _init_mission_client_ptr;

  rclcpp::Subscription<c2_msgs::msg::InitMissionResponse>::SharedPtr _init_mission_sub_ptr;
  rclcpp::Publisher<c2_msgs::msg::InitMissionRequest>::SharedPtr _init_mission_pub_ptr;

  rclcpp::Subscription<c2_msgs::msg::ChangeMissionStatusResponse>::SharedPtr _change_mission_status_sub_ptr;
  rclcpp::Publisher<c2_msgs::msg::ChangeMissionStatusRequest>::SharedPtr _change_mission_status_pub_ptr;

  rclcpp::Subscription<c2_msgs::msg::ChangeMissionVehicleResponse>::SharedPtr _change_mission_vehicles_sub_ptr;
  rclcpp::Publisher<c2_msgs::msg::ChangeMissionVehicleRequest>::SharedPtr _change_mission_vehicles_pub_ptr;

  std::shared_ptr<rclcpp::Client<c2_msgs::srv::ChangeMissionVehicle>>_change_vehicle_client_ptr;
  std::shared_ptr<rclcpp::Client<c2_msgs::srv::ChangeMissionStatus>>_change_mission_status_client_ptr;
  std::shared_ptr<rclcpp::Client<environment_msgs::srv::EnvironmentDataReset>>_environment_data_reset_client_ptr;
  std::shared_ptr<rclcpp::Client<environment_msgs::srv::EnvironmentDataUpload>>_environment_data_upload_client_ptr;
  std::shared_ptr<rclcpp::Client<environment_msgs::srv::EnvironmentDataGetVersion>>_environment_data_get_version_client_ptr;

  rclcpp::Publisher<environment_msgs::msg::EnvironmentDataResetRequest>::SharedPtr _env_data_reset_req_pub_ptr;
  rclcpp::Publisher<environment_msgs::msg::EnvironmentDataUploadRequest>::SharedPtr _env_data_upload_req_pub_ptr;
  rclcpp::Publisher<environment_msgs::msg::EnvironmentDataGetVersionRequest>::SharedPtr _env_data_version_req_pub_ptr;

  rclcpp::Service<centralized_msgs::srv::CreatePlanner>::SharedPtr _create_planner_srv_ptr;
  rclcpp::Service<centralized_msgs::srv::DeletePlanner>::SharedPtr _delete_planer_srv_ptr;
  
  // Subscribers
  std::shared_ptr<rclcpp::Subscription<c2_msgs::msg::MissionFeedback>> _mission_feedback_sub_ptr;
  std::shared_ptr<rclcpp::Subscription<c2_msgs::msg::SwarmLog>> _swarm_log_sub_ptr;

  // Timers
  rclcpp::TimerBase::SharedPtr _timer;
  
  // message attributes
  // json _mission_config;
  json _mission_feedback;
  c2_msgs::json::enums::MissionStatusRequest _status_requested;

  // METHODS
  void _LoadMissionConfigFile();
  void _initSwarmManagerInterface();
  void _initPlannerInterface();
  void _changeMissionStatusClient();
  void _changeVehicleClient();
  void _missionFeedbackSub();
  void _swarmLogSub();
  void _resetEnvironmentDataInit();
  void _uploadEnvironmentDataInit();
  void _getVersionEnvironmentDataInit();

  
  void _callbackSimu();
  void _sendInitMission();
  void _initMissionResponseCallback(const c2_msgs::msg::InitMissionResponse::SharedPtr msg);
  void _changeMissionStatusResponseCallback(const c2_msgs::msg::ChangeMissionStatusResponse::SharedPtr msg);
  void _changeMissionVehicleResponseCallback(const c2_msgs::msg::ChangeMissionVehicleResponse::SharedPtr msg);
  void _sendChangeStatus(int requested_state);
  void _sendVehiclesChanges(int requested_action, std::string vehicle_id);
  void _environmentRequest(std::string requested_action, std::string requested_upload_action, std::string requested_geojson_file);
  void _createPlanner(const std::shared_ptr<centralized_msgs::srv::CreatePlanner::Request> request, std::shared_ptr<centralized_msgs::srv::CreatePlanner::Response> response);
  void _deletePlanner(const std::shared_ptr<centralized_msgs::srv::DeletePlanner::Request> request, std::shared_ptr<centralized_msgs::srv::DeletePlanner::Response> response);
  void _getMissionFeedback(const c2_msgs::msg::MissionFeedback &feedback);
  void _logCallback(const c2_msgs::msg::SwarmLog &log_msg);
  json _readJsonFile(std::string json_path, std::string json_file_name);

public:
  TestC2(/* args */);
  ~TestC2();
};

#endif