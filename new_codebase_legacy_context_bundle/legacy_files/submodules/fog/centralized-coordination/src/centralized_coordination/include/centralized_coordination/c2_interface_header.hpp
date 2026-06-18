/****************************************************************/
// Central Coordination - C2 interface header
// Alexandre La Grappe & Emile Le Flecher  - RMA - alexandre.lagrappe@mil.be or emile.leflecher@mil.be 
// 03.12.2024 - V1.0
/****************************************************************/

#ifndef C2_INTERFACE_HEADER_HPP
#define C2_INTERFACE_HEADER_HPP

// standard ros include
#include <cstdio>
#include <rclcpp/rclcpp.hpp>
#include <chrono>
#include <vector>
#include <optional>
#include <mutex>
#include <nlohmann/json.hpp>

// Header file
#include <centralized_coordination/orchestrator_header.hpp>

// Custom libraries 
#include <custom_libraries/mongodb_handler.hpp>
#include <custom_libraries/uuid_library.hpp>

// Custom structures
#include "models.hpp"

// Custom messages & services
// Swarm manager msgs
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
#include <c2_msgs/msg/mission_feedback.hpp>
#include <c2_msgs/msg/swarm_log.hpp>

#include <environment_msgs/srv/environment_data_reset.hpp>
#include <environment_msgs/srv/environment_data_upload.hpp>
#include <environment_msgs/srv/environment_data_get_version.hpp>

// Swarm planner msgs
#include <centralized_msgs/srv/create_planner.hpp>
#include <centralized_msgs/srv/delete_planner.hpp>
#include <centralized_msgs/msg/agent.hpp>

// Enums
#include <c2_msgs/json/Enums.hpp>

// Json Parsers
#include <c2_msgs/json/MissionConfig.hpp>
#include <c2_msgs/json/MissionFeedback.hpp>



// namespaces
using namespace std::chrono_literals;
using namespace std::placeholders;
using json = nlohmann::json;

class OrchestratorNode;

class Interface : public rclcpp::Node
{
/*---------------------------------------------------*/
//                    General                        //
/*---------------------------------------------------*/
public:
  Interface();
  ~Interface();
  
  /** set / get **/
  void setOrchestratorPtr(std::shared_ptr<OrchestratorNode> ptr);
  ResultFct<InterfaceC2State> getC2InterfaceStatus();

private:
  /*------------------------------*/
  //            Methods           //
  /*------------------------------*/  
  // Init transmissions
  void _initInterfaces(); // general
  
  /*------------------------------*/
  //          Attributes          //
  /*------------------------------*/
  /** Mutex **/
  std::mutex mutex_c2_interface_state;

  // class pointers
  std::shared_ptr<Interface> _c2_interface_node_ptr;
  std::shared_ptr<OrchestratorNode> _swarm_manager_node_ptr;
  
  
/*---------------------------------------------------*/
//                  C2 interface                     //
/*---------------------------------------------------*/
  // ATTRIBUTES
private:
  /*------------------------------*/
  //            Methods           //
  /*------------------------------*/
  /// GENERAL
  // C2 timer loop
  void _c2InterfaceLoop();
  void _c2FeedbackLoop();
  // Initialization C2 interface
  void _initC2Interface();
  void _initC2Services();
  void _initC2Clients();
  void _initC2Publisher();
  void _initC2Subscribers();
  void _initPublishers();

  /// MISSION
  // Service 'initMission' from C2
  void _initMissionCallback(const c2_msgs::msg::InitMissionRequest::SharedPtr _request);
  // Service 'ChangeMissionStatus' from C2
  void _changeMissionStatusCallback(const c2_msgs::msg::ChangeMissionStatusRequest::SharedPtr _request);
  // Service 'ChangeMissionVehicle' from C2 (Custom message must be created)
  void _changeMissionVehicleCallback(const c2_msgs::msg::ChangeMissionVehicleRequest::SharedPtr _request);
  
