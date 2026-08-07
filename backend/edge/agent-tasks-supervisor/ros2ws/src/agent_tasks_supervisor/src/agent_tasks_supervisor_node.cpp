/****************************************************************/
// Swarm Edge Module - Edge Node
// Emile Le Flecher & Alexandre La Grappe - RMA - alexandre.lagrappe@mil.be or emile.leflecher@mil.be 
// 21.02.2022 - V1.0.0
/****************************************************************/

// Header File
#include <agent_tasks_supervisor/agent_tasks_supervisor_header.hpp>

using std::placeholders::_1;
using std::placeholders::_2;

// Constructor - Destructor
AgentTaskSupervisorNode::AgentTaskSupervisorNode(std::string node_name) : Node(node_name) , // ROS node
    _current_task("", 0, false) // Initialize with dummy values
{
  // Set configuration parameters
  this->_ReadConfigurationFile();

  // Record agent id
  this->agent_id_underscores = node_name;
  if (node_name.find("agent_") != std::string::npos) {
    node_name.erase(0,6); // remove 'agent_' prefix from node name
  }
  
  std::cout << "Agent ID: " << node_name << std::endl;
  std::replace( node_name.begin(), node_name.end(), '_', '-'); // replace all '_' to '-'
  this->agent_id = node_name;
  
  this->agent_profile["agent_id"] = this->agent_id;

  this->_cb_grp_int = this->create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
  this->cb_grp_ext_ = this->create_callback_group(rclcpp::CallbackGroupType::Reentrant);

  // Initialize Interfaces
  // if(this->_use_unity_simulator) this->_initSimulatorInterface();else 
  this->_initAutonomyInterface();
  this->_initFogInterface();
  this->_initCmdServices();

  // Initialize timers
  this->_objective_control_timer = this->create_wall_timer(500ms, std::bind(&AgentTaskSupervisorNode::_objectiveControl_timer_callback, this)); 
  this->_task_control_timer = this->create_wall_timer(200ms, std::bind(&AgentTaskSupervisorNode::_taskControl_timer_callback, this));
  this->_connection_check_timer = this->create_wall_timer(1000ms, std::bind(&AgentTaskSupervisorNode::_connection_check_timer_callback, this)); 
  this->_wait_timer = this->create_wall_timer(1000ms, std::bind(&AgentTaskSupervisorNode::_wait_timer_callback, this)); 

  // Inform Centralized Coordination about node initialization
  this->_publishNodeInit();
  RCLCPP_INFO(this->get_logger(), "agent_tasks_supervisor_node initialized, waiting for connection with Swarming Fog and Autonomy...");
}

AgentTaskSupervisorNode::~AgentTaskSupervisorNode()
{
}


// Autonomy Interface
void AgentTaskSupervisorNode::_initAutonomyInterface()
{
    /*********** Objective Publisher ****************/
  this->_objective_publisher = this->create_publisher<autonomy_msgs::msg::AutonomySetObjective>(this->AUTONOMY_TOPIC_PREFIX +"/edge/multi_robot/autonomy_set_objective", 10);
  this->_set_objective_timer = this->create_wall_timer(500ms, std::bind(&AgentTaskSupervisorNode::_set_objective_publisher_callback, this));
  this->_speed_control_timer = this->create_wall_timer(500ms, std::bind(&AgentTaskSupervisorNode::_speed_control_timer_callback, this));
  /*********** Localization Subscriber ****************/
  this->_localization_subscriber = this->create_subscription<nav_msgs::msg::Odometry>(this->AUTONOMY_TOPIC_PREFIX +"/edge/multi_robot/localization", 10, std::bind(&AgentTaskSupervisorNode::_localization_subscriber_callback, this, _1));

  /*********** Vehicle Profile Subscriber ****************/
  this->_vehicle_profile_subscriber = this->create_subscription<autonomy_msgs::msg::VehicleProfile>(this->AUTONOMY_TOPIC_PREFIX +"/edge/multi_robot/vehicle_profile", 10, std::bind(&AgentTaskSupervisorNode::_vehicle_profile_subscriber_callback, this, _1));

  /*********** Detected Obstacle Subscriber ****************/
  this->_detected_obstacle_subscriber = this->create_subscription<autonomy_msgs::msg::DetectedObstacle>(this->AUTONOMY_TOPIC_PREFIX +"/edge/multi_robot/detected_obstacle", 10, std::bind(&AgentTaskSupervisorNode::_detected_obstacle_subscriber_callback, this, _1));

  /*********** Swarming Status Subscriber ****************/
  this->_autonomy_status_subscriber = this->create_subscription<autonomy_msgs::msg::AutonomyStatus>(this->AUTONOMY_TOPIC_PREFIX +"/edge/multi_robot/autonomy_status", 10, std::bind(&AgentTaskSupervisorNode::_autonomy_status_subscriber_callback, this, _1));

  /*********** Swarming Trajectory Subscriber ****************/
  this->_autonomy_trajectory_subscriber = this->create_subscription<autonomy_msgs::msg::AutonomyTrajectory>(this->AUTONOMY_TOPIC_PREFIX +"/edge/multi_robot/autonomy_trajectory", 10, std::bind(&AgentTaskSupervisorNode::_autonomy_trajectory_subscriber_callback, this, _1));
}

