/****************************************************************/
// Central Coordination - Mission Manager Node (one for each instantiated mission)
// Alexandre La Grappe & Emile Le Flecher  - RMA - alexandre.lagrappe@mil.be or emile.leflecher@mil.be 
// 03.12.2024 - V1.0
/****************************************************************/

// One node for every instantiated mission runtime, for managing its runtime state

// Header File:
#include "centralized_coordination/mission_manager_header.hpp"

using namespace c2_msgs::json::enums;


MissionManager::MissionManager(std::string mission_id, bool existing_mission) : Node("mission_" + mission_id)
{
  RCLCPP_INFO(this->get_logger(), "Mission Manager Node ----> Initialization");
  this->_cb_grp_int = this->create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
  
  this->_mission_id_underscores = mission_id;
  std::replace(mission_id.begin(), mission_id.end(), '_', '-'); // replace all '_' to '-'
  this->_mission_id = mission_id;

  this->_getMissionConfig();

  this->_initPlannerInterface();
  this->_initC2Interface(this->_mission_id);
  this->_initIntraProcessComms();
  this->_initCmdServices();
  this->_initPublishers();

  this->setInitialMissionStatus(existing_mission);

  // while(this->_waiting_location)
  // {
  // this->_createPlanner();
  // }
  

  this->_timer_state_machine = this->create_wall_timer(50ms, std::bind(&MissionManager::_stateMachineCallback, this), this->_cb_grp_int);
  this->_timer_planner_connection = this->create_wall_timer(1000ms, std::bind(&MissionManager::_swarm_planner_connection_timer_callback, this), this->_cb_grp_int);
  this->_timer_replannification = this->create_wall_timer(1000ms, std::bind(&MissionManager::_plannification_timer_callback, this), this->_cb_grp_int);


  RCLCPP_INFO(this->get_logger(), "New Mission Manager Node initialized");
  this->_publishSwarmLog(0,this->_mission_id , "New Mission Manager Node initialized");
}

MissionManager::~MissionManager()
{
}

/************************************************************/
// Init comms                                               //
/************************************************************/

void MissionManager::_initPlannerInterface()
{
  /*********** Planning Request Client ****************/
  this->_get_plan_client = this->create_client<centralized_msgs::srv::GetPlan>("/multi_robot/planner/get_plan", rmw_qos_profile_default, this->_cb_grp_int);

  /*********** Create Planner Client ****************/
  this->_create_planner_client = this->create_client<centralized_msgs::srv::CreatePlanner>("/multi_robot/planner/create", rmw_qos_profile_default, this->_cb_grp_int);

  /*********** Update Planner Agents Client ****************/
   this->_update_planner_agents_client = this->create_client<centralized_msgs::srv::UpdatePlannerAgents>("/multi_robot/planner/set_agents", rmw_qos_profile_default, this->_cb_grp_int);

  /*********** Planning Subscriber ****************/
  this->_planning_subscriber = this->create_subscription<centralized_msgs::msg::PlanCalculated>("/multi_robot/planner/planner_calculated", 10, std::bind(&MissionManager::_planning_subscriber_callback, this, _1));

  /*********** Planner state Subscriber ****************/
  this->_planner_state_subscriber = this->create_subscription<std_msgs::msg::String>("/multi_robot/planner/state", 10, std::bind(&MissionManager::_planner_state_subscriber_callback, this, _1));


}

// Communication with swarm_manager_node
void MissionManager::_initIntraProcessComms()
{
    /*********** Agent Task Completed Subscriber (from fleet manager) ****************/
  // this->_agent_task_completed_subscriber = this->create_subscription<std_msgs::msg::String>("/multi_robot/agent_completed_tasks", 10, std::bind(&MissionManager::_agent_task_completed_subscriber_callback, this, _1));

  /*********** Change Mission Status Server ****************/
  this->_change_mission_status_server = this->create_service<c2_msgs::srv::ChangeMissionStatus>("multi_robot/mission_" + this->_mission_id_underscores + "/mission_status_change", std::bind(&MissionManager::_changeMissionStatus_callback, this, _1, _2), rmw_qos_profile_services_default, this->_cb_grp_int);

  /*********** Environment Change Server ****************/
  this->_environment_change_server = this->create_service<std_srvs::srv::Trigger>("multi_robot/mission_" + this->_mission_id_underscores + "/environment_change", std::bind(&MissionManager::_environmentChange_callback, this, _1, _2), rmw_qos_profile_services_default, this->_cb_grp_int);

  /*********** Vehicle Change Server ****************/
  this->_vehicle_change_server = this->create_service<std_srvs::srv::Trigger>("multi_robot/mission_" + this->_mission_id_underscores + "/vehicle_change", std::bind(&MissionManager::_vehicleChange_callback, this, _1, _2), rmw_qos_profile_services_default, this->_cb_grp_int);

  /*********** Mission can be deleted Publisher ****************/
  this->_delete_mission_client = this->create_client<c2_msgs::srv::ChangeMissionStatus>("multi_robot/delete_mission", rmw_qos_profile_default, this->_cb_grp_int);

  /*********** Get vehicle localizations ****************/
  this->_get_agent_client = this->create_client<centralized_msgs::srv::GetAgents>("multi_robot/fleet_manager/get_agents", rmw_qos_profile_default, this->_cb_grp_int);

  /*********** Send Tasks to Edge from Fleet manager ****************/
  this->_send_tasks_client = this->create_client<c2_msgs::srv::InitMission>("multi_robot/fleet_manager/send_tasks", rmw_qos_profile_default, this->_cb_grp_int);

/*********** Ask Fleet manager to start tasks at Edge ****************/
  this->_change_agent_task_status_client = this->create_client<c2_msgs::srv::ChangeMissionStatus>("multi_robot/fleet_manager/change_mission_status", rmw_qos_profile_default, this->_cb_grp_int);

/*********** Edge Feedback Subscriber ****************/
  this->_edge_feedback_subscriber = this->create_subscription<task_msgs::msg::Feedback>("/multi_robot/edge/feedback", 10, std::bind(&MissionManager::_edge_feedback_subscriber_callback, this, _1));

/*********** Wait for services ****************/
  while(!this->_delete_mission_client->wait_for_service(1s) || !this->_get_agent_client->wait_for_service(1s) || !this->_send_tasks_client->wait_for_service(1s) || !this->_change_agent_task_status_client->wait_for_service(1s))
  {
    if(!rclcpp::ok())
    {
      RCLCPP_ERROR(this->get_logger(), "_initIntraProcessComms -> Services not responding");
      this->_publishSwarmLog(2,"", "_initIntraProcessComms -> Services not responding");
    }
    RCLCPP_WARN(this->get_logger(), " _initIntraProcessComms -> waiting for services to wake up");
  }
}

