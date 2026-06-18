/****************************************************************/
// Multi-Robot Orchestrator Node
// Alexandre La Grappe & Emile Le Flecher  - RMA - alexandre.lagrappe@mil.be or emile.leflecher@mil.be 
// 03.12.2024 - V1.0
/****************************************************************/

// Header File:
#include <centralized_coordination/orchestrator_header.hpp>

using std::placeholders::_1;
using std::placeholders::_2;

// Constructor - Destructor
OrchestratorNode::OrchestratorNode() : Node("orchestrator_node") // ROS intra
{
  this->_cb_grp_int = this->create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
  this->_cb_grp_ext = this->create_callback_group(rclcpp::CallbackGroupType::Reentrant);

  this->_initRosParameters();
  this->_initRosParameters();

  this->_initIntraProcessComms();
  this->_initPlannerInterface();
  this->_init_C2_interface();
  this->_initCmdServices();
  
  RCLCPP_INFO(this->get_logger(), "orchestrator_node instantiated");
  this->_publishSwarmLog(0, "", "orchestrator_node instantiated");

  this->_timer = this->create_wall_timer(5000ms, std::bind(&OrchestratorNode::_TimerLoop, this));
}

OrchestratorNode::~OrchestratorNode()
{
}

void OrchestratorNode::_initRosParameters()
{
  // declare_parameter("agent_id", "no_node_name");
  // this->agent_id= get_parameter("agent_id").as_string();
}

void OrchestratorNode::_initPlannerInterface()
{
  // this->_create_planner_client = this->create_client<centralized_msgs::srv::CreatePlanner>("multi_robot/planner/create", rmw_qos_profile_default, this->_cb_grp_int);
  this->_delete_planner_client = this->create_client<centralized_msgs::srv::DeletePlanner>("multi_robot/planner/delete", rmw_qos_profile_default, this->_cb_grp_int);
}

void OrchestratorNode::_initIntraProcessComms()
{
  /*********** Delete Mission Server ****************/
  this->_delete_mission_server = this->create_service<c2_msgs::srv::ChangeMissionStatus>("multi_robot/delete_mission", std::bind(&OrchestratorNode::_deleteMission_callback, this, _1, _2), rmw_qos_profile_services_default, this->_cb_grp_int);
  
  /*********** Swarm Log Subscriber (to upload in DB) ****************/
  this->_swarm_log_subscriber = this->create_subscription<c2_msgs::msg::SwarmLog>("/multi_robot/log", 10, std::bind(&OrchestratorNode::_swarm_log_subscriber_callback, this, _1));

}
void OrchestratorNode::_init_C2_interface()
{
  rclcpp::QoS c2_qos = rclcpp::QoS(
    rclcpp::QoSInitialization(
      rmw_qos_profile_services_default.history,
      rmw_qos_profile_services_default.depth
    ),
    rmw_qos_profile_services_default);
  if (this->_c2_qos_avoid_ros_prefix){c2_qos.avoid_ros_namespace_conventions(true);};

  this->_swarm_log_publisher = this->create_publisher<c2_msgs::msg::SwarmLog>("/multi_robot/log", c2_qos);
}

void OrchestratorNode::_initCmdServices()
{
  /*********** Trigger Command Server - for development ****************/
  this->_cmd_server = this->create_service<std_srvs::srv::Trigger>("multi_robot/cmd", std::bind(&OrchestratorNode::_commandService_callback, this, _1, _2), rmw_qos_profile_services_default, this->_cb_grp_int);
}

void OrchestratorNode::setInterfacePtr(std::shared_ptr<Interface> ptr)
{
  this->_interface_node_ptr = ptr;
}

/*********** Swarm_manager_node main loop ****************/
void OrchestratorNode::_TimerLoop()
{
  // First loop
  if (this->_firstloop)
  {
    this->_recoverMissionsFromDatabase(); // in case Centralized Coordination is restarted, so that missions can continue
    this->_firstloop = false;
  }

  /** Update status from the different interfaces **/
  InterfaceC2State c2_interface = this->_updateC2InterfaceState();

  /** Apply action depending on interface requests **/
  this->_managerActions(c2_interface);
  // RCLCPP_WARN(this->get_logger(), "SWARM MANAGER TIMER LOOP");
}

