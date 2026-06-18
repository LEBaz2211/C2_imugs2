/****************************************************************/
/*    Code to test custom message which are sent from C2        */
/*    Emile Le Flecher - RMA - 24.02.2022                       */
/****************************************************************/
# include <centralized_coordination/test/test_c2.hpp>

TestC2::TestC2(/* args */) : Node("test_c2_node")
{
  
  this->_C2_callback_group_ptr = this->create_callback_group(rclcpp::CallbackGroupType::Reentrant);
  this->_planner_callback_group_ptr = this->create_callback_group(rclcpp::CallbackGroupType::Reentrant);

  this->_LoadMissionConfigFile(); 

  this->_initSwarmManagerInterface();
  this->_initPlannerInterface();

  std::cout << "All interfaces initialized" << std::endl;

  this->_timer = this->create_wall_timer(500ms, std::bind(&TestC2::_callbackSimu, this),this->_C2_callback_group_ptr);

  std::cout << "end of config" << std::endl;
  
}


/****************************************************************/

TestC2::~TestC2()
{
}

/****************************************************************/

void TestC2::_callbackSimu()
{
  std::cout << "------------------------------- \n ------------------------------- \n ------------------------------- " << std::endl;
  std::cout << "Current Mission ID: " << this->_mission_id << std::endl;
  std::cout << "m: set mission id, r: reload mission config file\n" << std::endl;

  std::cout << "i: init_mission, s: Change mission status, v: change vehicles, e: environment" << std::endl;
  
  
  char trigger;
  std::cin >> trigger;
  std::cout << "trigger: ";
  if(trigger == 'm')
  {
    std::cout << "New Mission ID: " << std::endl;
    
    std::string new_mission_id;
    std::cin >> new_mission_id;

    this->_mission_id = new_mission_id;
  }

  if(trigger == 'r')
  {
    this->_LoadMissionConfigFile(); 
  }

  if(trigger == 'i')
  {
    std::cout << "send a new mission" << std::endl;
    this->_sendInitMission();
  }
  if(trigger == 's')
  {
    std::cout << "change swarm status request" << std::endl;
    std::cout << "INIT = 0,    // Initialize mission\n"
         "APPROVE = 1, // Approve mission\n"
         "START = 2,   // Start mission\n"
         "PAUSE = 3,   // Pause mission\n"
         "STOP = 4,    // Stop mission\n"
         "DELETE = 5   // Delete mission" << std::endl;
    
    int requested_state;
    std::cin >> requested_state;

    this->_sendChangeStatus(requested_state);
  }
  if(trigger == 'v')
  {
    std::cout << "change swarm vehicles request" << std::endl;
    std::cout << "REMOVE = 0,    // remove vehicles\n"
         "ADD = 1   // add vehicles" << std::endl;
    
    int requested_action;
    std::cin >> requested_action;

    std::cout << "Vehicle ID:" << std::endl;
    std::string vehicle_id;
    std::cin >> vehicle_id;

    this->_sendVehiclesChanges(requested_action, vehicle_id);
  }

  if(trigger == 'e')
  {
    std::cout << "Environment request" << std::endl;
    std::cout << "RESET = r \n"
         "UPLOAD = u \n"
         "VERSION = v" << std::endl;
    
    std::string requested_action;
    std::string requested_upload_action;
    std::string requested_geojson_file;

    std::cin >> requested_action;
    
    if(requested_action == "u")
    {
      std::cout << "Environment upload action:" << std::endl;
      std::cout << "INSERT = i \n"
          "UPDATE = u \n"
          "DELETE = d" << std::endl;
      
      std::cin >> requested_upload_action;

      if(requested_upload_action == "i" || requested_upload_action == "u" )
      {
        std::cout << "Select geojson file:" << std::endl;
        std::cout << "b = blue_force_geofences\n" 				
            "c = comms_geofences\n" 				
            "e = enemy_geofences\n" 				
            "o = obstacle_geofences\n" 				
            "g = generic_geofences\n" 				
            "m = max_speed_zones\n" 				
            "f = gnss_forbidden_zones\n" 				
            "s = silent_zones\n" 				
            "d = detection_notification_zones\n" 				
            "p = observation_points\n" 				
            "d = observation_directions\n" 				
            << std::endl;
        std::cin >> requested_geojson_file;
      }

      this->_environmentRequest(requested_action, requested_upload_action, requested_geojson_file);
    }
    
  }

  trigger = 0;
  
}