void MissionManager::_initC2Interface(std::string mission_id)
{
  // C2 QOS settings
  rclcpp::QoS c2_qos = rclcpp::QoS(
    rclcpp::QoSInitialization(
      rmw_qos_profile_services_default.history,
      rmw_qos_profile_services_default.depth
    ),
    rmw_qos_profile_services_default);
  if (this->_c2_qos_avoid_ros_prefix){
    c2_qos.avoid_ros_namespace_conventions(true);
    // c2_qos.depth(size_t(1));
    c2_qos.history(RMW_QOS_POLICY_HISTORY_KEEP_LAST);
  };

  // Initial mission feedback message 
  this->_mission_feedback.MissionId = mission_id;
  this->_mission_feedback.Status = MissionStatus::NONE;
  this->_mission_feedback.RequestedStatus = MissionStatusRequest::INIT;
  // this->_mission_feedback.Behavior = this->_mission_config.Behavior; 
  this->_mission_feedback.Behavior = (this->_mission_config.at("behavior").get<int>() == 0) ? Behavior::NAVIGATE : Behavior::COVERAGE;
  this->_mission_feedback.Issue = MissionIssue::NONE;

  /*********** Mission Feedback Publisher ****************/
  this->_mission_feedback_publisher = this->create_publisher<c2_msgs::msg::MissionFeedback>("/multi_robot/mission_feedback", c2_qos);
  this->_timer_mission_feedback = this->create_wall_timer(1000ms, std::bind(&MissionManager::_publishMissionFeedback, this), this->_cb_grp_int);

  /*********** C2 response for change mission status ****************/
  this->_change_mission_status_pub_ptr = this->create_publisher<c2_msgs::msg::ChangeMissionStatusResponse>("/multi_robot/change_mission_status_response", c2_qos);

}

void MissionManager::_initPublishers()
{
  this->_swarm_log_publisher = this->create_publisher<c2_msgs::msg::SwarmLog>("/multi_robot/log", 10);
}

void MissionManager::_initCmdServices()
{
  /*********** Trigger Command Server - for development ****************/
  this->_cmd_server = this->create_service<std_srvs::srv::Trigger>("multi_robot/mission_" + this->_mission_id_underscores + "/cmd", std::bind(&MissionManager::_commandService_callback, this, _1, _2), rmw_qos_profile_services_default, this->_cb_grp_int);
}

/************************************************************/
// Get Mission Config from DataBase                  //
/************************************************************/
void MissionManager::_getMissionConfig()
{
  this->_mission_config_str = _runtime_database.databaseFindMission(this->_mission_id);
  if (this->_mission_config_str == "")
  {
    RCLCPP_ERROR(this->get_logger(), "_getMissionConfig -> Mission was not found in database");
    this->_publishSwarmLog(2, this->_mission_id, "_getMissionConfig -> Mission configuration was not found in database");
  }
  else 
  {
    this->_mission_config = this->_json_parser.deserialzeStringToJson(this->_mission_config_str);
  }  
}

/************************************************************/
// Publish Swarm Log (Publisher)                  //
/************************************************************/
void MissionManager::_publishSwarmLog(int log_type, std::string mission_id, std::string log_message)
{
  try
  {
    auto msg = c2_msgs::msg::SwarmLog();
    msg.log_type = log_type;
    msg.log = "[MISSION MANAGER " +mission_id+"]"+log_message;
    if(!mission_id.empty()) msg.mission_id = convertStringUuidtoRosUuid(mission_id);
    this->_swarm_log_publisher->publish(msg);
    // RCLCPP_WARN(this->get_logger(), "LOG PUBLISHED");
  }

  catch (const std::exception &e)
  {
    RCLCPP_ERROR(this->get_logger(), "An error occured during _publishSwarmLog");
  }
}

/************************************************************/
// Set Initial Mission Status                               //
/************************************************************/
void MissionManager::setInitialMissionStatus(bool existing_mission)
{
  // Recover mission from database in case it was already running before
  std::string latest_mission_feedback_str = _feedback_database.databaseFindLatestFeedback(this->_mission_id);
  if (existing_mission && latest_mission_feedback_str!="") // In case mission id already existed, continue with latest status (in case of restart of Centralized Coordination module) 
  {
    auto json_result = c2_msgs::json::MissionFeedback::FromJsonString(latest_mission_feedback_str);
    if(!json_result.Success)
    {
      RCLCPP_ERROR(this->get_logger(), "setInitialMissionStatus -> Error while parsing Mission Feedback: %s",json_result.Log.c_str());
      this->_publishSwarmLog(2,this->_mission_id, "MissionManager init -> Error while parsing Mission Feedback: "+json_result.Log);
    }
    auto latest_mission_feedback = json_result.Result.value();
    this->_state = (int) latest_mission_feedback.Status;

    // Check if need to plan mission or not
    if (this->_state == (int) MissionStatus::STOPPED || this->_state == (int) MissionStatus::DELETED || this->_state == (int) MissionStatus::FAILED){
      this->_plannification_needed_flag = false;
    }
    else {
      this->_plannification_needed_flag = true; // Mission needs to be replanned as things might have changed since restart
    }
    RCLCPP_ERROR(this->get_logger(), "setInitialMissionStatus -> State recovered from DataBase (Mission Feedback): %d",this->_state);
  }
  else // mission id seems to be new, start with initial state NONE
  {
    this->_state = (int) MissionStatus::NONE ; // NONE
  }
  this->_new_mission_status = this->_state;
  this->_change_mission_status_flag = true;
}

void MissionManager::_swarm_planner_connection_timer_callback()
{
  this->_planner_connection_counter +=1;
  if (this->_connected_to_swarm_planner && this->_planner_connection_counter >= 10) // seconds without planner state message
  {
    this->_connected_to_swarm_planner = false;
    this->_planner_service_state = 3; // Disconnected state
    RCLCPP_WARN(this->get_logger(), "_swarm_planner_connection_timer_callback -> DISCONNECTED FROM SWARM PLANNER");
    this->_publishSwarmLog(1,this->_mission_id, "_swarm_planner_connection_timer_callback -> DISCONNECTED FROM SWARM PLANNER");
  }
}