InterfaceC2State OrchestratorNode::_updateC2InterfaceState()
{
  InterfaceC2State interface_C2_state;
  // Check interface status
  auto result = this->_interface_node_ptr->getC2InterfaceStatus();
  if(!result.Success)
  {
    // Send a log message ("access to interface state impossible" + result.Log;)
    RCLCPP_WARN(this->get_logger(), "_updateC2InterfaceState -> Error while updating interface_c2_status");
    this->_publishSwarmLog(2, "", "_updateC2InterfaceState -> Error while updating interface_c2_status");
    std::cout << result.Log << std::endl;
  }
  else
  {
    interface_C2_state = result.Result.value();
  }
  
  // std::cout << "Centralized Coordination loop" << std::endl;
  // this->_interface_node_ptr->print_from_interface("in manager loop calling interface function");
  return interface_C2_state;
}

void OrchestratorNode::_managerActions(InterfaceC2State c2_interface)
{
  if(c2_interface.flag_new_mission)
  {
    std::cout<< "_managerActions -> add mission mission_id: " << c2_interface.mission_info.mission_config.MissionId << std::endl;
    this->_publishSwarmLog(0, "", "_managerActions -> Adding mission with mission_id " + c2_interface.mission_info.mission_config.MissionId );

    this->_addMission(c2_interface.mission_info.mission_config.MissionId, c2_interface.mission_info.mission_config);    
  }
  if(c2_interface.flag_vehicle_changes)
  {
    if(c2_interface.mission_info.vehicle_change_config.action == 0)
    {
      try
      {
        this->_deleteVehiclesFromMission(c2_interface.mission_id, c2_interface.mission_info.vehicle_change_config.vehicles_list);
      }
      catch(const std::exception& e)
      {
        // Send Log : Error while deleting the vehicle from mission
        RCLCPP_WARN(this->get_logger(), "_managerActions -> Error while deleting vehicle from mission " + *e.what());
        this->_publishSwarmLog(2, "", "_managerActions -> Error while deleting vehicle from mission " + c2_interface.mission_info.mission_config.MissionId );
      }
    }
    else if (c2_interface.mission_info.vehicle_change_config.action == 1)
    {
      try
      {
        this->_addVehiclesToMission(c2_interface.mission_id, c2_interface.mission_info.vehicle_change_config.vehicles_list);
      }
      catch(const std::exception& e)
      {
        // Send Log : Error while deleting the vehicle from mission
        RCLCPP_WARN(this->get_logger(), "_managerActions -> Error while adding vehicle to mission " + *e.what());
        this->_publishSwarmLog(2, "", "_managerActions -> Error while adding vehicle to mission " + c2_interface.mission_info.mission_config.MissionId );

      }
    }
    else
    {
      RCLCPP_WARN(this->get_logger(), "_managerActions -> ChangeVehicle action not listed in the enumeration");
      this->_publishSwarmLog(2, "", "_managerActions -> ChangeVehicle action not listed in the enumeration");
    }

    // get agents from fleet manager, set agents to swarm planner
  }
}

void OrchestratorNode::print_from_manager(std::string message)
{
  std::cout << message << std::endl;
}

/************************************************************/
// Publish Swarm Log (Publisher)                            //
/************************************************************/
void OrchestratorNode::_publishSwarmLog(int log_type, std::string mission_id, std::string log_message)
{
  try
  {
    auto msg = c2_msgs::msg::SwarmLog();
    msg.log_type = log_type;
    msg.log = "[ORCHESTRATOR] "+log_message;
    if (!mission_id.empty()) msg.mission_id = convertStringUuidtoRosUuid(mission_id);
    this->_swarm_log_publisher->publish(msg);
  }

  catch (const std::exception &e)
  {
    RCLCPP_ERROR(this->get_logger(), "_publishSwarmLog -> An error occured during _publishSwarmLog");
  }
}