void TestC2::_LoadMissionConfigFile()
{
  try
  {
    this->_mission_config = this->_readJsonFile(this->_test_json_path, "mission_config.json");    
    std::cout << "Mission Config file loaded\n" << this->_mission_config << std::endl;

  }
  catch(const std::exception& e)
  {
    std::cerr << "Error while reading json files" << e.what() << '\n';
  }

  RCLCPP_INFO(this->get_logger(), " ------ All json files loaded");
}

void TestC2::_initPlannerInterface()
{
  this->_create_planner_srv_ptr = this->create_service<centralized_msgs::srv::CreatePlanner>("multi_robot/planner/create", std::bind(&TestC2::_createPlanner, this, _1, _2), rmw_qos_profile_default, this->_planner_callback_group_ptr);
  // this->_delete_planer_srv_ptr = this->create_service<centralized_msgs::srv::DeletePlanner>("multi_robot/planner/delete", std::bind(&TestC2::_deletePlanner, this, _1,_2), rmw_qos_profile_default, this->_planner_callback_group_ptr);
  // this->_create_planner_srv_ptr = this->create_service<centralized_msgs::srv::CreatePlanner>("/multi_robot/planner/create", std::bind(&TestC2::_createPlanner,this,std::placeholders::_1,std::placeholders::_2),rmw_qos_profile_default,this->_C2_callback_group_ptr);
}


/********************************** ******************************/
// C2 Interface
/****************************************************************/

/** Client comms initialization for initMission message **/
void TestC2::_initSwarmManagerInterface ()
{
  // QoS
  rclcpp::QoS swarm_manager_qos = rclcpp::QoS(
    rclcpp::QoSInitialization(
      rmw_qos_profile_services_default.history,
      rmw_qos_profile_services_default.depth
    ),
    rmw_qos_profile_services_default);
  if (this->_swarm_manager_qos_avoid_ros_prefix){swarm_manager_qos.avoid_ros_namespace_conventions(true);};

  this->_init_mission_sub_ptr = this->create_subscription<c2_msgs::msg::InitMissionResponse>("/multi_robot/mission_init_response", swarm_manager_qos, std::bind(&TestC2::_initMissionResponseCallback, this, _1));
  this->_init_mission_pub_ptr = this->create_publisher<c2_msgs::msg::InitMissionRequest>("/multi_robot/mission_init_request", swarm_manager_qos);

  this->_change_mission_status_sub_ptr = this->create_subscription<c2_msgs::msg::ChangeMissionStatusResponse>("/multi_robot/change_mission_status_response", swarm_manager_qos, std::bind(&TestC2::_changeMissionStatusResponseCallback, this, _1));
  this->_change_mission_status_pub_ptr = this->create_publisher<c2_msgs::msg::ChangeMissionStatusRequest>("/multi_robot/change_mission_status_request", swarm_manager_qos);

  this->_change_mission_vehicles_sub_ptr = this->create_subscription<c2_msgs::msg::ChangeMissionVehicleResponse>("/multi_robot/change_mission_vehicle_response", swarm_manager_qos, std::bind(&TestC2::_changeMissionVehicleResponseCallback, this, _1));
  this->_change_mission_vehicles_pub_ptr = this->create_publisher<c2_msgs::msg::ChangeMissionVehicleRequest>("/multi_robot/change_mission_vehicle_request", swarm_manager_qos);

  this->_mission_feedback_sub_ptr = this->create_subscription<c2_msgs::msg::MissionFeedback>("/multi_robot/mission_feedback", swarm_manager_qos, std::bind(&TestC2::_getMissionFeedback, this, _1));

  this->_swarm_log_sub_ptr = this->create_subscription<c2_msgs::msg::SwarmLog>("/multi_robot/log", swarm_manager_qos, std::bind(&TestC2::_logCallback, this, _1));

  // Environment Data
  this->_env_data_reset_req_pub_ptr = this->create_publisher<environment_msgs::msg::EnvironmentDataResetRequest>("/multi_robot/reset_data_request", swarm_manager_qos);
  this->_env_data_upload_req_pub_ptr = this->create_publisher<environment_msgs::msg::EnvironmentDataUploadRequest>("/multi_robot/upload_data_request", swarm_manager_qos);
  this->_env_data_version_req_pub_ptr = this->create_publisher<environment_msgs::msg::EnvironmentDataGetVersionRequest>("/multi_robot/get_version_request", swarm_manager_qos);  

}