void MissionManager::_agent_task_completed(std::string agent_id)
{
  // Register agent has finished its tasks
  if (!std::count(this->_finished_vehicles.begin(), this->_finished_vehicles.end(), agent_id)) 
  {
    RCLCPP_INFO(this->get_logger(), "Agent completed its tasks: %s", agent_id.c_str());
    this->_finished_vehicles.push_back(agent_id);
    
    // Check if all agents completed their tasks

    std::sort(this->_finished_vehicles.begin(), this->_finished_vehicles.end());
    std::sort(this->_planned_mission_vehicles.begin(), this->_planned_mission_vehicles.end());

    if (this->_finished_vehicles == this->_planned_mission_vehicles) 
    {
      RCLCPP_INFO(this->get_logger(), "All agents completed their tasks, MISSION COMPLETED");
      this->_new_mission_status = (int) MissionStatus::COMPLETED;
      this->_change_mission_status_flag = true;
    }
  }
}


/************************************************************/
// Request Planning                                            //
/************************************************************/
void MissionManager::_requestPlanning() // Request planning to swarm planner
{
  try
  {
    auto get_plan_request = std::make_shared<centralized_msgs::srv::GetPlan::Request>();
    get_plan_request->id = this->_mission_id;
    using ServiceResponseFuture = rclcpp::Client<centralized_msgs::srv::GetPlan>::SharedFuture;
    auto planning_received_callback = [this](ServiceResponseFuture future)
    {
      auto result = future.get();

      if (result->plan == "")
      {
        this->_mission_feedback.Issue = MissionIssue::PLANNING_FAILED_NO_SOLUTION_FOUND;
        RCLCPP_ERROR(this->get_logger(), "_requestPlanning -> RECEIVED EMPTY STRING");
        this->_publishSwarmLog(2, this->_mission_id, "_requestPlanning -> RECEIVED EMPTY STRING");
        
        // Change mission status to FAILED
        this->_change_mission_status_flag = true;
        this->_new_mission_status = (int) MissionStatus::FAILED;
      }
      if (result->plan.find("\"tasks\":[]") != std::string::npos)
      {
        this->_mission_feedback.Issue = MissionIssue::PLANNING_FAILED_NO_SOLUTION_FOUND;
        RCLCPP_ERROR(this->get_logger(), "_requestPlanning -> RECEIVED EMPTY TASK LIST");
        this->_publishSwarmLog(2, this->_mission_id, "_requestPlanning -> RECEIVED EMPTY TASK LIST");
      }
      else
      {
        RCLCPP_INFO(this->get_logger(), "_requestPlanning -> Planning received: %s", result->plan.c_str());
        this->_publishSwarmLog(0, this->_mission_id, "_requestPlanning -> Planning received from Swarm Planner");
        this->_mission_feedback.Issue = MissionIssue::NONE;

        // Save planning
        this->_register_planning_result(result->plan);

        // Change mission status to PLANNED
        this->_change_mission_status_flag = true;
        this->_new_mission_status = (this->_replannification_needed_flag)? (int) MissionStatus::PLANNED_ALTERNATIVE : (int) MissionStatus::PLANNED;
        this->_plannification_needed_flag = false;
        this->_replannification_needed_flag = false;
      }
      this->_waiting_for_planner_response = false;
    };
    this->_waiting_for_planner_response = true;
    auto plan_future_result = this->_get_plan_client->async_send_request(get_plan_request, planning_received_callback);
  }

  catch (const std::exception &e)
  {
    RCLCPP_ERROR(this->get_logger(), "_requestPlanning -> A std exception was thrown during planning request");
    this->_publishSwarmLog(2, this->_mission_id, "_requestPlanning -> A std exception was thrown during planning request");
    this->_mission_feedback.Issue = MissionIssue::PLANNING_FAILED_NO_SOLUTION_FOUND;
  }
  catch (char *c)
  {
    RCLCPP_ERROR(this->get_logger(), "_requestPlanning -> An error occured during planning request");
    this->_publishSwarmLog(2, this->_mission_id, "_requestPlanning -> An error occured during planning request");
  }
}

/************************************************************/
// Create Planner for mission                                //
/************************************************************/
void MissionManager::_createPlanner()
{
  RCLCPP_INFO(this->get_logger(), "_createPlanner -> Requesting Planner Creation, included agents:");
  this->_publishSwarmLog(0, this->_mission_id, "_createPlanner -> Requesting Planner Creation");

  std::vector<std::string> vehicles_str = this->_mission_config.at("vehicles").get<std::vector<std::string>>();

  std::vector<unique_identifier_msgs::msg::UUID> vehicles_uuid_list;
  for(auto vehicle : vehicles_str)
  {
    RCLCPP_INFO(this->get_logger(), "agent: %s", vehicle.c_str());
    vehicles_uuid_list.push_back(convertStringUuidtoRosUuid(vehicle));
  }
  // Request agent information to Fleet manager
  auto get_agents_request = std::make_shared<centralized_msgs::srv::GetAgents::Request>();
  get_agents_request->agent_id_list = vehicles_uuid_list;

  using ServiceResponseFuture = rclcpp::Client<centralized_msgs::srv::GetAgents>::SharedFuture;
  auto agents_received_callback = [this](ServiceResponseFuture future)
  {
    RCLCPP_INFO(this->get_logger(), "_createPlanner -> Agent info received from Fleet manager");
    auto result = future.get();
    auto mission_agents = result->agents;
    if (mission_agents.size()==0)
    {
      RCLCPP_ERROR(this->get_logger(), "_createPlanner -> Agent info received, but it is empty!");
      this->_publishSwarmLog(1,this->_mission_id , "_createPlanner -> Agent info received from fleet manager is empty!");
    }

    auto request = std::make_shared<centralized_msgs::srv::CreatePlanner::Request>();
    request->id = this->_mission_id;
    request->config = this->_mission_config_str;
    request->priority=0;
    request->agents = mission_agents;

    using ServiceResponseFuture = rclcpp::Client<centralized_msgs::srv::CreatePlanner>::SharedFuture;
    auto response_received_callback = [this](ServiceResponseFuture future)
    { 
      auto result = future.get();
      int planner_state = result->state;
      if (planner_state==0 || planner_state==1 || planner_state==2) // Normal or calculating
      {
        
        RCLCPP_INFO(this->get_logger(), "_createPlanner -> Planner created, actual state: %d", planner_state);
        this->_publishSwarmLog(0,this->_mission_id , "_createPlanner -> Planner created");
      }
      else 
      {
        RCLCPP_ERROR(this->get_logger(), "_createPlanner -> Failed to create planner");
        this->_publishSwarmLog(1,this->_mission_id , "_createPlanner -> Failed to create planner!");
      }
      
    };
    auto future_result = this->_create_planner_client->async_send_request(request, response_received_callback);

  };
  auto agents_future_result = this->_get_agent_client->async_send_request(get_agents_request, agents_received_callback);
}

