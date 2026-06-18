/****************************************************************/
// Central Coordination - C2 interface node
// Alexandre La Grappe & Emile Le Flecher  - RMA - alexandre.lagrappe@mil.be or emile.leflecher@mil.be 
// 03.12.2024 - V1.0
/****************************************************************/

/*---------------------------------------------------*/
//                    General                        //
/*---------------------------------------------------*/
// - C2 interface 
// - Environment interface
/*---------------------------------------------------*/
#include <centralized_coordination/c2_interface_header.hpp>

using namespace c2_msgs::json;

Interface::Interface() : Node("c2_interface_node")
{
  // initiate the services
  this->_initInterfaces();

  this->mutex_c2_interface_state.unlock();

  RCLCPP_INFO(this->get_logger(), "C2 Interface initialized");
  this->_publishSwarmLog(0,"", "C2 interface initialized");
}

Interface::~Interface()
{
  
}

// Allow the interface to call public attributes and methods from the Swarm Manager
void Interface::setOrchestratorPtr(std::shared_ptr<OrchestratorNode> ptr)
{
  this->_swarm_manager_node_ptr = ptr;
}

// Initialize the different types of interface
void Interface::_initInterfaces()
{
  this->_initC2Interface();
}

/*---------------------------------------------------*/
//                    C2 Interface                   //
/*---------------------------------------------------*/

// init c2 transmission
void Interface::_initC2Interface()
{
    rclcpp::QoS c2_qos = rclcpp::QoS(
    rclcpp::QoSInitialization(
      rmw_qos_profile_services_default.history,
      rmw_qos_profile_services_default.depth
    ),
    rmw_qos_profile_services_default);
  if (this->_c2_qos_avoid_ros_prefix){
    c2_qos.avoid_ros_namespace_conventions(true);
    c2_qos.history(RMW_QOS_POLICY_HISTORY_KEEP_LAST);
  };

  // Callback group for C2 interface
  this->_C2_callback_group_ptr = this->create_callback_group(rclcpp::CallbackGroupType::Reentrant);
  
  // Publishers and Subscribers
  this->_init_mission_subscriber = this->create_subscription<c2_msgs::msg::InitMissionRequest>("/multi_robot/mission_init_request", c2_qos, std::bind(&Interface::_initMissionCallback, this, _1));
  this->_init_mission_publisher = this->create_publisher<c2_msgs::msg::InitMissionResponse>("/multi_robot/mission_init_response", c2_qos);
  
  this->_change_mission_status_subscriber = this->create_subscription<c2_msgs::msg::ChangeMissionStatusRequest>("/multi_robot/change_mission_status_request", c2_qos, std::bind(&Interface::_changeMissionStatusCallback, this, _1));
  this->_change_mission_status_publisher = this->create_publisher<c2_msgs::msg::ChangeMissionStatusResponse>("/multi_robot/change_mission_status_response", c2_qos);

  this->_change_mission_vehicles_subscriber = this->create_subscription<c2_msgs::msg::ChangeMissionVehicleRequest>("/multi_robot/change_mission_vehicle_request", c2_qos, std::bind(&Interface::_changeMissionVehicleCallback, this, _1));
  this->_change_mission_vehicles_publisher = this->create_publisher<c2_msgs::msg::ChangeMissionVehicleResponse>("/multi_robot/change_mission_vehicle_response", c2_qos);

  // Environment Data
  this->_env_data_reset_req_subscriber = this->create_subscription<environment_msgs::msg::EnvironmentDataResetRequest>("/multi_robot/environment_data_reset_request", c2_qos, std::bind(&Interface::_environmentResetDataCallback, this, _1));
  this->_env_data_reset_res_publisher = this->create_publisher<environment_msgs::msg::EnvironmentDataResetResponse>("/multi_robot/environment_data_reset_response", c2_qos);
  this->_env_data_upload_req_subscriber = this->create_subscription<environment_msgs::msg::EnvironmentDataUploadRequest>("/multi_robot/environment_data_upload_request", c2_qos, std::bind(&Interface::_environmentUploadDataCallback, this, _1));
  this->_env_data_upload_res_publisher = this->create_publisher<environment_msgs::msg::EnvironmentDataUploadResponse>("/multi_robot/environment_data_upload_response", c2_qos);
  this->_env_data_version_req_subscriber = this->create_subscription<environment_msgs::msg::EnvironmentDataGetVersionRequest>("/multi_robot/environment_data_get_version_request", c2_qos, std::bind(&Interface::_environmentGetVersionCallback, this, _1));
  this->_env_data_version_res_publisher = this->create_publisher<environment_msgs::msg::EnvironmentDataGetVersionResponse>("/multi_robot/environment_data_get_version_response", c2_qos);  

  // Log
  this->_swarm_log_publisher = this->create_publisher<c2_msgs::msg::SwarmLog>("/multi_robot/swarm_log", c2_qos);
  this->_mission_feedback_publisher = this->create_publisher<c2_msgs::msg::MissionFeedback>("/multi_robot/mission_feedback", c2_qos);
}