/************************************************************/
// Swarm Log DB insertion (Subscriber)                            //
/************************************************************/
void OrchestratorNode::_swarm_log_subscriber_callback(const c2_msgs::msg::SwarmLog::SharedPtr msg)
{
  // RCLCPP_INFO(this->get_logger(), "_swarm_log_subscriber_callback -> inserting Swarm Log in DataBase");
  nlohmann::json swarm_log;
  swarm_log["mission_id"] = convertByteArrayToString(msg->mission_id);
  // swarm_log["date"] = msg->date;
  swarm_log["log"] = msg->log;
  swarm_log["log_type"] = msg->log_type;
  this->log_database.databaseAddSwarmLog(swarm_log.dump());
}


/************************************************************/
// Cmd service callback (server)  For Testing               //
/************************************************************/
void OrchestratorNode::_commandService_callback(const std_srvs::srv::Trigger::Request::SharedPtr request, std_srvs::srv::Trigger::Response::SharedPtr response)
{
  try
  {
    RCLCPP_INFO(this->get_logger(), "----------------- I heard a Trigger Command ");
    this->_publishSwarmLog(1,"", "_commandService_callback was detected");


    if (request)
    {
      response->success = true;
      response->message = "Trigger was heard";
    }

    // For testing:
    // this->_addMission(this->_mission_config_example);
  }
  catch (const std::exception &e)
  {
    this->_publishSwarmLog(2, "", "_commandService_callback -> An error occured during _commandService_callback");
    RCLCPP_ERROR(this->get_logger(), "_commandService_callback -> An error occured during _commandService_callback");
  }
}

void OrchestratorNode::_addVehiclesToMission(std::string mission_id, std::vector<std::string> new_vehicles)
{
  // TODO: check vehicles availability
  std::string mission_config_str =  mission_database.databaseFindMission(mission_id);
  if (mission_config_str == "") // Mission not yet in database
  {
    this->_publishSwarmLog(2, mission_id , "_addVehiclesToMission -> Mission ID was not found in the database, vehicles can not be allocated to requested mission");
    RCLCPP_ERROR(this->get_logger(), "_addVehiclesToMission -> Mission ID was not found in the database, vehicles can not be allocated to requested mission");
  }
  else
  {
    nlohmann::json mission_config = this->_json_parser.deserialzeStringToJson(mission_config_str);
    std::vector<std::string> previous_vehicles = mission_config["vehicles"];
    for (std::string new_vehicle : new_vehicles)
    {
      if (std::find(previous_vehicles.begin(), previous_vehicles.end(), new_vehicle) != previous_vehicles.end()) // Only add vehicle if not already present
      {
        RCLCPP_WARN(this->get_logger(), "_addVehiclesToMission -> Vehicle already assigned to this mission: %s", new_vehicle.c_str());
        this->_publishSwarmLog(1,mission_id, "_addVehiclesToMission -> Vehicle already assigned to this mission");
      }
      else
      {
        mission_database.addVehicles(mission_id, new_vehicle);
        this->_publishSwarmLog(0,mission_id, "_addVehiclesToMission -> Vehicle added: "+new_vehicle);

        this->_vehicleChange(mission_id);
      }
    }
  }
}

void OrchestratorNode::_deleteVehiclesFromMission(std::string mission_id, std::vector<std::string> targeted_vehicles)
{
  // TODO: check vehicles availability
  std::string mission_config_str =  mission_database.databaseFindMission(mission_id);
  if (mission_config_str == "") // Mission not yet in database
  {
    this->_publishSwarmLog(2, mission_id, "_deleteVehiclesFromMission -> Mission ID was not found in the database, vehicles can not be deleted from mission");
    RCLCPP_ERROR(this->get_logger(), "_deleteVehiclesFromMission -> Mission ID was not found in the database, vehicles can not be allocated to requested mission");

  }
  else
  {
    nlohmann::json mission_config = this->_json_parser.deserialzeStringToJson(mission_config_str);
    std::vector<std::string> previous_vehicles = mission_config["vehicles"];
    for (std::string deleted_vehicle : targeted_vehicles)
    {
      if (std::find(previous_vehicles.begin(), previous_vehicles.end(), deleted_vehicle) != previous_vehicles.end()) // Only add vehicle if not already present
      {
        mission_database.deleteVehicles(mission_id, deleted_vehicle);
        this->_publishSwarmLog(0, mission_id, "_deleteVehiclesFromMission -> Vehicle was deleted: "+deleted_vehicle);
        this->_vehicleChange(mission_id);
      }
      else
      {
        this->_publishSwarmLog(1, mission_id, "_deleteVehiclesFromMission -> Vehicle was not in database: "+deleted_vehicle);
        RCLCPP_WARN(this->get_logger(), "_deleteVehiclesFromMission -> Vehicle was not in database: %s", deleted_vehicle.c_str());
      }
    }
  }
}