void MissionManager::_setConnectedToSwarmPlanner()
{
  this->_connected_to_swarm_planner = true;
  this->_planner_connection_counter = 0; // reset counter, Connected to swarm planner
  if (! this->_connected_to_swarm_planner)
  {
    RCLCPP_INFO(this->get_logger(), "_planner_state_subscriber_callback -> CONNECTED TO SWARM PLANNER");
  }
}

/************************************************************/
// Planner State Subscription Callback                                           //
/************************************************************/

void MissionManager::_planner_state_subscriber_callback(const std_msgs::msg::String::SharedPtr msg)
{
  this->_setConnectedToSwarmPlanner();

  // Deserialize JSON from the message
  nlohmann::json planner_state_json = this->_json_parser.deserialzeStringToJson(msg->data);

  // Check if "planners" key exists and is an array
  if (planner_state_json.contains("planners") && planner_state_json["planners"].is_array())
  {
    for (const auto &planner : planner_state_json["planners"])
    {
      if (planner.contains("mission_id") && planner.contains("state") &&
          planner["mission_id"].get<std::string>() == this->_mission_id)
      {
        this->_planner_service_state = planner["state"].get<int>();
        // this->_publishSwarmLog(0,this->_mission_id , "_planner_state_subscriber_callback -> planner status: "+ std::to_string(this->_planner_service_state));

        
        return;  // Exit early once the correct mission_id is found
      }
    }
  }

  // In case of error state
  if (this->_planner_service_state == 4) // ERROR
  {
    this->_mission_feedback.Issue = MissionIssue::PLANNING_FAILED;
    RCLCPP_ERROR(this->get_logger(), "_planner_state_subscriber_callback -> Swarm Planner Service state: ERROR");
    this->_publishSwarmLog(1, this->_mission_id, "_planner_state_subscriber_callback -> Swarm Planner Service state: ERROR");
    return;
  }  

  // If mission_id not found, set default state
  this->_planner_service_state = -1;
}

/************************************************************/
// Planning Subscription Callback                                           //
/************************************************************/
void MissionManager::_planning_subscriber_callback(const centralized_msgs::msg::PlanCalculated::SharedPtr msg)
{
  if (msg->id == this->_mission_id)
  {
    std::string planning = msg->plan;
    // this->_plan_calculated_flag = true;
  }
}

/************************************************************/
// Upload Planning to DB and include it in Mission Feedback    //
/************************************************************/
void MissionManager::_register_planning_result(std::string planning_result_str)
{
    this->_planning_json = this->_json_parser.deserialzeStringToJson(planning_result_str);
    this->_planning_json["mission_id"] = this->_mission_id;
    std::vector<c2_msgs::json::MissionFeedbackTask> mission_feedback_tasks_vec;

    this->_planned_mission_vehicles.clear();

    for (const auto &task : this->_planning_json["tasks"].items()) // Process each agent task
    {
        std::string agent_id = task.key();
        this->_planned_mission_vehicles.push_back(agent_id);

        std::string task_uuid_str = task.value()["task_id"].get<std::string>();  // Use the existing task_id

        c2_msgs::json::MissionFeedbackTask mission_feedback_task;
        mission_feedback_task.VehicleId = agent_id;
        mission_feedback_task.TaskId = task_uuid_str;

        std::vector<c2_msgs::json::MissionFeedbackTaskWaypoint> mission_feedback_task_waypoints_vec;

        for (const auto &objective : task.value()["objectives"].items()) 
        {
            for (const auto &primitive : objective.value()["primitives"].items()) 
            {
                std::string prim_id = primitive.value()["primitive_id"].get<std::string>(); // Extract primitive ID

                // Look up the primitive in task["primitives"]
                auto primitives_list = task.value()["primitives"];
                auto it = std::find_if(primitives_list.begin(), primitives_list.end(),
                                      [&prim_id](const auto &p) {
                                          return p["primitive_id"] == prim_id;
                                      });

                if (it != primitives_list.end() && (*it)["primitive_type"] == "waypoint") 
                {
                    c2_msgs::json::MissionFeedbackTaskWaypoint mission_feedback_WP;

                    // Extract coordinates and speed from the objective's parameters
                    if (primitive.value().contains("parameters")) 
                    {
                        auto params = primitive.value()["parameters"];
                        
                        if (params.contains("coordinates")) 
                        {
                            mission_feedback_WP.Coordinates.Lat = params["coordinates"][1].get<float>(); // Latitude
                            mission_feedback_WP.Coordinates.Lng = params["coordinates"][0].get<float>(); // Longitude
                        }
                        if (params.contains("speed")) 
                        {
                            mission_feedback_WP.AverageSpeed = params["speed"].get<float>();
                        }
                    }

                    // Generate an ETA (or use actual data if available)
                    mission_feedback_WP.Eta = std::chrono::system_clock::to_time_t(std::chrono::system_clock::now());

                    // Assign the waypoint_id from the primitive_id
                    mission_feedback_WP.waypoint_id = prim_id;

                    // Add to vector
                    mission_feedback_task_waypoints_vec.push_back(mission_feedback_WP);
                }
            }
        }



        mission_feedback_task.Waypoints = mission_feedback_task_waypoints_vec;
        mission_feedback_tasks_vec.push_back(mission_feedback_task);
    }
    this->_mission_feedback.Tasks = mission_feedback_tasks_vec;

    _runtime_database.databaseUpdatePlanning(this->_mission_id, this->_planning_json.dump());
}