// Centralized Coordination Interface
void AgentTaskSupervisorNode::_initFogInterface()
{
// Interface with Centralized Coordination (through its edge manager node):
// ---------------------------------------------------------------
    /*********** Node Initialization Publisher ****************/
  this->_node_init_publisher = this->create_publisher<std_msgs::msg::String>("multi_robot/edge/node_init", 10);

    /*********** Feedback Publisher ****************/
  this->_feedback_publisher = this->create_publisher<task_msgs::msg::Feedback>("/multi_robot/edge/feedback", 10);
  this->_feedback_timer = this->create_wall_timer(2000ms, std::bind(&AgentTaskSupervisorNode::_feedback_publisher_callback, this));

    /*********** Agent Profile Publisher ****************/
  this->_agent_profile_publisher = this->create_publisher<std_msgs::msg::String>("/multi_robot/edge/agent_profile", 10);
  this->_agent_profile_timer = this->create_wall_timer(2000ms, std::bind(&AgentTaskSupervisorNode::_agent_profile_publisher_callback, this));

    /***********    Fog Connection Check Subscriber      ****************/
  this->_connection_check_subscriber = this->create_subscription<std_msgs::msg::String>("multi_robot/edge/connection_check", 10, std::bind(&AgentTaskSupervisorNode::_connection_check_subscriber_callback, this, _1));

  /***********    Add Task Server      ****************/
  this->_add_task_server = this->create_service<task_msgs::srv::AddTask>("multi_robot/edge/"+this->agent_id_underscores+"/add_task", std::bind(&AgentTaskSupervisorNode::_addTaskService_callback, this, _1, _2), rmw_qos_profile_services_default, this->_cb_grp_int);
  
  /***********    Change (Agent) State Server - active or inactive****************/
  this->_change_state_server = this->create_service<task_msgs::srv::ChangeState>("multi_robot/edge/"+this->agent_id_underscores+"/change_state", std::bind(&AgentTaskSupervisorNode::_changeStateService_callback, this, _1, _2), rmw_qos_profile_services_default, this->_cb_grp_int);

  /***********    Change Task State Server      ****************/
  this->_change_task_state_server = this->create_service<task_msgs::srv::ChangeTaskState>("multi_robot/edge/"+this->agent_id_underscores+"/change_task_state", std::bind(&AgentTaskSupervisorNode::_changeTaskStateService_callback, this, _1, _2), rmw_qos_profile_services_default, this->_cb_grp_int);  
}

void AgentTaskSupervisorNode::_initCmdServices()
{
  /*********** Trigger Command Server - for development ****************/
  this->cmd_server_ = this->create_service<std_srvs::srv::Trigger>("multi_robot/edge/"+this->agent_id_underscores+"/cmd", std::bind(&AgentTaskSupervisorNode::commandService_callback, this, _1, _2), rmw_qos_profile_services_default, this->_cb_grp_int);
}


// Node initialization publisher
void AgentTaskSupervisorNode::_publishNodeInit()
{
  /*********** Inform Centralized Coordination about node initialization ****************/
  std_msgs::msg::String msg;
  msg.data = this->agent_id;
  this->_node_init_publisher->publish(msg);
}


// Read ROS parameters from config file
void AgentTaskSupervisorNode::_ReadConfigurationFile()
{
  // To activate interface with Unity simulator
  // declare_parameter<bool>("enable_unity_simulator", false);
  // this->_use_unity_simulator = get_parameter("enable_unity_simulator").as_bool();
  // if (this->_use_unity_simulator){RCLCPP_WARN(this->get_logger(), "UNITY SIMULATION SETUP IN USE");}

  declare_parameter<int>("fog_connection_timeout", 5);
  this->_fog_connection_timeout = get_parameter("fog_connection_timeout").as_int();
  RCLCPP_WARN(this->get_logger(), "Fog connection timeout set to [sec]: %d", this->_fog_connection_timeout);

  declare_parameter<int>("autonomy_connection_timeout", 5);
  this->_autonomy_connection_timeout = get_parameter("autonomy_connection_timeout").as_int();
  RCLCPP_WARN(this->get_logger(), "Autonomy connection timeout set to [sec]: %d", this->_autonomy_connection_timeout);

  // Task management parameters
  declare_parameter<bool>("use_start_time", true);
  this->_use_start_time = get_parameter("use_start_time").as_bool();
  if (!this->_use_start_time){RCLCPP_WARN(this->get_logger(), "NOT USING START TIME");}
  
  // Waypoint management parameters
  declare_parameter<int>("waypoint_switching_mode", 1);
  this->_waypoint_switching_mode = get_parameter("waypoint_switching_mode").as_int();
  declare_parameter<double>("objective_distance_tolerance", 3.0);
  this->_objective_distance_tolerance = get_parameter("objective_distance_tolerance").as_double();
  if (this->_waypoint_switching_mode==1)
  {
    RCLCPP_WARN(this->get_logger(), "Using waypoint validation based on objective_distance_tolerance [m]: %f", this->_objective_distance_tolerance);
  }
  if (this->_waypoint_switching_mode==2)
  {
    RCLCPP_WARN(this->get_logger(), "Using autonomy's waypoint validation (for switching to next waypoint)");
  }
  if (this->_waypoint_switching_mode==3)
  {
    RCLCPP_WARN(this->get_logger(), "Using autonomy's waypoint validation for last waypoint, for upstream waypoints based on objective_distance_tolerance [m]: %f", this->_objective_distance_tolerance);
  }

  // Speed control parameters
  declare_parameter<int>("speed_control_mode", 1);
  this->_speed_control_mode = get_parameter("speed_control_mode").as_int();
  RCLCPP_WARN(this->get_logger(), "Speed control mode set to: %d", this->_speed_control_mode);
  
  
  // For testing Fog-less (= edge-only) with pre-defined waypoints
  declare_parameter<bool>("edge_only_testing_mode", false);
  this->_edge_only_testing_mode = get_parameter("edge_only_testing_mode").as_bool();
  if (this->_edge_only_testing_mode)
    {
        RCLCPP_WARN(this->get_logger(), "TESTING MODE WITHOUT FOG");

        // Read test parameters
        declare_parameter<int>("test_mobility_profile", 2);
        this->_mobility_profile = get_parameter("test_mobility_profile").as_int();
        RCLCPP_WARN(this->get_logger(), "Mobility profile: %d", this->_mobility_profile);

        declare_parameter<int>("number_of_WP", 2);
        int number_of_WP = get_parameter("number_of_WP").as_int();
        RCLCPP_WARN(this->get_logger(), "Number of testing waypoints: %d", number_of_WP);

        declare_parameter<std::vector<double>>("speeds", std::vector<double>(number_of_WP, 3.0));
        std::vector<double> speed_list = get_parameter("speeds").as_double_array();

        // Initialize new task
        this->_current_task.task_id = "task_from_config_yaml";
        this->_current_task.task_type = 0;
        this->_current_task.override = true;
        this->_current_task.task_state = 1; // STARTED

        // Read all pre-defined waypoints and construct task
        for (int i = 1; i <= number_of_WP; i++) 
        {
          std::string WP_param_name = "WP" + std::to_string(i);
          declare_parameter(WP_param_name, std::vector<double>{50.258409, 5.389260}); // Default waypoint
          auto WP = get_parameter(WP_param_name).as_double_array();

          if (WP.size() < 2) {
              RCLCPP_ERROR(this->get_logger(), "Waypoint %d is incorrectly defined!", i);
              continue;
          }

          // Generate unique objective ID
          boost::uuids::uuid objective_uuid = boost::uuids::random_generator()();
          std::string objective_id = boost::uuids::to_string(objective_uuid);

          // Create corresponding primitive
          Primitive* primitive = new Primitive(objective_id, "waypoint", {}, {}, {});
          primitive->parameters["coordinates"] = {WP[0], WP[1], 0};
          primitive->parameters["speed"] = (i - 1 < speed_list.size()) ? speed_list[i - 1] : 3.0;

          Objective new_objective(objective_id, true);

          // Create a start GoalNode containing all primitives in this objective
          auto start_node = std::make_unique<GoalNode>("objective_id");
          start_node->addPrimitive(primitive);
        

          // Set the starting goal node
          new_objective.current_goal = start_node.get();
          new_objective.goal_nodes.push_back(std::move(start_node));

          this->_current_task.addObjective(std::move(new_objective));
        }

        // Initialize waypoint navigation

        
        this->_current_task.current_objective_index = 0; // Start with first objective
        this->_task_received = true;
        this->_start_time_passed = true;
        this->_null_objective = false;
    }
    else
    {
        this->_task_received = false; // Task should come from the Fog
        this->_null_objective = true;
    }
}