void OrchestratorNode::_recoverMissionsFromDatabase()
{
  auto existing_mission_id_list = mission_database.databaseGetAllMissionIDs();
  for(std::string mission_id : existing_mission_id_list)
  {
    RCLCPP_WARN(this->get_logger(), "_recoverMissionsFromDatabase -> Recovering mission from database: %s",mission_id.c_str());
    this->_publishSwarmLog(1, mission_id, "_recoverMissionsFromDatabase -> Recovering mission from database: "+ mission_id);
    this->_createMissionManagerNode(mission_id, true);
    this->_initialized_missions.push_back(mission_id);

    // std::string mission_config_str =  mission_database.databaseFindMission(mission_id);
    // auto json_result = c2_msgs::json::MissionConfig::FromJsonString(mission_config_str);
    // if(!json_result.Success)
    // {
    //   std::cout << "_recoverMissionsFromDatabase -> Error while parsing Mission Config: " << json_result.Log << std::endl;
    //   this->_publishSwarmLog(2,"", "_recoverMissionsFromDatabase -> Error while parsing Mission Config");
    // }
    // auto &mission_config = json_result.Result.value();
    
    // this->_createPlanner(mission_id, mission_config);
    // this->_createMissionFeedback(mission_id, mission_config);
  }
}

void OrchestratorNode::_addMission( std::string mission_id, c2_msgs::json::MissionConfig mission_config)
{
  if (mission_database.databaseFindMission(mission_id) == "") // Mission not yet in database, expected behavior
  {
    mission_database.databaseAddMission(mission_config.ToJsonString());

    RCLCPP_INFO(this->get_logger(), "_addMission -> Mission config has been added to database for new mission: %s",mission_id.c_str());
    this->_publishSwarmLog(0, mission_id, "_addMission -> Mission config has been added for new mission: "+ mission_id);

    // Check if a node was already created for this mission
    OrchestratorNode::clientStructure client_struct = _getClientStructure(mission_id);
    if (!client_struct.mission_id.empty()) {
      RCLCPP_INFO(this->get_logger(), "_addMission -> A node was already created for this mission: %s",mission_id.c_str());
      this->_publishSwarmLog(0, mission_id, "_addMission -> A node was already created for this mission: "+ mission_id);

      this->_changeMissionStatus(mission_id, (int) c2_msgs::json::enums::MissionStatus::NONE);
    }
  }
  else // In case a new mission is requested with same mission_id (should not be allowed)
  {
    mission_database.databaseUpdateMission(mission_id, mission_config.ToJsonString());
    this->_changeMissionStatus(mission_id, (int) c2_msgs::json::enums::MissionStatus::NONE);

    RCLCPP_INFO(this->get_logger(), "_addMission -> Mission found, updating Mission Config in database for mission %s", mission_id.c_str());
    this->_publishSwarmLog(0, mission_id, "_addMission -> Mission found, updating Mission Config in database for mission: "+ mission_id);
  }
  mission_config.MissionId = mission_id;
  
  
  if (std::find(this->_initialized_missions.begin(), this->_initialized_missions.end(), mission_id) == this->_initialized_missions.end())
  {
    RCLCPP_WARN(this->get_logger(), "The mission id is : %s", mission_id.c_str());
    this->_createMissionManagerNode(mission_id, false);
    this->_initialized_missions.push_back(mission_id);
  }
  // this->_createMissionFeedback(mission_id, mission_config);

}