/************************************************************/
// State Machine                                            //
/************************************************************/
void MissionManager::_stateMachineCallback()
{
  try
  {
    if (this->_change_mission_status_flag)
    {
      if (this->_new_mission_status == this->_state || this->_allowed_transitions[this->_new_mission_status] == true)
      {
        this->_state = this->_new_mission_status;
        this->_change_mission_status_flag = false;
        this->_updateAllowedTransitions(this->_state);
        RCLCPP_INFO(this->get_logger(), "_stateMachineCallback -> MISSION STATUS: %s", this->_get_status_string(this->_state).c_str());
        this->_publishSwarmLog(0,this->_mission_id , "_stateMachineCallback -> MISSION STATUS: "+ this->_get_status_string(this->_state));
        this->_mission_feedback.Status = static_cast<MissionStatus>(this->_state);// c2_msgs::json::enums::EnumsTools::MissionStatusEnum(this->_state); //c2_msgs::json::enums::MissionStatus::NONE; // enums::MissionStatus MissionStatusEnum
        

        this->_stateMachineActions();
      }
      else
      {
        this->_publishSwarmLog(0,this->_mission_id , "_stateMachineCallback -> Requested status change not allowed: "+ std::to_string(this->_new_mission_status));
      }
    }
    else
    {
      // do nothing
    }
  }
  catch (const std::exception &e)
  {
    RCLCPP_ERROR(this->get_logger(), "_stateMachineCallback -> An error occured during _stateMachineCallback");
    this->_publishSwarmLog(2,this->_mission_id , "_stateMachineCallback -> An error occured during _stateMachineCallback");
  }
}

/************************************************************/
// Process to try getting the planning                                    //
/************************************************************/
void MissionManager::_getPlanning_try()
{
  switch (this->_planner_service_state)
  {
  case -1: // Swarm Planner Service not available yet
    this->_mission_feedback.Issue = MissionIssue::MISSION_FAILED_DISCONNECTED_SWARM_PLANNER;
    RCLCPP_WARN(this->get_logger(), "_getPlanning_try -> Swarm Planner Service not available");
    this->_publishSwarmLog(1,this->_mission_id , "_getPlanning_try -> Swarm Planner Service not available");
    this->_createPlanner();
    break;  // Prevent fall-through

  case 0: // Swarm Planner Service initialized
    return; // Need to wait for the planner to start planning

  case 1: // Swarm Planner Service is still planning
    return; // Need to wait for the planner to finish planning

  case 2: // Plan should be available
    this->_requestPlanning();
    break;  // Prevent fall-through

  case 3: // Disconnected state
    this->_mission_feedback.Issue = MissionIssue::MISSION_FAILED_DISCONNECTED_SWARM_PLANNER;
    RCLCPP_WARN(this->get_logger(), "_getPlanning_try -> Swarm Planner DISCONNECTED");
    this->_publishSwarmLog(1,this->_mission_id , "_getPlanning_try -> Swarm Planner DISCONNECTED");
    break;  // Prevent fall-through

  case 4: // Planning Failed state
    this->_mission_feedback.Issue = MissionIssue::PLANNING_FAILED;
    RCLCPP_WARN(this->get_logger(), "_getPlanning_try -> Swarm Planner ERROR");
    this->_publishSwarmLog(1,this->_mission_id , "_getPlanning_try -> Swarm Planner ERROR");
    break;  // End of switch
  }
}


void MissionManager::_plannification_timer_callback()
{
  if ((this->_plannification_needed_flag || this->_replannification_needed_flag) && !this->_waiting_for_planner_response)
  {
    // this->_createPlanner();
    this->_getPlanning_try();
  }
}

/************************************************************/
// State Machine Actions                                    //
/************************************************************/
// TODO: Add enum for tasks and change type of this->_state to enum (no int cast needed)
void MissionManager::_stateMachineActions()
{
  switch (this->_state)
  {
  case (int) MissionStatus::NONE:
    /* Initializing state */
    this->_active_mission = true;
    this->_getMissionConfig();
    this->_createPlanner();
    this->_plannification_needed_flag = true;
    break;
  case (int) MissionStatus::PLANNED:
    this->_active_mission = true;
    /* Planned state */
    break;
  case (int) MissionStatus::PLANNED_ALTERNATIVE:
  /* Replanned state */
    this->_agents_need_task_updates_flag = true;
    break;
  case (int) MissionStatus::PLANNED_FAILED:
     /* Plannification Failed state */
    this->_change_mission_status_flag = true;
    this->_new_mission_status = (int) MissionStatus::FAILED;
    break;
  case (int) MissionStatus::ACCEPTED:
    /* Accepted */
    this->_sendAgentTasks();
    // Wait for start
    break;
  case (int) MissionStatus::STARTED:
    /* Started state */
    if (this->_agents_need_task_updates_flag)
    {
      this->_sendAgentTasks(); // Send tasks to all agents
    }
    this->_changeAgentTaskStatuses(1); // execute
    break;
  case (int) MissionStatus::PAUSED:
    /* Pausing state */
    this->_changeAgentTaskStatuses(2); //pause
    
    break;
  case (int) MissionStatus::FAILED:
    /* FAIL state */
    this->_changeAgentTaskStatuses(0); // Stop agents
    this->_change_mission_status_flag = true;
    this->_new_mission_status = (int) MissionStatus::NONE; // Start again
    break;
  case (int) MissionStatus::STOPPED:
    /* Stopping state */
    this->_changeAgentTaskStatuses(0); // stop agents
    this->_plannification_needed_flag = false;
    break;
  case (int) MissionStatus::DELETED:
    /* Deleting state */
    // this->_changeAgentTaskStatuses(0); // stop agents
    this->_plannification_needed_flag = false;
    this->_active_mission = false;
    this->_deleteMission();
    break;
  case (int) MissionStatus::COMPLETED:
    this->_active_mission = false;
    // DO NOTHING
    // this->_deleteMission();
    break;
    default:
    break;
  }
}

std::string MissionManager::_get_status_string(int status)
{
  std::vector<std::string> status_enum_list{ "NONE (0)", "PLANNED (1)", "PLANNED_ALTERNATIVE (2)", "PLANNED_FAILED (3)", "APPROVED (4)", "STARTED (5)", "PAUSED (6)", "FAILED (7)", "STOPPED (8)", "DELETED (9)", "COMPLETED (10)" };
  return status_enum_list[status];
}