// Publishers

// To Swarming Fog
void AgentTaskSupervisorNode::_agent_profile_publisher_callback() 
{
  std_msgs::msg::String msg;
  msg.data = this->agent_profile.dump();
  this->_agent_profile_publisher->publish(msg);
}

void AgentTaskSupervisorNode::_feedback_publisher_callback()
{
  task_msgs::msg::Feedback feedback;
  feedback.agent_id = this->agent_id;
  feedback.state = 1;
  
  if(this->_task_received)
  {  
    std::vector<task_msgs::msg::TaskFeedback> tasks;
    task_msgs::msg::TaskFeedback task1;
    task1.task_id = this->_current_task.task_id;
    task1.task_state = this->_current_task.task_state;
    task1.current_objective_id = this->_current_task.objectives[this->_current_task.current_objective_index].id; // this->_objective_id_list[this->_current_task.current_objective_index];
    tasks.push_back(task1);
    feedback.tasks = tasks;
  }
  feedback.odometry = this->_odometry;
  // feedback.speed = this->_current_speed;

  this->_feedback_publisher->publish(feedback);
}

// To Autonomy
void AgentTaskSupervisorNode::_set_objective_publisher_callback()
{ 
    autonomy_msgs::msg::AutonomySetObjective set_objective;
    
    if (!this->_null_objective && !this->_waiting_here) // If there is a registered task
    {
        Objective& current_objective = this->_current_task.objectives[this->_current_task.current_objective_index];
        GoalNode* current_goal = current_objective.current_goal;


        autonomy_msgs::msg::AutonomyObjective objective;
        unique_identifier_msgs::msg::UUID objective_uuid = convertStringUuidtoRosUuid(current_objective.id);
        objective.id = objective_uuid;
        objective.max_speed = this->_required_speed; 
        objective.mobility_profile = this->_mobility_profile;

        

        objective.parallel_execution = current_objective.parallel_execution;

        // Encode primitives into JSON strings
        std::vector<std::string> json_primitives_list;
        for (const auto& [primitive_id, primitive] : current_goal->primitives) {
            nlohmann::json primitive_json;
            primitive_json["id"] = primitive->id;
            primitive_json["type"] = primitive->type;
            primitive_json["continuous"] = primitive->continuous;
            primitive_json["primitive_inputs"] = primitive->primitive_inputs;
            primitive_json["primitive_outputs"] = primitive->primitive_outputs;
            primitive_json["parameters"] = primitive->parameters;
            
            json_primitives_list.push_back(primitive_json.dump()); // Convert JSON to string
        }

        objective.primitives = json_primitives_list; // Assign JSON-encoded primitive list
        set_objective.objective = objective;
        set_objective.null_objective = false;

        // RCLCPP_INFO(this->get_logger(), "Objective: %s", objective.id.c_str());
        // RCLCPP_INFO(this->get_logger(), "Objective Speed: %f", objective.max_speed);
    }
    else
    {
        set_objective.null_objective = true;
    }

    this->_objective_publisher->publish(set_objective);
}