// void OrchestratorNode::_createMissionFeedback(const std::string mission_id, const c2_msgs::json::MissionConfig mission_config)
// {
// 	c2_msgs::json::MissionFeedback feedback;
// 	feedback.MissionId = mission_id;
// 	feedback.Behavior = mission_config.Behavior;
// 	feedback.Date = std::chrono::system_clock::to_time_t(std::chrono::system_clock::now());
// 	feedback.Status = c2_msgs::json::enums::MissionStatus::NONE;

//   mission_database.databaseAddMissionFeedback(feedback.ToJsonString());
// }

void OrchestratorNode::_deleteMission_callback(const c2_msgs::srv::ChangeMissionStatus::Request::SharedPtr request, c2_msgs::srv::ChangeMissionStatus::Response::SharedPtr response)
{
  std::string mission_id = convertByteArrayToString(request->mission_id);
  RCLCPP_INFO(this->get_logger(), "_deleteMission_callback -> Deleting mission from database: %s", mission_id.c_str());
  this->_publishSwarmLog(0, mission_id, "_deleteMission_callback -> Deleting mission from database: "+ mission_id);
  
  mission_database.databaseDeleteMission(mission_id);
  // this->_initialized_missions.erase(std::remove(this->_initialized_missions.begin(), this->_initialized_missions.end(), mission_id), this->_initialized_missions.end());
  
  response->mission_id = request->mission_id;
  response->mission_status = request->mission_request_status;
  response->error_message = "Mission Deleted";

  // Todo: delete mission from database
  this->_publishSwarmLog(0, mission_id, "_deleteMission_callback -> Mission deleted: "+ mission_id);
  // We should also delete mission from the saved list

}


// void OrchestratorNode::_createPlanner(std::string mission_id, nlohmann::json mission_config)
// {
//     RCLCPP_INFO(this->get_logger(), "Requesting Planner Creation");
//     auto request = std::make_shared<centralized_msgs::srv::CreatePlanner::Request>();
//     request->id = mission_id;
//     request->config = mission_config.dump();
//     using ServiceResponseFuture = rclcpp::Client<centralized_msgs::srv::CreatePlanner>::SharedFuture;
//     auto response_received_callback = [this, mission_id](ServiceResponseFuture future)
//     {
//       auto result = future.get();
//       RCLCPP_INFO(this->get_logger(), "The response state for the Create Planner request is %d", result->state);
//       this->_publishSwarmLog(0, mission_id, "_createPlanner -> Planner creation has been requested to Swarm_Planner for mission: "+mission_id);
//     };
//     auto future_result = this->_create_planner_client->async_send_request(request, response_received_callback);
// }

void OrchestratorNode::_deletePlanner(std::string mission_id)
{
    RCLCPP_INFO(this->get_logger(), "_deletePlanner -> Requesting Planner Deletion");

    auto request = std::make_shared<centralized_msgs::srv::DeletePlanner::Request>();
    request->id = mission_id;
    using ServiceResponseFuture = rclcpp::Client<centralized_msgs::srv::DeletePlanner>::SharedFuture;
    auto response_received_callback = [this, mission_id](ServiceResponseFuture future)
    {
      auto result = future.get();
      RCLCPP_INFO(this->get_logger(), "_deletePlanner -> The response state for the Delete Planner request is %d", result->state);
     this->_publishSwarmLog(0, mission_id, "_deletePlanner -> Planner deletion has been requested to Swarm_Planner for mission: "+mission_id);
    };
    auto future_result = this->_delete_planner_client->async_send_request(request, response_received_callback);
}