/************************************************************/
// update alowed transitions                                //
/************************************************************/
void MissionManager::_updateAllowedTransitions(int new_state)
{
  std::vector<int> allowed_indices;                       // Vector to keep indices of possible transitions
  std::vector<bool> allowed_transitions_vector(11, false); // make all transitions impossible by default

  if (new_state == (int) MissionStatus::NONE) // Initializing
    allowed_indices.insert(allowed_indices.end(), {(int) MissionStatus::NONE, (int) MissionStatus::PLANNED, (int) MissionStatus::STOPPED, (int) MissionStatus::FAILED, (int) MissionStatus::DELETED});
  else if (new_state == (int) MissionStatus::PLANNED) // Plannification
    allowed_indices.insert(allowed_indices.end(), {(int) MissionStatus::NONE, (int) MissionStatus::PLANNED_ALTERNATIVE, (int) MissionStatus::ACCEPTED, (int) MissionStatus::STOPPED, (int) MissionStatus::FAILED, (int) MissionStatus::DELETED});
  else if (new_state == (int) MissionStatus::PLANNED_ALTERNATIVE) // Replannification
    allowed_indices.insert(allowed_indices.end(), {(int) MissionStatus::NONE, (int) MissionStatus::ACCEPTED, (int) MissionStatus::STOPPED, (int) MissionStatus::FAILED, (int) MissionStatus::DELETED});
  else if (new_state == (int) MissionStatus::PLANNED_FAILED) // Planning fail
    allowed_indices.insert(allowed_indices.end(), {(int) MissionStatus::STOPPED, (int) MissionStatus::FAILED});
  else if (new_state == (int) MissionStatus::ACCEPTED) // Accepted
    allowed_indices.insert(allowed_indices.end(), {(int) MissionStatus::NONE, (int) MissionStatus::PLANNED_ALTERNATIVE, (int) MissionStatus::ACCEPTED, (int) MissionStatus::STARTED, (int) MissionStatus::STOPPED, (int) MissionStatus::FAILED, (int) MissionStatus::DELETED});
  else if (new_state == (int) MissionStatus::STARTED) // Started
    allowed_indices.insert(allowed_indices.end(), {(int) MissionStatus::NONE, (int) MissionStatus::PLANNED_ALTERNATIVE, (int) MissionStatus::PAUSED, (int) MissionStatus::FAILED, (int) MissionStatus::STOPPED, (int) MissionStatus::COMPLETED, (int) MissionStatus::DELETED});
  else if (new_state == (int) MissionStatus::PAUSED) // Paused
    allowed_indices.insert(allowed_indices.end(), {(int) MissionStatus::NONE, (int) MissionStatus::PLANNED_ALTERNATIVE, (int) MissionStatus::STARTED, (int) MissionStatus::FAILED, (int) MissionStatus::STOPPED, (int) MissionStatus::COMPLETED, (int) MissionStatus::DELETED});
  else if (new_state == (int) MissionStatus::FAILED) // Fail
    allowed_indices.insert(allowed_indices.end(), {(int) MissionStatus::NONE, (int) MissionStatus::STOPPED, (int) MissionStatus::COMPLETED, (int) MissionStatus::DELETED});
  else if (new_state == (int) MissionStatus::STOPPED) // Stopped
    allowed_indices.insert(allowed_indices.end(), {(int) MissionStatus::NONE, (int) MissionStatus::STARTED, (int) MissionStatus::FAILED, (int) MissionStatus::DELETED});
  else if (new_state == (int) MissionStatus::DELETED) // Deleted
    allowed_indices.insert(allowed_indices.end(), {(int) MissionStatus::NONE});
  else if (new_state == (int) MissionStatus::COMPLETED) // Completed
    allowed_indices.insert(allowed_indices.end(), {(int) MissionStatus::NONE, (int) MissionStatus::STOPPED, (int) MissionStatus::DELETED});

  for (int i : allowed_indices)
  {
    allowed_transitions_vector[i] = true;
  }

  this->_allowed_transitions = allowed_transitions_vector;
}

/************************************************************/
// Publish Delete Mission  to Centralized Coordination (Publisher)      //
/************************************************************/
void MissionManager::_deleteMission()
{
  try
  {
    // TODO: Delete mission from vehicles

    // Inform Swarm_Manager that mission can now be deleted:
    RCLCPP_INFO(this->get_logger(), "_deleteMission -> Requesting Mission Deletion");
    this->_publishSwarmLog(0,this->_mission_id , "_deleteMission -> Requesting Mission Deletion");

    auto request = std::make_shared<c2_msgs::srv::ChangeMissionStatus::Request>();
    request->mission_id = convertStringUuidtoRosUuid(this->_mission_id);
    request->mission_request_status = 8;
    using ServiceResponseFuture = rclcpp::Client<c2_msgs::srv::ChangeMissionStatus>::SharedFuture;
    auto response_received_callback = [this](ServiceResponseFuture future)
    {
      auto result = future.get();
      RCLCPP_INFO(this->get_logger(), "_deleteMission ->  %s", result->error_message.c_str());
    };
    auto future_result = this->_delete_mission_client->async_send_request(request, response_received_callback);
  }

  catch (const std::exception &e)
  {
    RCLCPP_ERROR(this->get_logger(), "_deleteMission -> An error occured during _deleteMission method");
    this->_publishSwarmLog(2,this->_mission_id , "_deleteMission -> An error occured during _deleteMission method");
  }
}

void MissionManager::_edge_feedback_subscriber_callback(const task_msgs::msg::Feedback::SharedPtr msg)
{
  if (this->_mission_feedback.Tasks.has_value() && !msg->tasks.empty())
  {
    std::string agent_id = msg->agent_id;
    task_msgs::msg::TaskFeedback task_feedback = msg->tasks[0];
    std::string task_feedback_id = task_feedback.task_id;
    auto task_vec = this->_mission_feedback.Tasks.value();
    int i=0;
    for (auto task : task_vec) {
      if (task.VehicleId == agent_id && task_feedback_id == task.TaskId)
      {
        auto waypoints = task.Waypoints.value();

        if (msg->tasks[0].task_state == (uint8_t) 3)
        {
          this->_agent_task_completed(agent_id);
          // waypoints.clear(); // Clear waypoint list if task was COMPLETED
        }
        std::string waypoint_id = msg->tasks[0].current_objective_id;        
        // Remove the previous waypoints from the current task
        long unsigned int N = 0;
        for (N = 0; N <= waypoints.size(); N++) {
          if (N == waypoints.size())
          {
            break;
          }

          if (waypoint_id == waypoints[N].waypoint_id) {
              break;
          }
        }
        if (N > 0 && N < waypoints.size()) 
        {
          waypoints.erase(waypoints.begin(),waypoints.begin() + N);      
        }
        task_vec[i].Waypoints.emplace(waypoints); 
        break;
      }
      i++;
    }
    this->_mission_feedback.Tasks.emplace(task_vec);   
  }
}