// Timer Callbacks
void AgentTaskSupervisorNode::_taskControl_timer_callback()
{
  if(this->_task_received)
  {    
    // Start time passed flag
    if(this->_use_start_time && !this->_start_time_passed && difftime(this->_current_task_std, std::chrono::system_clock::to_time_t(std::chrono::system_clock::now())) <= 0) 
    {
      this->_start_time_passed = true;
      RCLCPP_WARN(this->get_logger(), "START TIME PASSED");
    }

    if (this->_connected_to_autonomy && (this->_connected_to_fog || this->_edge_only_testing_mode ) && this->_current_task.task_state == 1 && this->_start_time_passed)
    {
      this->_null_objective = false;
    }
    else // all task states different from 1 imply null_objective
    {
      this->_null_objective = true;
    }
  }
  else
  {
    this->_null_objective = true;
  }
}

void AgentTaskSupervisorNode::_objectiveControl_timer_callback()
{
  if (this->_current_task.objectives.empty() || this->_null_objective) {
      RCLCPP_WARN(this->get_logger(), "No objectives to process.");
      return;
  }
  

  Objective& current_objective = this->_current_task.objectives[this->_current_task.current_objective_index];
  
  GoalNode* current_goal = current_objective.current_goal;

  if (!current_goal) {
      RCLCPP_WARN(this->get_logger(), "No active goal for the current objective.");
      return;
  }
  
  bool is_last_objective = (this->_current_task.current_objective_index == this->_current_task.objectives.size() - 1);


  // Check if all (non-continuous) primitives in the current goal are completed
  bool goal_completed = std::all_of(
      current_goal->primitives.begin(),
      current_goal->primitives.end(),
      [this, is_last_objective](const auto& pair) { 
          Primitive* p = pair.second;  
          return (this->_check_if_primitive_completed(p, is_last_objective) && p->completion.followed_by_primitives.empty()) || p->continuous;
      }
  );

  if (goal_completed) {
    // Traverse up the parent chain to find a resumable parent
    GoalNode* parent = current_goal->parent;
    while (parent) {
        // If primitive that led to current_goal needs to be resumed
        bool resume_origin_primitive = current_goal->origin_primitive && current_goal->origin_primitive->completion.resume_after;
        // If other (non-continuous) primitives in parent were not done
        bool parent_has_incomplete_non_continuous = std::any_of(parent->primitives.begin(), parent->primitives.end(),
              [](const auto& pair) { return !pair.second->continuous && pair.second->status != autonomy_msgs::msg::AutonomyPrimitiveStatus::COMPLETED; });
        
        if (resume_origin_primitive || parent_has_incomplete_non_continuous) {
            RCLCPP_INFO(this->get_logger(), "Resuming parent goal: %s", parent->id.c_str());
            current_goal = parent;
            return;
        }
        parent = parent->parent; // Move up the tree
    }
    // If no parent to resume, switch to the next objective
    this->_switch_to_next_objective();
    return;
  }
  else // Goal not (fully) completed
  {
    for (auto& [primitive_id, primitive] : current_goal->primitives) {
      bool primitive_completed = this->_check_if_primitive_completed(primitive, is_last_objective);

      // If one of the primitives is completed and has children
      if (primitive_completed && !primitive->completion.followed_by_primitives.empty()) 
      {
        auto new_goal = std::make_unique<GoalNode>("goal_" + primitive_id, primitive); // Store origin primitive
        // Add the primitives
        for (const std::string& next_primitive_id : primitive->completion.followed_by_primitives) {
            if (this->_current_task.primitive_map.find(next_primitive_id) == this->_current_task.primitive_map.end()) {
                RCLCPP_ERROR(this->get_logger(), "Primitive ID %s not found in task!", next_primitive_id.c_str());
                continue;
            }

            Primitive* next_primitive = this->_current_task.primitive_map[next_primitive_id];
            new_goal->addPrimitive(next_primitive);
        }

        // Add the new goal node as a child of the current goal
        current_goal->addChild(std::move(new_goal));

        // Transition to the child node
        current_goal = current_goal->children.front().get();
        return;

      }
    }
  }
}

bool AgentTaskSupervisorNode::_check_if_primitive_completed(Primitive* prim, bool is_last_objective)
{
  bool primitive_completed = prim->status == autonomy_msgs::msg::AutonomyPrimitiveStatus::COMPLETED;
  if (!primitive_completed && prim->type == "waypoint") 
  { 
    // Check if parsing valid
    bool valid_waypoint = prim->parameters.contains("coordinates") && prim->parameters["coordinates"].is_array() && prim->parameters["coordinates"].size() >= 2;
    if(!valid_waypoint)
    {
      return primitive_completed;
    }
    // If it is a waypoint, check if it is close enough
    if (this->_odometry.header.frame_id == "map") 
    {
      float obj_lat = prim->parameters["coordinates"][1]; // Latitude
      float obj_long = prim->parameters["coordinates"][0]; // Longitude
      this->_distance_to_objective = distance_lat_lon_to_meters(obj_lat, obj_long, 
                                                                  this->_odometry.pose.pose.position.y, 
                                                                  this->_odometry.pose.pose.position.x);
    }
    else { // Local coordinates
        float obj_x = prim->parameters["coordinates"][0];
        float obj_y = prim->parameters["coordinates"][1];
        float dx = obj_x - this->_odometry.pose.pose.position.x;
        float dy = obj_y - this->_odometry.pose.pose.position.y;
        this->_distance_to_objective = std::sqrt(dx * dx + dy * dy); // Euclidean distance
    }

    RCLCPP_INFO(this->get_logger(), "Distance to waypoint: %f", this->_distance_to_objective);    

    switch (this->_waypoint_switching_mode)
    {
        case 1: // Based on objective_distance_tolerance 
            primitive_completed = (this->_distance_to_objective <= this->_objective_distance_tolerance);
            break;
        case 2: // Based on autonomy's "autonomy_status" message
            primitive_completed = this->_autonomy_objective_finished;
            break;
        case 3: // Based on both modes 1 and 2, with AND condition
            primitive_completed = (this->_autonomy_objective_finished && (this->_distance_to_objective <= this->_objective_distance_tolerance));
            break;
        case 4: // Based on objective_distance_tolerance, but for last waypoint use autonomy's "autonomy_status" message
            if (is_last_objective) {
                primitive_completed = this->_autonomy_objective_finished;
            } else {
                primitive_completed = (this->_distance_to_objective <= this->_objective_distance_tolerance);
            }
            break;
    }
    // Force primitive status to be completed
    if (primitive_completed){prim->status = autonomy_msgs::msg::AutonomyPrimitiveStatus::COMPLETED;};
  }
  return primitive_completed;
}
void AgentTaskSupervisorNode::_switch_to_next_objective()
{
  bool is_last_objective = (this->_current_task.current_objective_index == this->_current_task.objectives.size() - 1);
  if (!is_last_objective)
  {
      // Move to the next objective
    RCLCPP_INFO(this->get_logger(), "Going to the next objective");
    this->_current_task.current_objective_index++;
    this->_autonomy_objective_finished = false; // Reset flag

    this->_sum_of_previous_speeds = 0;
    this->_count_of_previous_speeds = 0;

  }
  else
  {
    this->_task_completed();
  }
}