void OrchestratorNode::_createMissionManagerNode(std::string mission_id, bool existing_mission)
{
  std::string mission_id_underscores = mission_id;
  std::replace(mission_id_underscores.begin(), mission_id_underscores.end(), '-', '_'); // replace all '-' to '_'

  RCLCPP_INFO(this->get_logger(), "_createMissionManagerNode -> Creating MissionManager Node Instance");
  this->_publishSwarmLog(0, mission_id, "_createMissionManagerNode -> creating multi-agent mission service node for mission: "+mission_id);
  auto MissionManager_node = std::make_shared<MissionManager>(mission_id_underscores, existing_mission);
  // Spin in another thread
  std::thread thrd(std::bind(&OrchestratorNode::_spinNode, this, MissionManager_node));
  thrd.detach();

  // Create clients for intra process communication with multi agent mission service nodes
  OrchestratorNode::clientStructure clients_structure;
  clients_structure.mission_id = mission_id;
  
  clients_structure.change_mission_status_client_ = this->create_client<c2_msgs::srv::ChangeMissionStatus>("multi_robot/mission_"+mission_id_underscores+"/mission_status_change", rmw_qos_profile_default, this->_cb_grp_ext);
  clients_structure.environment_change_client_ = this->create_client<std_srvs::srv::Trigger>("multi_robot/mission_"+mission_id_underscores+"/environment_change", rmw_qos_profile_default, this->_cb_grp_ext);
  clients_structure.vehicle_change_client_ = this->create_client<std_srvs::srv::Trigger>("multi_robot/mission_"+mission_id_underscores+"/vehicle_change", rmw_qos_profile_default, this->_cb_grp_ext);

  while (!clients_structure.change_mission_status_client_->wait_for_service(1s) || !clients_structure.environment_change_client_->wait_for_service(1s) || !clients_structure.vehicle_change_client_->wait_for_service(1s))
  {
    if (!rclcpp::ok())
    {
      RCLCPP_ERROR(rclcpp::get_logger("rclcpp"), "_createMissionManagerNode -> Interrupted while waiting for the MissionManager services. Exiting.");
      this->_publishSwarmLog(2, mission_id, "_createMissionManagerNode -> multi-agent mission service node not available for mission: "+mission_id);
      exit(1);
    }
    RCLCPP_INFO(rclcpp::get_logger("rclcpp"), "_createMissionManagerNode ->  MissionManager services not available yet, waiting again...");
    this->_publishSwarmLog(1, mission_id, "_createMissionManagerNode -> multi-agent mission service node not available yet, waiting again... for mission: "+mission_id);
  }

  this->_clients_struct_list.push_back(clients_structure);
}

void OrchestratorNode::_spinNode(std::shared_ptr<MissionManager> MissionManager_node)
{
  rclcpp::spin(MissionManager_node);
}

void OrchestratorNode::_changeMissionStatus(std::string mission_id, int requested_status)
{
  std::string mission_config_str =  mission_database.databaseFindMission(mission_id);
  if (mission_config_str == "") // Mission not yet in database
  {
    this->_publishSwarmLog(2, mission_id , "_changeMissionStatus -> Mission ID was not found in the database, Need to initialize mission");
    RCLCPP_ERROR(this->get_logger(), "_changeMissionStatus -> Mission ID was not found in the database, Need to initialize mission");
  }
  if (std::find(this->_initialized_missions.begin(), this->_initialized_missions.end(), mission_id) == this->_initialized_missions.end())
  { // MissionManager node not created yet (mission not initialized)
    this->_publishSwarmLog(2,"", "_changeMissionStatus -> Mission was not initialized yet");
    RCLCPP_ERROR(this->get_logger(), "_changeMissionStatus -> Mission was not initialized yet: %s", mission_id.c_str());
  }
  else
  {
    RCLCPP_INFO(this->get_logger(), "_changeMissionStatus -> Requesting mission status change to MissionManager for mission %s", mission_id.c_str());
    this->_publishSwarmLog(0, mission_id, "_changeMissionStatus -> Requesting mission status change to multi-agent mission service, for mission: "+mission_id);


    auto request = std::make_shared<c2_msgs::srv::ChangeMissionStatus::Request>();
    request->mission_id = convertStringUuidtoRosUuid(mission_id);
    request->mission_request_status = requested_status;

    using ServiceResponseFuture = rclcpp::Client<c2_msgs::srv::ChangeMissionStatus>::SharedFuture;
    auto response_received_callback = [this](ServiceResponseFuture future) 
    {
      auto result = future.get();
      RCLCPP_INFO(this->get_logger(), "------> The result for MISSION STATUS CHANGE is %d", result->mission_status);
      // rclcpp::shutdown();
    };
    auto future_result = this->_getClientStructure(mission_id).change_mission_status_client_->async_send_request(request, response_received_callback);
  }
}