/************************************************************/
// Publish Mission Feedback to c2 (Publisher)                  //
/************************************************************/
void MissionManager::_publishMissionFeedback()
{
  try
  {
    if (!this->_active_mission){
      this->_mission_feedback.Tasks =std::vector<c2_msgs::json::MissionFeedbackTask>(); // Clear it as the tasks as they are not wanted anymore
    }

    this->_mission_feedback.Date = std::chrono::system_clock::to_time_t(std::chrono::system_clock::now());

    c2_msgs::json::MissionFeedback mission_feedback_to_send = this->_mission_feedback;

    // Truncate each task to first 50 waypoints
    if ( this->_mission_feedback.Tasks.has_value())
    {
      auto task_vec = this->_mission_feedback.Tasks.value();
      std::vector<c2_msgs::json::MissionFeedbackTask> new_task_vec;

      for (size_t i = 0; i < task_vec.size(); i++) {
          auto task = task_vec[i];
          auto waypoints = task.Waypoints.value();
          if (waypoints.size() >50)
          {
            waypoints.erase(waypoints.begin()+50 , waypoints.end());
          }
          task.Waypoints.emplace(waypoints);
          new_task_vec.push_back(task);
      }
      mission_feedback_to_send.Tasks.emplace(new_task_vec);
    }
        
    std::string mission_feedback_string = mission_feedback_to_send.ToJsonString();
    _feedback_database.databaseAddMissionFeedback(mission_feedback_string);

    auto msg = c2_msgs::msg::MissionFeedback();
    msg.mission_feedback = mission_feedback_string;
    msg.mission_id = convertStringUuidtoRosUuid(this->_mission_id);
    this->_mission_feedback_publisher->publish(msg);
  }
  catch (const std::exception &e)
  {
    RCLCPP_ERROR(this->get_logger(), "_publishMissionFeedback -> An error occured during _publishMissionFeedback");
    this->_publishSwarmLog(2,this->_mission_id , "_publishMissionFeedback -> An error occured during _publishMissionFeedback method");
  }
}

/************************************************************/
// Change mission runtime state callback (Server) //
/************************************************************/
void MissionManager::_changeMissionStatus_callback(const c2_msgs::srv::ChangeMissionStatus::Request::SharedPtr request, c2_msgs::srv::ChangeMissionStatus::Response::SharedPtr response)
{
  try
  {
    c2_msgs::msg::ChangeMissionStatusResponse c2_response;
    c2_response.mission_id = request->mission_id;

    this->_mission_feedback.RequestedStatus = (c2_msgs::json::enums::MissionStatusRequest) request->mission_request_status; //c2_msgs::json::enums::EnumsTools::MissionStatusRequestToEnum(request->mission_request_status);  

    int maybe_new_mission_status = this->_convert_requested_status_to_mission_status(request->mission_request_status);
    if (this->_allowed_transitions[maybe_new_mission_status] == true) // If the requested transition is a possible one
    {
      RCLCPP_INFO(this->get_logger(), "_changeMissionStatus_callback -> I heard that I should change my state to '%d'", maybe_new_mission_status);
      this->_publishSwarmLog(0,this->_mission_id , "_changeMissionStatus_callback -> Mission status change request, requested state:" + std::to_string(request->mission_request_status));

      this->_change_mission_status_flag = true;
      this->_new_mission_status = maybe_new_mission_status;

      response->mission_id = convertStringUuidtoRosUuid(this->_mission_id);
      response->mission_status = this->_new_mission_status;
      response->error_message = "";

      c2_response.mission_status = this->_new_mission_status;
    }
    else
    {
      RCLCPP_ERROR(this->get_logger(), "_changeMissionStatus_callback -> IMPOSSIBLE TRANSITION REQUESTED");
      this->_publishSwarmLog(1,this->_mission_id , "_changeMissionStatus_callback -> IMPOSSIBLE TRANSITION REQUESTED");

      response->mission_id = convertStringUuidtoRosUuid(this->_mission_id);
      response->mission_status = this->_state;
      response->error_message = "Impossible transition";

      c2_response.mission_status = this->_state;
    }

    
    this->_change_mission_status_pub_ptr->publish(c2_response);
  }

  catch (const std::exception &e)
  {
    RCLCPP_ERROR(this->get_logger(), "_changeMissionStatus_callback -> An error occured during _changeMissionStatus_callback");
    this->_publishSwarmLog(2,this->_mission_id , "_changeMissionStatus_callback -> An error occured during _changeMissionStatus_callback");
  }
}
/************************************************************/
// Convert a MissionStatusRequest to a MissionStatus  //
/************************************************************/
int MissionManager::_convert_requested_status_to_mission_status(int mission_request_status)
{

  switch (mission_request_status)
  {
  case (int) MissionStatusRequest::INIT:
    return (int) MissionStatus::NONE;

  case (int) MissionStatusRequest::APPROVE:
    return (int) MissionStatus::ACCEPTED;

  case (int) MissionStatusRequest::START:
    return (int) MissionStatus::STARTED;

  case (int) MissionStatusRequest::PAUSE:
    return (int) MissionStatus::PAUSED;

  case (int) MissionStatusRequest::STOP:
    return (int) MissionStatus::STOPPED;

  case (int) MissionStatusRequest::DELETE:
    return (int) MissionStatus::DELETED;
  default:
    {
      RCLCPP_ERROR(this->get_logger(), "_convert_requested_status_to_mission_status -> Error in 'MissionStatus', enum unknown");
      this->_publishSwarmLog(2,this->_mission_id , "_convert_requested_status_to_mission_status -> Error in 'MissionStatus', enum unknown");
      return this->_state;
    }
  }
}
/************************************************************/
// Environment Change Callback (Server) //
/************************************************************/
void MissionManager::_environmentChange_callback(const std_srvs::srv::Trigger::Request::SharedPtr request, std_srvs::srv::Trigger::Response::SharedPtr response)
{
  try
  {
    if (request)
    {
      RCLCPP_INFO(this->get_logger(), "_environmentChange_callback -> I heard that the Environment has changed");
      this->_publishSwarmLog(0,this->_mission_id , "_environmentChange_callback -> environment change will be handled");

      response->success = true;
      response->message = "ok";
    }

    // New plan should be calculated
    this->_change_mission_status_flag = true;
    // this->_plan_calculated_flag = false;
    this->_replannification_needed_flag = true;
    this->_new_mission_status = (int) c2_msgs::json::enums::MissionStatus::PAUSED; // pause mission, replannification will be launched after pausing

  }

  catch (const std::exception &e)
  {
    RCLCPP_ERROR(this->get_logger(), "_environmentChange_callback -> An error occured during _environmentChange_callback");
    this->_publishSwarmLog(2,this->_mission_id , "_environmentChange_callback -> An error occured during _environmentChange_callback");
  }
}