  void _publishSwarmLog(int log_type, std::string mission_id, std::string log_message);
  /*------------------------------*/
  //         Attributes           //
  /*------------------------------*/


   // Quality of Service 
  std::string C2_INTERFACE_AVOID_ROS_PREFIX = std::getenv("C2_INTERFACE_AVOID_ROS_PREFIX");
  bool _c2_qos_avoid_ros_prefix = (C2_INTERFACE_AVOID_ROS_PREFIX=="TRUE") ? true : false;



  InterfaceC2State _C2_interface_state;
  rclcpp::CallbackGroup::SharedPtr _C2_callback_group_ptr;
  // Services
  rclcpp::Service<c2_msgs::srv::InitMission>::SharedPtr _init_mission_srv_ptr;
  rclcpp::Subscription<c2_msgs::msg::InitMissionRequest>::SharedPtr _init_mission_subscriber;
  rclcpp::Publisher<c2_msgs::msg::InitMissionResponse>::SharedPtr _init_mission_publisher;

  rclcpp::Subscription<c2_msgs::msg::ChangeMissionStatusRequest>::SharedPtr _change_mission_status_subscriber;
  rclcpp::Publisher<c2_msgs::msg::ChangeMissionStatusResponse>::SharedPtr _change_mission_status_publisher;

  rclcpp::Subscription<c2_msgs::msg::ChangeMissionVehicleRequest>::SharedPtr _change_mission_vehicles_subscriber;
  rclcpp::Publisher<c2_msgs::msg::ChangeMissionVehicleResponse>::SharedPtr _change_mission_vehicles_publisher;

  rclcpp::Service<c2_msgs::srv::ChangeMissionStatus>::SharedPtr _change_mission_status_srv_ptr;
  rclcpp::Service<c2_msgs::srv::ChangeMissionVehicle>::SharedPtr _change_vehicles_srv_ptr;

  rclcpp::Subscription<environment_msgs::msg::EnvironmentDataResetRequest>::SharedPtr _env_data_reset_req_subscriber;
  rclcpp::Publisher<environment_msgs::msg::EnvironmentDataResetResponse>::SharedPtr _env_data_reset_res_publisher;

  rclcpp::Subscription<environment_msgs::msg::EnvironmentDataUploadRequest>::SharedPtr _env_data_upload_req_subscriber;
  rclcpp::Publisher<environment_msgs::msg::EnvironmentDataUploadResponse>::SharedPtr _env_data_upload_res_publisher;

  rclcpp::Subscription<environment_msgs::msg::EnvironmentDataGetVersionRequest>::SharedPtr _env_data_version_req_subscriber;
  rclcpp::Publisher<environment_msgs::msg::EnvironmentDataGetVersionResponse>::SharedPtr _env_data_version_res_publisher;

  // Publishers
  rclcpp::Publisher<c2_msgs::msg::MissionFeedback>::SharedPtr _mission_feedback_publisher;
  c2_msgs::json::MissionFeedback _mission_feedback;
  c2_msgs::json::MissionConfig _mission_config;
  rclcpp::Publisher<c2_msgs::msg::SwarmLog>::SharedPtr _swarm_log_publisher;
  c2_msgs::msg::SwarmLog _log;

/*---------------------------------------------------*/
//                  Map data Interface                //
// Map data will be directly acquired via the planner//
/*---------------------------------------------------*/
public:

private:

  /** Methods **/
  // Map data callbacks
  void _environmentResetDataCallback(const environment_msgs::msg::EnvironmentDataResetRequest _request);
  void _environmentUploadDataCallback(const environment_msgs::msg::EnvironmentDataUploadRequest _request);
  void _environmentGetVersionCallback(const environment_msgs::msg::EnvironmentDataGetVersionRequest _request);
  
};

#endif //C2_INTERFACE_HEADER_HPP