/************************************************************/
// Publish Swarm Log (Publisher)                  //
/************************************************************/
void Interface::_publishSwarmLog(int log_type, std::string mission_id, std::string log_message)
{
  try
  {
    auto msg = c2_msgs::msg::SwarmLog();
    msg.log_type = log_type;
    msg.log = "[C2 INTERFACE] "+log_message;
    if(!mission_id.empty()) msg.mission_id = convertStringUuidtoRosUuid(mission_id);
    this->_swarm_log_publisher->publish(msg);
  }

  catch (const std::exception &e)
  {
    RCLCPP_ERROR(this->get_logger(), "An error occured during _publishSwarmLog");
  }
}


/*** MISSION ***/
// Callback for initMission service
// Must get the new mission config to be checked and registered in the database 
void Interface::_initMissionCallback( const c2_msgs::msg::InitMissionRequest::SharedPtr _request)
{ 
  unique_identifier_msgs::msg::UUID uuid_mission_id = _request.get()->mission_id;
  std::string mission_id = convertByteArrayToString(uuid_mission_id);

  std::cout << "mission_id: " << mission_id.c_str() << std::endl;
  std::cout << " mission config string: " << _request.get()->mission_config << std::endl;
  
  try
  {
    auto json_result = MissionConfig::FromJsonString(_request.get()->mission_config);
    if(!json_result.Success)
    {
      std::cout << "_initMissionCallback -> Error while parsing InitMission: " << json_result.Log << std::endl;
      this->_publishSwarmLog(2,"", "_initMissionCallback -> Error while parsing InitMission");
    }

    auto &mission_config = json_result.Result.value();
    this->_mission_config = mission_config;
    this->_mission_config.MissionId = mission_id;

    // To test parser:
    //-----
    std::string mission_config_string = this->_mission_config.MissionConfig::ToJsonString();
    std::cout << " mission config string after conversions: " << mission_config_string << std::endl;
    //-----

    /** Add Check info completness function here **/
    bool mission_config_complete = true; // for now, consider it to be always complete

    /** Add mission action **/
    if(this->mutex_c2_interface_state.try_lock())
    {
      this->_C2_interface_state.flag_new_mission = true;
      this->_C2_interface_state.mission_id = mission_id;
      this->_C2_interface_state.mission_info.mission_config = this->_mission_config;
      this->mutex_c2_interface_state.unlock();
      
      // compose mission_feedback parsed json
      this->_mission_feedback.Date = std::chrono::system_clock::to_time_t(std::chrono::system_clock::now());
      this->_mission_feedback.MissionId = this->_C2_interface_state.mission_id;
      this->_mission_feedback.Status = enums::MissionStatus::NONE;
      this->_mission_feedback.RequestedStatus = enums::MissionStatusRequest::INIT;
      this->_mission_feedback.Behavior = this->_mission_config.Behavior;
      if (mission_config_complete){this->_mission_feedback.Issue = enums::MissionIssue::NONE;}
      else {this->_mission_feedback.Issue = enums::MissionIssue::NONE;}
      
      std::string mission_feedback_string = this->_mission_feedback.ToJsonString();
      c2_msgs::msg::InitMissionResponse _response;
      _response.mission_id = convertStringUuidtoRosUuid(mission_id);
      _response.mission_feedback = mission_feedback_string;
    }
    else
    {
      RCLCPP_WARN(this->get_logger(), "_initMissionCallback -> mutex locked in callback");
      this->_publishSwarmLog(1,"", "_initMissionCallback -> mutex locked in callback");
      c2_msgs::msg::InitMissionResponse _response;
      _response.mission_id = convertStringUuidtoRosUuid(mission_id);
      _response.mission_feedback = "Error while saving the init_mission request, probably mutex error";
    }
  }
  catch(const std::exception& e)
  {
    c2_msgs::msg::InitMissionResponse _response;
    _response.mission_id = convertStringUuidtoRosUuid(mission_id);
    _response.mission_feedback = "_initMissionCallback -> Error while saving the mission config: " + (std::string) e.what();
    this->_publishSwarmLog(2,"", "_initMissionCallback -> Error while saving the mission config");
  } 
}