void AgentTaskSupervisorNode::_task_completed()
{
  RCLCPP_WARN(this->get_logger(), "TASK COMPLETED");
  this->_current_task.task_state = 3; // COMPLETED
  // this->_task_received = false;
  this->_autonomy_objective_finished = false; // Reset flag

}
void AgentTaskSupervisorNode::_speed_control_timer_callback()
{ 
  if (this->_current_task.objectives.empty() || this->_null_objective) {
      return;
  }
  // Speed control for waypoint primitives
  //--------------------------------------
  Objective& current_objective = this->_current_task.objectives[this->_current_task.current_objective_index];
  GoalNode* current_goal = current_objective.current_goal;

  for (const auto& [primitive_id, current_primitive] : current_goal->primitives) if (current_primitive->status != autonomy_msgs::msg::AutonomyPrimitiveStatus::COMPLETED && current_primitive->type=="waypoint")
  {
    
    this->_target_average_speed = current_primitive->parameters["speed"]; // this->_current_task.objectives[this->_current_task.current_objective_index].speed;
    
    switch (this->_speed_control_mode)
    {
      case 0: // * Unbound - Based on given speed value (in task)
        this->_required_speed = this->_target_average_speed;
        break;
      case 1: // * Based on given speed value (in task)
        this->_required_speed = (this->_target_average_speed <= this->_max_speed_limit) ? this->_target_average_speed : this->_max_speed_limit;
        break;
      case 2: // * Based on given speed value (in task), as an average value (try to keep average speed +- constant between two waypoints)
              //   used speed formula: V_(N+1) = V_target*(N+2) - SUM i=0...N (V_i)  where V_i is the i'th speed registered since the beginning of this objective and V_target is the average speed to be reached for this objective
        this->_required_speed = this->_target_average_speed*(this->_count_of_previous_speeds + 1) - this-> _sum_of_previous_speeds; //this->_target_average_speed*(static_cast<int>(this->previous_speeds_list.size()) +1)  - std::accumulate(this->previous_speeds_list.begin(), this->previous_speeds_list.end(), 0.0f);
        break;
      // case 3: // * Based on given ETA (in task)
      //   time_t eta = Isotime::FromIso8601(current_primitive->parameters["eta"]) + 60*60;
      //   time_t current_time = std::chrono::system_clock::to_time_t(std::chrono::system_clock::now());
      //   RCLCPP_INFO(this->get_logger(), "ETA: %s", Isotime::ToIso8601(eta).c_str());
      //   RCLCPP_INFO(this->get_logger(), "NOW: %s", Isotime::ToIso8601(current_time).c_str());
      //   this->_remaining_time_to_objective = difftime(eta, current_time);
      //   RCLCPP_WARN(this->get_logger(), "REMAINING TIME: %f", this->_remaining_time_to_objective);
      //   if (this->_remaining_time_to_objective > 0)
      //   {
      //     this->_required_speed = this->_distance_to_objective/this->_remaining_time_to_objective; // speed = distance/remaining time
      //     if (this->_required_speed > this->_max_speed_limit) // never exceed max speed limit
      //     {
      //       this->_required_speed =  this->_max_speed_limit; 
      //     }
      //   }
      //   else // if time is already over, go as fast as possible
      //   {
      //     this->_required_speed =  this->_max_speed_limit; 
      //   }
      //   break;
    }   
  } 
  
}


void AgentTaskSupervisorNode::_connection_check_timer_callback()
{
  if (!this->_edge_only_testing_mode)
  {
    this->_fog_connection_check_counter +=1;
    if(this->_connected_to_fog && this->_fog_connection_check_counter > this->_fog_connection_timeout)
    {
      this->_connected_to_fog = false;
      RCLCPP_WARN(this->get_logger(), "Disconnected from the Fog (Centralized Coordination)");
    }
  }

  this->_autonomy_connection_check_counter +=1;
  if(this->_connected_to_autonomy && this->_autonomy_connection_check_counter > this->_autonomy_connection_timeout)
  {
    this->_connected_to_autonomy = false;
    RCLCPP_WARN(this->get_logger(), "Disconnected from Autonomy");
  }
}

void AgentTaskSupervisorNode::_wait_timer_callback()
{
  if (this->_waiting_here && this->_wait_time_clock >=0)
  {
    this->_wait_time_clock -= 1;
  }
}