/************************************************************/
// Vehicle Change Callback (Server) //
/************************************************************/
void MissionManager::_vehicleChange_callback(const std_srvs::srv::Trigger::Request::SharedPtr request, std_srvs::srv::Trigger::Response::SharedPtr response)
{
  try
  {
    if (request)
    {
      RCLCPP_INFO(this->get_logger(), "_vehicleChange_callback -> I heard that the vehicles have changed");
      this->_publishSwarmLog(0,this->_mission_id , "_vehicleChange_callback -> vehicle change will be handled");

      response->success = true;
      response->message = "ok";
    }

    // New plan should be calculated
    this->_change_mission_status_flag = true;
    // this->_plan_calculated_flag = false;
    this->_replannification_needed_flag = true;
    this->_new_mission_status = (int) c2_msgs::json::enums::MissionStatus::PAUSED; // pause mission, replannification will be launched after pausing

    this->_getMissionConfig(); // update mission config from DB
    // this->_updatePlannerAgents(); // update planner agents
  }

  catch (const std::exception &e)
  {
    RCLCPP_ERROR(this->get_logger(), "_vehicleChange_callback -> An error occured during _vehicleChange_callback");
    this->_publishSwarmLog(2,this->_mission_id , "_vehicleChange_callback -> An error occured during _vehicleChange_callback");
  }
}

void MissionManager::_updatePlannerAgents()
{
  std::vector<std::string> vehicles_str = this->_mission_config.at("vehicles").get<std::vector<std::string>>();
  std::vector<unique_identifier_msgs::msg::UUID> vehicles_uuid_list;
  for (auto vehicle : vehicles_str)
  {
    vehicles_uuid_list.push_back(convertStringUuidtoRosUuid(vehicle));
  };
  // Request agent information to Fleet manager
  auto get_agents_request = std::make_shared<centralized_msgs::srv::GetAgents::Request>();
  get_agents_request->agent_id_list = vehicles_uuid_list;

  using ServiceResponseFuture = rclcpp::Client<centralized_msgs::srv::GetAgents>::SharedFuture;
  auto agents_received_callback = [this](ServiceResponseFuture future)
  {
    auto result = future.get();
    auto mission_agents = result->agents;
    if (mission_agents.size() == 0)
    {
      RCLCPP_ERROR(this->get_logger(), "_vehicleChange_callback -> Agent info received, but it is empty!");
      this->_publishSwarmLog(1, this->_mission_id, "_vehicleChange_callback -> Agent info received from fleet manager is empty!");
    }
    auto request = std::make_shared<centralized_msgs::srv::UpdatePlannerAgents::Request>();
    request->id = this->_mission_id;
    request->agents = mission_agents;
    using ServiceResponseFuture = rclcpp::Client<centralized_msgs::srv::UpdatePlannerAgents>::SharedFuture;
    auto response_received_callback = [this](ServiceResponseFuture future)
    {
      auto result = future.get();
      RCLCPP_INFO(this->get_logger(), "_vehicleChange_callback -> Vehicles changed for planner: %s", result->id.c_str());
    };
    auto future_result = this->_update_planner_agents_client->async_send_request(request, response_received_callback);
  };

  auto agents_future_result = this->_get_agent_client->async_send_request(get_agents_request, agents_received_callback);
}

void MissionManager::_sendAgentTasks()
{
  
  auto request = std::make_shared<c2_msgs::srv::InitMission::Request>();
  request->mission_id = convertStringUuidtoRosUuid(this->_mission_id);
  request->mission_config = ""; // Does not matter

  using ServiceResponseFuture = rclcpp::Client<c2_msgs::srv::InitMission>::SharedFuture;
  auto response_received_callback = [this](ServiceResponseFuture future) 
  {
    auto result = future.get();
    RCLCPP_INFO(this->get_logger(), "_sendAgentTasks -> tasks will be sent by fleet manager");
    this->_publishSwarmLog(0,this->_mission_id , "_sendAgentTasks -> tasks will be sent by fleet manager");

    this->_finished_vehicles.clear(); // all agents have new tasks, so no agent has finished its task

  };
  auto future_result = this->_send_tasks_client->async_send_request(request, response_received_callback);

  this->_agents_need_task_updates_flag = false;
}

void MissionManager::_changeAgentTaskStatuses(int task_status)
{
        // STOP = 0,    // request to stop the task & re-init
        // EXECUTE = 1, // request to execute the task
        // PAUSE = 2,   // request to pause the task
        // DELETE = 3   // request to delete the task

  auto request = std::make_shared<c2_msgs::srv::ChangeMissionStatus::Request>();
  request->mission_id = convertStringUuidtoRosUuid(this->_mission_id);
  request->mission_request_status = task_status;

  using ServiceResponseFuture = rclcpp::Client<c2_msgs::srv::ChangeMissionStatus>::SharedFuture;
  auto response_received_callback = [this, task_status](ServiceResponseFuture future) 
  {
    auto result = future.get();
    RCLCPP_INFO(this->get_logger(), "_changeAgentTaskStatuses -> fleet manager will set tasks statuses to: %d", task_status);
    this->_publishSwarmLog(0,this->_mission_id , "_changeAgentTaskStatuses -> fleet manager will set tasks statuses to: "+ std::to_string(task_status));
  };
  auto future_result = this->_change_agent_task_status_client->async_send_request(request, response_received_callback);
}



/************************************************************/
// Cmd service callback (server)                            //
// Currently not in use                                    //
/************************************************************/
void MissionManager::_commandService_callback(const std_srvs::srv::Trigger::Request::SharedPtr request, std_srvs::srv::Trigger::Response::SharedPtr response)
{
  try
  {
    RCLCPP_INFO(this->get_logger(), "CMD SERVICE -  _commandService_callback triggered ");
    this->_publishSwarmLog(0,this->_mission_id , "CMD SERVICE -  _commandService_callback triggered");

    if (request)
    {
      response->success = true;
      response->message = "Trigger was heard";
    }
  }

  catch (const std::exception &e)
  {
    RCLCPP_ERROR(this->get_logger(), "_commandService_callback -> An error occured during _commandService_callback");
    this->_publishSwarmLog(2,this->_mission_id , "_commandService_callback -> An error occured during _commandService_callback");
  }
}