// Callback for changing the mission status from C2
void Interface::_changeMissionStatusCallback(const c2_msgs::msg::ChangeMissionStatusRequest::SharedPtr _request)
{
  c2_msgs::msg::ChangeMissionStatusResponse _response;
  try
  {
    auto status_mission = (enums::MissionStatusRequest) _request->mission_request_status;
    unique_identifier_msgs::msg::UUID uuid_mission_id = _request.get()->mission_id;
    std::string mission_id = convertByteArrayToString(uuid_mission_id);
    
    this->_swarm_manager_node_ptr->setRequestMissionChangeStatus(mission_id, status_mission);

    _response.mission_id = _request->mission_id;
    _response.mission_status = this->_swarm_manager_node_ptr->getMissionStatus(convertByteArrayToString(_request->mission_id));
    // this->_change_mission_status_publisher->publish(_response);

  }
  catch(const std::exception& e)
  {
    _response.mission_id = _request->mission_id;
    _response.error_message = "_changeMissionStatusCallback -> Error while changing the mission status: " + (std::string) e.what();
    this->_publishSwarmLog(2,"", "_changeMissionStatusCallback -> Error while changing the mission status");
  }

  return void();
}

void Interface::_changeMissionVehicleCallback(const c2_msgs::msg::ChangeMissionVehicleRequest::SharedPtr _request)
{  
  auto vehicles_list = _request.get()->vehicule_id_list;
    
  if(this->mutex_c2_interface_state.try_lock())
  {
    this->_C2_interface_state.flag_vehicle_changes = true;
    this->_C2_interface_state.mission_id = convertByteArrayToString(_request->mission_id);
    this->_C2_interface_state.mission_info.vehicle_change_config.action = _request->vehicle_changes;
    this->_C2_interface_state.mission_info.vehicle_change_config.vehicles_list = vehicles_list;

    c2_msgs::msg::ChangeMissionVehicleResponse _response;
    _response.mission_id = _request->mission_id;
    this->_change_mission_vehicles_publisher->publish(_response);

    this->mutex_c2_interface_state.unlock();
  }
  else
  {
    /** Send Log */
    RCLCPP_WARN(this->get_logger(), "_changeMissionVehicleCallback -> Error while requesting c2_interface_mutex");
    this->_publishSwarmLog(2,"", "_changeMissionVehicleCallback -> Error while requesting c2_interface_mutex");
  }
  
  return void();
}

// Create instance of mission feedback
void createMissionFeedbackInstance(std::string mission_id, std::string feedback)
{
  std::cout << mission_id << feedback << std::endl;
}

// Handle the communication between interface and manager
ResultFct<InterfaceC2State> Interface::getC2InterfaceStatus()
{
  InterfaceC2State result;

  if(this->mutex_c2_interface_state.try_lock())
  {
    result = this->_C2_interface_state;
    this->_C2_interface_state.flush();
    this->mutex_c2_interface_state.unlock();
  }
  else
  {
    RCLCPP_WARN(this->get_logger(), "createMissionFeedbackInstance -> mutex locked in get");
    this->_publishSwarmLog(1,"", "createMissionFeedbackInstance -> mutex locked in get");
  }
    
  return {result};
}

void Interface::_environmentResetDataCallback(const environment_msgs::msg::EnvironmentDataResetRequest _request)
{
  RCLCPP_INFO(this->get_logger(), "RESET ENVIRONMENT DATA REQUESTED");
  this->_swarm_manager_node_ptr->_environmentChange();
  environment_msgs::msg::EnvironmentDataResetResponse _response;
  _response.request_id = _request.request_id;
  _response.result_status = 0;
  this->_env_data_reset_res_publisher->publish(_response);
}

void Interface::_environmentUploadDataCallback(const environment_msgs::msg::EnvironmentDataUploadRequest _request)
{
  RCLCPP_INFO(this->get_logger(), "UPLOAD ENVIRONMENT DATA REQUESTED");
  this->_swarm_manager_node_ptr->_environmentChange();
  environment_msgs::msg::EnvironmentDataUploadResponse _response;
  _response.request_id = _request.request_id;
  _response.result_status = 0;
  RCLCPP_INFO(this->get_logger(), "_response.status: %d", _response.result_status);
  this->_env_data_upload_res_publisher->publish(_response);
}

void Interface::_environmentGetVersionCallback(const environment_msgs::msg::EnvironmentDataGetVersionRequest _request)
{
  RCLCPP_INFO(this->get_logger(), "ENVIRONMENT VERSION REQUESTED");
  environment_msgs::msg::EnvironmentDataGetVersionResponse _response;
  _response.request_id = _request.request_id;
  _response.version_nr = 1;
  this->_env_data_version_res_publisher->publish(_response);
} 