// Subscriber Callbacks

void AgentTaskSupervisorNode::_localization_subscriber_callback(const nav_msgs::msg::Odometry::SharedPtr msg)
{
  this->_set_connected_to_autonomy();
  this->_odometry = *msg;

  this-> _sum_of_previous_speeds += this->_current_speed; // To compute the required_speed
  this->_count_of_previous_speeds += 1;
}


void AgentTaskSupervisorNode::_connection_check_subscriber_callback(const std_msgs::msg::String::SharedPtr msg)
{
  std::string connection_msg = msg->data;
  if (!this->_connected_to_fog){RCLCPP_WARN(this->get_logger(), "Connected to the Fog (Centralized Coordination)");}
  
  this->_connected_to_fog = true;
  this->_fog_connection_check_counter = 0;
}

void AgentTaskSupervisorNode::_detected_obstacle_subscriber_callback(const autonomy_msgs::msg::DetectedObstacle::SharedPtr msg)
{
  this->_set_connected_to_autonomy();

  unique_identifier_msgs::msg::UUID obstacle_id = msg->obstacle_id;
  std::string obstacle_geofence = msg->obstacle_geofence;
  RCLCPP_INFO(this->get_logger(), "Obstacle geofence received from autonomy: %s", obstacle_geofence.c_str());
}

void AgentTaskSupervisorNode::_autonomy_status_subscriber_callback(const autonomy_msgs::msg::AutonomyStatus::SharedPtr msg)
{
  this->_set_connected_to_autonomy();

  unique_identifier_msgs::msg::UUID autonomy_objective_id = msg->autonomy_objective_id;
  int status = msg->status;
  
  // Check if the entire objective is considered completed
  this->_autonomy_objective_finished = (status == autonomy_msgs::msg::AutonomyStatus::COMPLETED);
  
  // Iterate over all primitive statuses
  for (const auto& primitive_status : msg->primitive_statuses)
  {
    auto primitive_id = convertRosUuidtoStringUuid(primitive_status.primitive_id);
    auto primitive_it = this->_current_task.primitive_map.find(primitive_id);
                  
    if (primitive_it != this->_current_task.primitive_map.end())
    {
      Primitive* primitive = primitive_it->second;
      primitive->status = primitive_status.status;
    }
  }
}


void AgentTaskSupervisorNode::_autonomy_trajectory_subscriber_callback(const autonomy_msgs::msg::AutonomyTrajectory::SharedPtr msg)
{

  this->_set_connected_to_autonomy();

  unique_identifier_msgs::msg::UUID autonomy_objective_id = msg->autonomy_objective_id;
  std::string trajectory = msg->trajectory;
}

void AgentTaskSupervisorNode::_vehicle_profile_subscriber_callback(const autonomy_msgs::msg::VehicleProfile::SharedPtr msg)
{
  this->_set_connected_to_autonomy();
  autonomy_msgs::msg::VehicleConstraints vehicle_constraints_msg = msg->vehicle_constraints;
  autonomy_msgs::msg::VehicleInfo vehicle_info_msg = msg->vehicle_info;

  nlohmann::json vehicle_constraints = {
  {"max_speed", {
    {"linear", {
      {"x", vehicle_constraints_msg.max_speed.linear.x},
      {"y", vehicle_constraints_msg.max_speed.linear.y},
      {"z", vehicle_constraints_msg.max_speed.linear.z}
    }
    },
    {"angular", {
      {"x", vehicle_constraints_msg.max_speed.angular.x},
      {"y", vehicle_constraints_msg.max_speed.angular.y},
      {"z", vehicle_constraints_msg.max_speed.angular.z}
      }
    }
    }
  },
  {"max_acceleration", {
    {"linear", {
      {"x", vehicle_constraints_msg.max_acceleration.linear.x},
      {"y", vehicle_constraints_msg.max_acceleration.linear.y},
      {"z", vehicle_constraints_msg.max_acceleration.linear.z}
    }
    },
    {"angular", {
      {"x", vehicle_constraints_msg.max_acceleration.angular.x},
      {"y", vehicle_constraints_msg.max_acceleration.angular.y},
      {"z", vehicle_constraints_msg.max_acceleration.angular.z}
      }
    }
    }
  },
  {"max_weight", 3.141},
  {"max_tilt_angle", 3.141}
  };

  nlohmann::json vehicle_info = {
  {"fuel_status_pct", vehicle_info_msg.fuel_status_pct},
  {"fuel_hours", vehicle_info_msg.fuel_hours},
  {"battery_status_pct", vehicle_info_msg.battery_status_pct},
  {"battery_hours", vehicle_info_msg.battery_hours},
  {"vehicle_dimensions", {
    {"length", vehicle_info_msg.vehicle_dimensions[0]},
    {"width", vehicle_info_msg.vehicle_dimensions[1]},
    {"height", vehicle_info_msg.vehicle_dimensions[2]}
    }
  }
  };

  auto sensor_list = nlohmann::json::array();
  for (autonomy_msgs::msg::SensorProperties sensor_msg : vehicle_info_msg.sensor_list)
  {
    nlohmann::json sensor = {
      {"type", sensor_msg.type},
      {"status", sensor_msg.status},
      {"field_of_view", {
        {"r", sensor_msg.field_of_view[0]},
        {"theta", sensor_msg.field_of_view[1]}
      }
      }
    };
    sensor_list.push_back(sensor);
  }
  vehicle_info["sensor_list"] = sensor_list;

  this->agent_profile["vehicle_constraints"] = vehicle_constraints;
  this->agent_profile["vehicle_info"] = vehicle_info;

  this->_max_speed_limit = 5;
  this->agent_profile["vehicle_constraints"]["max_speed"]["linear"]["x"];

}
    