/** Function to simulate an initMission request from C2 **/
void TestC2::_sendInitMission()
{
  c2_msgs::msg::InitMissionRequest request;
  
  request.mission_id = convertStringUuidtoRosUuid(this->_mission_id);

  // std::cout << "mission config: " << this->_json_parser.serializeJsonToString(this->_mission_config) << std::endl;
  this->_mission_config_str = this->_mission_config.dump();
  request.mission_config = this->_mission_config_str;
  std::cout << request.mission_config << std::endl;

  this->_init_mission_pub_ptr->publish(request);
}

void TestC2::_initMissionResponseCallback(const c2_msgs::msg::InitMissionResponse::SharedPtr msg)
{
  std::cout << "response from the swarm: " << convertRosUuidtoStringUuid(msg.get()->mission_id) << " with the feedback: " << msg.get()->mission_feedback << std::endl;
}

void TestC2::_changeMissionStatusResponseCallback(const c2_msgs::msg::ChangeMissionStatusResponse::SharedPtr msg)
{
  std::cout << "response for mission status change received for mission: " << convertRosUuidtoStringUuid(msg.get()->mission_id) << std::endl;
}
void TestC2::_changeMissionVehicleResponseCallback(const c2_msgs::msg::ChangeMissionVehicleResponse::SharedPtr msg)
{
  std::cout << "response for mission vehicle change received for mission: " << convertRosUuidtoStringUuid(msg.get()->mission_id) << std::endl;
}

/** Function to simulate a status change request from C2 **/
void TestC2::_sendChangeStatus(int requested_state)
{
  c2_msgs::msg::ChangeMissionStatusRequest request;
  request.mission_id = convertStringUuidtoRosUuid(this->_mission_id);
  request.mission_request_status = requested_state;//std::uint8_t(c2_msgs::json::enums::MissionStatusRequest::INIT);

  this->_change_mission_status_pub_ptr->publish(request);
}

/** Function to simulate a vehicle change request from C2 **/
void TestC2::_sendVehiclesChanges(int requested_action, std::string vehicle_id)
{
  c2_msgs::msg::ChangeMissionVehicleRequest request;
  /* build message */

  std::vector<std::string> vehicle_list;
  
  vehicle_list.push_back(vehicle_id);
  // vehicle_list.push_back("fcee3176_50f6_11ec_bf63_0242ac130001");
  
  request.mission_id = convertStringUuidtoRosUuid(this->_mission_id);
  request.vehicle_changes = std::uint8_t(requested_action);
  request.vehicule_id_list = vehicle_list;

  this->_change_mission_vehicles_pub_ptr->publish(request);
}