void OrchestratorNode::_environmentChange()
{
  auto request = std::make_shared<std_srvs::srv::Trigger::Request>();

  RCLCPP_INFO(this->get_logger(), "_environmentChange ->  Informing every MissionManager about environment change");

  auto existing_mission_id_list = mission_database.databaseGetAllMissionIDs();
  for(std::string mission_id : existing_mission_id_list)
  {
    using ServiceResponseFuture = rclcpp::Client<std_srvs::srv::Trigger>::SharedFuture;
    auto response_received_callback = [this, mission_id](ServiceResponseFuture future) 
    {
      auto result = future.get();
      RCLCPP_INFO(this->get_logger(), "_environmentChange -> Informed %s\n", mission_id.c_str());
      // rclcpp::shutdown();
    };
    auto future_result = this->_getClientStructure(mission_id).environment_change_client_->async_send_request(request, response_received_callback);
  }
}

void OrchestratorNode::_vehicleChange(std::string mission_id)
{
  auto request = std::make_shared<std_srvs::srv::Trigger::Request>();

  RCLCPP_INFO(this->get_logger(), "_vehicleChange ->  Informing MissionManager about vehicle change");
  this->_publishSwarmLog(0, mission_id, "_vehicleChange -> Informing multi-agent mission service about vehicle change, for mission: "+mission_id);

  using ServiceResponseFuture = rclcpp::Client<std_srvs::srv::Trigger>::SharedFuture;
  auto response_received_callback = [this](ServiceResponseFuture future) 
  {
    auto result = future.get();
    RCLCPP_INFO(this->get_logger(), "_vehicleChange -> The result for VEHICLE CHANGE is %d\n", result->success);
    // rclcpp::shutdown();
  };
  auto future_result = this->_getClientStructure(mission_id).vehicle_change_client_->async_send_request(request, response_received_callback);
}

OrchestratorNode::clientStructure OrchestratorNode::_getClientStructure(std::string mission_id)
{
  auto finder = std::find_if(this->_clients_struct_list.cbegin(), this->_clients_struct_list.cend(), 
                             [&mission_id](const clientStructure& c) {
                               return c.mission_id == mission_id;
                             });

  OrchestratorNode::clientStructure clients_structure;
  
  if (finder != this->_clients_struct_list.cend()) {
    clients_structure.mission_id = mission_id;
    clients_structure.change_mission_status_client_ = finder->change_mission_status_client_;
    clients_structure.environment_change_client_ = finder->environment_change_client_;
    clients_structure.vehicle_change_client_ = finder->vehicle_change_client_;
  } 
  else 
  {
    RCLCPP_WARN(this->get_logger(), "_getClientStructure -> multi-agent mission service was not found for requested mission id");
    this->_publishSwarmLog(1, mission_id, "_getClientStructure -> multi-agent mission service was not found for requested mission id: " + mission_id);
    
    // Set an empty or invalid mission_id to indicate "not found"
    clients_structure.mission_id = "";  
  }
  
  return clients_structure;
}

void OrchestratorNode::setRequestMissionChangeStatus(const std::string mission_id, const c2_msgs::json::enums::MissionStatusRequest status_request){this->_changeMissionStatus(mission_id, (int) status_request);}
int OrchestratorNode::getMissionStatus(const std::string mission_id)
{ 
  std::string status_str = this->mission_database.databaseFindObject(mission_id, (std::string)"status");
  return (int) std::stoi(status_str.c_str());
}

// std::vector<std::string> OrchestratorNode::getFeedbacks()
// {
//   std::vector<std::string> feedbacks;
//   for(std::string mission_id : this->_list_active_mission)
//   {
//     RCLCPP_INFO(this->get_logger(), "get mission: %s from database", mission_id.c_str());
//     auto json_str = this->mission_database.databaseFindMissionFeedback(mission_id);
//     std::cout << json_str << std::endl;
//     feedbacks.push_back(json_str);
//   }
  
//   return feedbacks;
// }

std::shared_ptr<OrchestratorNode> OrchestratorNode::get_ptr()
{
    return std::shared_ptr<OrchestratorNode>(this);
}