// Service Callbacks

void AgentTaskSupervisorNode::commandService_callback(const std_srvs::srv::Trigger::Request::SharedPtr request, std_srvs::srv::Trigger::Response::SharedPtr response)
{
  if (request)
    {
      response->success = true;
      response->message = "Trigger was heard";
    }
}

void AgentTaskSupervisorNode::_addTaskService_callback(
    const task_msgs::srv::AddTask::Request::SharedPtr request, 
    task_msgs::srv::AddTask::Response::SharedPtr response)
{
    RCLCPP_WARN(this->get_logger(), "----- Received a new task : %s", request->task_config.c_str());

    // Clear previous task data
    this->_current_task.objectives.clear();
    this->_current_task.primitive_map.clear();
    this->_current_task.current_objective_index = 0;
    
    // Check if updating the same task
    if (this->_current_task.task_id == request->task_id) {
        RCLCPP_WARN(this->get_logger(), "! Updating task, maintaining previous task state");
    } else {
        this->_current_task.task_state = 0; // STOPPED
    }

    // Initialize task metadata
    this->_current_task.task_id = request->task_id;
    this->_current_task.task_type = request->task_type;
    this->_current_task.override = request->override;
    
    nlohmann::json task_config_json = nlohmann::json::parse(request->task_config);

    // Create new Task instance
    Task new_task(request->task_id, request->task_type, request->override);

    // Parse primitives and store them in a lookup map
    std::unordered_map<std::string, Primitive*> primitive_lookup;
    for (const auto& primitive_json : task_config_json["primitives"]) {
        std::string primitive_id = primitive_json["primitive_id"];
        std::string primitive_type = primitive_json["primitive_type"];
        nlohmann::json parameters = primitive_json.value("parameters", nlohmann::json{});

        std::vector<std::string> inputs, outputs;
        if (primitive_json.contains("primitive_inputs")) {
            for (const auto& input : primitive_json["primitive_inputs"]) {
                inputs.push_back(input.get<std::string>());
            }
        }
        if (primitive_json.contains("primitive_outputs")) {
            for (const auto& output : primitive_json["primitive_outputs"]) {
                outputs.push_back(output.get<std::string>());
            }
        }

        bool ends_objective = false;
        bool ends_task = false;
        std::vector<std::string> followed_by_primitives;

        if (primitive_json.contains("completion") && primitive_json["completion"].is_object()) 
        {
            if (primitive_json["completion"].contains("ends_objective") && !primitive_json["completion"]["ends_objective"].is_null()) 
            {
                ends_objective = primitive_json["completion"]["ends_objective"].get<bool>();
            }
            if (primitive_json["completion"].contains("ends_task") && !primitive_json["completion"]["ends_task"].is_null()) 
            {
                ends_task = primitive_json["completion"]["ends_task"].get<bool>();
            }
            if (primitive_json["completion"].contains("followed_by_primitives") && primitive_json["completion"]["followed_by_primitives"].is_array()) 
            {
                for (const auto& item : primitive_json["completion"]["followed_by_primitives"])
                {
                    followed_by_primitives.push_back(item.get<std::string>());
                }
            }
        }

        // Now pass the values safely
        Primitive* new_primitive = new Primitive(
          primitive_id,            // std::string
          primitive_type,          // std::string
          false,                   // _continuous (default: false)
          parameters,              // nlohmann::json
          inputs,                  // std::vector<std::string>
          outputs,                 // std::vector<std::string>
          ends_objective,          // bool
          ends_task,               // bool
          followed_by_primitives,  // std::vector<std::string>
          false,                   // _inherit_other_primitives (default: false)
          true                    // _resume_after (default: false)
      );


        primitive_lookup[primitive_id] = new_primitive;
        new_task.registerPrimitive(new_primitive);
    }

    // Parse objectives and add all primitives to the start node
    for (const auto& objective_json : task_config_json["objectives"]) {
        std::string objective_id = objective_json["objective_id"];
        bool parallel_execution = objective_json["parallel_execution"];

        Objective new_objective(objective_id, parallel_execution);

        // Create a start GoalNode containing all primitives in this objective
        auto start_node = std::make_unique<GoalNode>("start");

        for (const auto& primitive_entry : objective_json["primitives"]) {
            std::string primitive_id = primitive_entry["primitive_id"];
            
            if (primitive_lookup.find(primitive_id) != primitive_lookup.end()) {
                Primitive* primitive = primitive_lookup[primitive_id];
                Primitive* cloned_primitive = new Primitive(*primitive);


                // Override primitive parameters if specified in the objective
                if (primitive_entry.contains("parameters")) {
                    cloned_primitive->parameters = primitive_entry["parameters"];
                }

                start_node->addPrimitive(cloned_primitive);
            } else {
                RCLCPP_ERROR(this->get_logger(), "Primitive ID %s not found in primitives!", primitive_id.c_str());
            }
        }

        // Set the starting goal node
        new_objective.current_goal = start_node.get();
        new_objective.goal_nodes.push_back(std::move(start_node));

        new_task.addObjective(std::move(new_objective));
    }

    // Assign new task
    this->_current_task = std::move(new_task);
    this->_task_received = true;
    this->_start_time_passed = !this->_use_start_time;

    response->task_id = this->_current_task.task_id;
    response->task_state = 0; // Pending
    RCLCPP_WARN(this->get_logger(), "----------------------------------    26 ");
}



// void AgentTaskSupervisorNode::_addTaskService_callback(const task_msgs::srv::AddTask::Request::SharedPtr request, task_msgs::srv::AddTask::Response::SharedPtr response)
// {
//   RCLCPP_WARN(this->get_logger(), "----- Received a new task : %s", request->task_id.c_str());
//   // RCLCPP_WARN(this->get_logger(), "content : %s", request->task_config.c_str());
//   this->_current_task.waypoints.clear();
//   this->_objective_id_list.clear();
//   this->_current_objective_index = 0; // start with first objective
//   this->_sum_of_previous_speeds = 0 ;
//   this->_count_of_previous_speeds = 0;