void TestC2::_environmentRequest(std::string requested_action, std::string requested_upload_action, std::string requested_geojson_file)
{
  boost::uuids::uuid request_boost_uuid = boost::uuids::random_generator()();
  std::string request_uuid_str = boost::uuids::to_string(request_boost_uuid);
  auto request_ros_uuid = convertStringUuidtoRosUuid(request_uuid_str);

  if(requested_action=="r")
  {
    environment_msgs::msg::EnvironmentDataResetRequest request;
    request.request_id = request_ros_uuid;
    this->_env_data_reset_req_pub_ptr->publish(request);
  }
  if(requested_action=="v")
  {
    environment_msgs::msg::EnvironmentDataGetVersionRequest request;
    request.request_id = request_ros_uuid;
    this->_env_data_version_req_pub_ptr->publish(request);
  }
  if(requested_action=="u")
  {
    environment_msgs::msg::EnvironmentDataUploadRequest request;
    request.request_id = request_ros_uuid;
    request.version_nr = (uint8_t) std::rand();
    request.insert_geojson = "";
    request.update_geojson = "";
    request.delete_json = "";

    if(requested_upload_action == "d")
    {
      request.delete_json = this->_readJsonFile(this->_test_json_path, "geojson/deletion.json");    ;
    }
    else
    {
      std::string geojson_file_name;
      if (requested_geojson_file == "b")
      {
        geojson_file_name = "blue_force_geofences.json";
      }
      if (requested_geojson_file == "c")
      {
        geojson_file_name = "comms_geofences.json";
      }
      if (requested_geojson_file == "e")
      {
        geojson_file_name = "enemy_geofences.json";
      }
      if (requested_geojson_file == "o")
      {
        geojson_file_name = "obstacle_geofences.json";
      }
      if (requested_geojson_file == "g")
      {
        geojson_file_name = "generic_geofences.json";
      }
      if (requested_geojson_file == "m")
      {
        geojson_file_name = "max_speed_zones.json";
      }
      if (requested_geojson_file == "gf")
      {
        geojson_file_name = "gnss_forbidden_zones.json";
      }
      if (requested_geojson_file == "s")
      {
        geojson_file_name = "silent_zones.json";
      }
      if (requested_geojson_file == "d")
      {
        geojson_file_name = "detection_notification_zones.json";
      }
      if (requested_geojson_file == "op")
      {
        geojson_file_name = "observation_points.json";
      }
      if (requested_geojson_file == "od")
      {
        geojson_file_name = "observation_directions.json";
      }

      // Construct message

      if (requested_geojson_file == "i")
      {
        request.insert_geojson = this->_readJsonFile(this->_test_json_path, geojson_file_name);
      }
      if (requested_geojson_file == "u")
      {
        request.update_geojson = this->_readJsonFile(this->_test_json_path, geojson_file_name);
      }
    }
    this->_env_data_upload_req_pub_ptr->publish(request);
  }
  
}



void TestC2::_getMissionFeedback(const c2_msgs::msg::MissionFeedback &feedback)
{
  this->_mission_feedback_msg = feedback;
  // std::cout << "get mission feedback, mission_id: " << feedback.mission_id << ", feedback: " << feedback.mission_feedback << std::endl;
}

void TestC2::_logCallback(const c2_msgs::msg::SwarmLog &log_msg)
{
  this->log = log_msg;
  // std::cout << "log sub, mission_id: " << log_msg.mission_id << ", with the message: " << log_msg.log << std::endl;
}
/****************************************************************/

json TestC2::_readJsonFile(std::string json_path, std::string json_file_name)
{
   return this->_json_parser.readJsonFile(json_path, json_file_name);
}

/****************************************************************/
// PLANNER INTERFACE TEST
/****************************************************************/

void TestC2::_createPlanner(const std::shared_ptr<centralized_msgs::srv::CreatePlanner::Request> request, std::shared_ptr<centralized_msgs::srv::CreatePlanner::Response> response)
{
  // std::cout << "create planner srv, create planner: id: " << request->id << "config: " << request->config << std::endl;
  response->id = request->id;
  response->state = std::uint8_t(centralized_msgs::json::enums::PlanStatus::NONE); // needs to build enums
  return void();
}

void TestC2::_deletePlanner(const std::shared_ptr<centralized_msgs::srv::DeletePlanner::Request> request, std::shared_ptr<centralized_msgs::srv::DeletePlanner::Response> response)
{
  // std::cout << "delete planner, delete planner: id: " << request->id << std::endl;
  response->id = request->id;
  response->state = std::uint8_t(centralized_msgs::json::enums::PlanStatus::NONE);
}





/****************************************************************/
/****************************************************************/
/****************************************************************/

int main(int argc, char ** argv)
{
  (void) argc;
  (void) argv;
  
  rclcpp::init(argc, argv);
  
  // rclcpp::executors::MultiThreadedExecutor executor;
  auto executor_ptr = std::make_shared<rclcpp::executors::MultiThreadedExecutor>();
  // Ros node
  auto test_c2_node = std::make_shared<TestC2>();
  // add node
  executor_ptr->add_node(test_c2_node);
  // spin execution
  executor_ptr->spin();
  // Shutdown executor
  rclcpp::shutdown();
  return 0;
}