//   if (this->_current_task.task_id == request->task_id.c_str())
//   {
//     RCLCPP_WARN(this->get_logger(), "! Updating task, maintaining previous task state");
//   }
//   else
//   {
//     this->_current_task.task_state = 0 ; //STOPPED
//   }
//   this->_current_task.task_id = request->task_id.c_str();
//   this->_current_task.task_type = request->task_type;
//   this->_current_task.override = request->override;
  
//   this->_current_task_std = Isotime::FromIso8601(request->std) + 60*60 ; //START TIME

  

//   nlohmann::json task_config_json = nlohmann::json::parse(request->task_config);
  

//   for (const auto& waypoint_json : task_config_json.items()) // repopulate _objective_id_list
//   {
//     WayPoint wp;
//     wp.position[0] = waypoint_json.value()["position"][0].get<float>();
//     wp.position[1] = waypoint_json.value()["position"][1].get<float>();
//     wp.speed = waypoint_json.value()["speed"].get<float>();
//     wp.objective_id = waypoint_json.value()["waypoint_id"].get<std::string>();

//     if (waypoint_json.value().contains("wait_time"))
//     {
//       wp.wait_time = waypoint_json.value()["wait_time"].get<float>();
//     }
    
//     this->_current_task.waypoints.push_back(wp);
//     this->_objective_id_list.push_back(waypoint_json.value()["waypoint_id"].get<std::string>());
//   }
//   this->_current_objective_id = this->_objective_id_list[this->_current_objective_index]; 
//   this->_target_average_speed = this->_current_task.waypoints[this->_current_objective_index].speed;
  

//   this->_task_received = true;
//   this->_start_time_passed = !this->_use_start_time; // false if we use the given start time
//   // this->_null_objective = true;
  
//   response->task_id = this->_current_task.task_id;
//   response->task_state = 0;

//     // enum class TaskType
//     // {
//     //     DRIVE = 0,                     // waypoint drive task
//     //     EXAMPLE_PERIPHERAL_CAMERA = 1, // move camera task (example)
//     //     EXAMPLE_DEFENSE_SHIELDS = 2,   // move camera task (example)
//     // };

//     //     enum class TaskState
//     // {
//     //     STOPPED = 0,   // stopped, but not completed or started
//     //     STARTED = 1,   // started
//     //     PAUSED = 2,    // paused
//     //     COMPLETED = 3, // completed the task
//     //     ABORTED = 4,   // aborted
//     //     DELETED = 5    // deleted
//     // };
// }

// TODO: remove or find usefullness of this
void AgentTaskSupervisorNode::_changeStateService_callback(const task_msgs::srv::ChangeState::Request::SharedPtr request, task_msgs::srv::ChangeState::Response::SharedPtr response)
{
  RCLCPP_WARN(this->get_logger(), "----AGENT STATE CHANGED TO %d", request->requested_state);
  this->agent_state = request->requested_state;

  response->state = 1;
  response->feedback = "ok";

    // enum class State
    // {
    //     INACTIVE = 0, // inactive
    //     ACTIVE = 1    // active
    // };
}

void AgentTaskSupervisorNode::_changeTaskStateService_callback(const task_msgs::srv::ChangeTaskState::Request::SharedPtr request, task_msgs::srv::ChangeTaskState::Response::SharedPtr response)
{
  RCLCPP_WARN(this->get_logger(), "---- TASK STATE SET TO ------ %s", this->_taskStatusToString(request->task_requested_state).c_str());
  this->_current_task.task_state = request->task_requested_state ;

  response->task_id = this->_current_task.task_id;
  response->task_state = this->_current_task.task_state;
  response->feedback = "ok";
}

// Setters
void AgentTaskSupervisorNode::_set_connected_to_autonomy()
{
  if (this->_connected_to_autonomy == false){RCLCPP_WARN(this->get_logger(), "Connected to Autonomy");}
  
  this->_connected_to_autonomy = true;
  this->_autonomy_connection_check_counter = 0;
}

// Helpers
std::string AgentTaskSupervisorNode::_taskStatusToString(int task_status)
{
   // enum class TaskRequestState
    // {
    //     STOP = 0,    // request to stop the task & re-init
    //     EXECUTE = 1, // request to execute the task
    //     PAUSE = 2,   // request to pause the task
    //     DELETE = 3   // request to delete the task
    // };
  switch (task_status)
  {
  case 0:
    return "STOP";
  case 1:
    return "EXECUTE";
  case 2:
    return "PAUSE";
  case 3:
    return "DELETE";
  }
}


int main(int argc, char ** argv)
{
  std::string node_name = argv[1];
  std::replace( node_name.begin(), node_name.end(), '-', '_'); // replace all '-' to '_'
  std::transform(node_name.begin(), node_name.end(), node_name.begin(),
    [](unsigned char c){ return std::tolower(c); }); // transform every letter to lowercase
  std::cout << "Node name will be: " << node_name << std::endl;
  rclcpp::init(argc, argv);

  
  auto executor_ptr = std::make_shared<rclcpp::executors::MultiThreadedExecutor>();

  // Ros nodes
  auto agent_tasks_supervisor_node = std::make_shared<AgentTaskSupervisorNode>(node_name);

  // Add nodes
  executor_ptr->add_node(agent_tasks_supervisor_node);  

  // spin execution
  executor_ptr->spin();
  // Shutdown executor
  rclcpp::shutdown();
  return 0;
}
