/****************************************************************/
// Central Coordination - Fleet manager Node
// Alexandre La Grappe & Emile Le Flecher  - RMA - alexandre.lagrappe@mil.be or emile.leflecher@mil.be 
// 03.12.2024 - V1.0
/****************************************************************/

// Header file:
#include <centralized_coordination/fleet_manager_header.hpp>


// Custom structures
using models::EdgeClient;
using models::Agent;
using models::Task;
using models::Objective;
using models::Primitive;


using std::placeholders::_1;
using std::placeholders::_2;

// Constructor - Destructor
FleetManagerNode::FleetManagerNode() : Node("fleet_manager_node")
{
  this->cb_grp_int_ = this->create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
  this->cb_grp_ext_ = this->create_callback_group(rclcpp::CallbackGroupType::Reentrant);

  this->_ReadConfigurationFile();

  this->initIntraProcessComms_();
  this->_initEdgeInterface();
  this->_init_C2_interface();

  this->_runtime_database.databaseDropConnectedVehicles(); // Start with empty list of connected vehicles


  RCLCPP_INFO(this->get_logger(), "Fleet manager node initialized");
  this->_publishSwarmLog(0,"", "Fleet manager node initialized");
  
  this->timer_ = this->create_wall_timer(500ms, std::bind(&FleetManagerNode::_TimerLoop_callback, this));
  this->timer_edge_connection = this->create_wall_timer(1000ms, std::bind(&FleetManagerNode::_EdgeConnection_timer_callback, this));
  this->timer_collision_avoidance = this->create_wall_timer(1000ms, std::bind(&FleetManagerNode::_HighLevelCollisionAvoidance_timer_callback, this));

}

FleetManagerNode::~FleetManagerNode()
{
}

void FleetManagerNode::_init_C2_interface()
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

void FleetManagerNode::initIntraProcessComms_()
{
  /*********** Get Agents Server ****************/
  this->get_agents_server_ = this->create_service<centralized_msgs::srv::GetAgents>("multi_robot/fleet_manager/get_agents", std::bind(&FleetManagerNode::GetAgents_callback, this, _1, _2), rmw_qos_profile_services_default, this->cb_grp_int_);

  /*********** Send Tasks Server ****************/ //(from mission id or vehicle list, read planning result and call addTask for each vehicle)
  this->_send_tasks_server = this->create_service<c2_msgs::srv::InitMission>("multi_robot/fleet_manager/send_tasks", std::bind(&FleetManagerNode::SendTasks_callback, this, _1, _2), rmw_qos_profile_services_default, this->cb_grp_int_);
  /*********** Change Mission Status Server (to pause/stop all agents on that mission) ****************/
  this->_change_agent_task_status_server = this->create_service<c2_msgs::srv::ChangeMissionStatus>("multi_robot/fleet_manager/change_mission_status", std::bind(&FleetManagerNode::ChangeMissionTaskStatuses_callback, this, _1, _2), rmw_qos_profile_services_default, this->cb_grp_int_);

  /*********** Agent Publisher (for Swarm Planner) ****************/
  this->_agent_publisher = this->create_publisher<centralized_msgs::msg::Agent>("/multi_robot/planner/agent", 10);

    /*********** Agent Task Completed Publisher (for MAMS) ****************/
  // this->_agent_task_completed_publisher = this->create_publisher<std_msgs::msg::String>("/multi_robot/agent_completed_tasks", 10);
}

void FleetManagerNode::_initEdgeInterface()
{
  /*********** Edge Feedback Subscriber ****************/
  this->_edge_feedback_subscriber = this->create_subscription<task_msgs::msg::Feedback>("/multi_robot/edge/feedback", 10, std::bind(&FleetManagerNode::_edge_feedback_subscriber_callback, this, _1));

  /*********** Agent Profile Subscriber ****************/
  this->_agent_profile_subscriber = this->create_subscription<std_msgs::msg::String>("/multi_robot/edge/agent_profile", 10, std::bind(&FleetManagerNode::_agent_profile_subscriber_callback, this, _1));
   
    /*********** Edge connection Publisher ****************/
  this->_edge_connection_check_publisher = this->create_publisher<std_msgs::msg::String>("multi_robot/edge/connection_check", 10);

}

void FleetManagerNode::_ReadConfigurationFile()
{
  // For high level collision avoidance
  declare_parameter<bool>("use_high_level_collision_avoidance", true);
  this->use_high_level_collision_avoidance = get_parameter("use_high_level_collision_avoidance").as_bool();
  declare_parameter<double>("tolerance_distance", 10.0);
  this->tolerance_distance = get_parameter("tolerance_distance").as_double();
  declare_parameter<double>("vicinity_radius", 30.0);
  this->vicinity_radius = get_parameter("vicinity_radius").as_double();
  declare_parameter<double>("max_deceleration_factor", 10.0);
  this->max_deceleration_factor = get_parameter("max_deceleration_factor").as_double();

}


void FleetManagerNode::_HighLevelCollisionAvoidance_timer_callback()
{
  if (!this->use_high_level_collision_avoidance)
  {
    return;
  }
  // For each pair of robots, estimate if a collision might occur
  // std::list<std::pair<Agent, Agent>> pairs;
  // pairs = tools::get_all_pairs(this->_detected_agent_list);
  // for (auto [agent1, agent2] : pairs) {
  //   // Process only pairs where both agents have frame_id == "map"
  //   if (agent1.odometry.header.frame_id != "map" || agent2.odometry.header.frame_id != "map") {
  //       continue;  // Skip this pair and move to the next one
  //   }

  //   agent1.collision_avoidance.is_executing_task = (!agent1.current_task.objectives.empty() && agent1.current_task.status == 1);
  //   agent2.collision_avoidance.is_executing_task = (!agent2.current_task.objectives.empty() && agent2.current_task.status == 1);
  //   // if (agent1.current_task.objectives.empty() || agent2.current_task.objectives.empty() || agent1.current_task.status == 0 || agent2.current_task.status == 0 || relative_distance > this->vicinity_radius || relative_distance < this->tolerance_distance){
  //   if (!agent1.collision_avoidance.is_executing_task && !agent2.collision_avoidance.is_executing_task)
  //   {
  //     continue;
  //   }
  //   double relative_distance = sqrt(pow(agent1.odometry.pose.pose.position.x - agent2.odometry.pose.pose.position.x, 2) + pow(agent1.odometry.pose.pose.position.y - agent2.odometry.pose.pose.position.y, 2))*111000; // 111km =~ 1 deg
  //   // bool agents_approaching =  tools::are_agents_approaching(agent1, agent2);
  //   if (relative_distance < this->vicinity_radius && 
  //       agent1.collision_avoidance.is_executing_task && agent2.collision_avoidance.is_executing_task)
  //   {
  //     std::optional<double> time_to_collision = tools::check_collision(agent1, agent2,  this->tolerance_distance);
  //     if (time_to_collision){
  //       // Reduce the desired speed of one of the agents
  //       RCLCPP_INFO(this->get_logger(), "_HighLevelCollisionAvoidance_timer_callback -> Potential collision! ");

  //       double distance1 = tools::distance_between_poses(agent1.odometry.pose.pose, agent1.current_task.objectives[0].pose);
  //       double distance2 = tools::distance_between_poses(agent2.odometry.pose.pose, agent2.current_task.objectives[0].pose);
  //       Agent decel_agent, other_agent;
  //       // Choose agent to decelerate
  //       decel_agent = (agent1.collision_avoidance.speed_modulated) ? agent1 :
  //             (agent2.collision_avoidance.speed_modulated) ? agent2 :
  //             (distance1 >= distance2) ? agent1 : agent2;

  //       other_agent = (decel_agent.agent_id == agent1.agent_id) ? agent2 : agent1;

  //       // Effectively modulate the agent's speed
  //       Agent* agent = this->getAgent(decel_agent.agent_id);
  //       agent->collision_avoidance.original_speed = (agent->collision_avoidance.speed_modulated) ? 
  //                                            agent->collision_avoidance.original_speed : 
  //                                            agent->current_task.objectives[0].speed;
  //       decel_agent.collision_avoidance.original_speed = agent->collision_avoidance.original_speed;
  //       decel_agent = tools::avoid_collision_in_pair(decel_agent, other_agent, this->tolerance_distance, time_to_collision, max_deceleration_factor);
        
  //       agent->current_task.objectives[0] = decel_agent.current_task.objectives[0];
  //       agent->collision_avoidance.speed_modulated = true;
  //       // agent->collision_avoidance.risks.append(other_agent);
        

  //       RCLCPP_INFO(this->get_logger(), "_HighLevelCollisionAvoidance_timer_callback -> Reduced speed of agent: %s", agent->agent_id.c_str());
  //       this->_publishSwarmLog(1,"", "_HighLevelCollisionAvoidance_timer_callback -> Reducing speed of agent: "+agent->agent_id);

  //       // Send the task update to the slowed agent
  //       this->_sendAgentTask(agent->agent_id);
  //     }
  //     continue;
  //   }

  //   // If there seems to be no danger of collision but one of these agents was slowed down because of the other one in this pair:
  //   // elif(!agents_approaching && agent1.collision_avoidance.speed_modulated && tools::agent_is_in_list(agent2.agent_id, agent1.collision_avoidance.risks))
  //   // RCLCPP_INFO(this->get_logger(), "---------------------------- 13");
  //   if((agent1.collision_avoidance.speed_modulated && agent1.collision_avoidance.is_executing_task) || 
  //           (agent2.collision_avoidance.speed_modulated && agent2.collision_avoidance.is_executing_task))
  //   {
  //     // Accelerate agent 1 until its nominal speed or a speed that is expected to respect the tolerance distance with other agents
  //     Agent accel_agent = (agent1.collision_avoidance.speed_modulated)? agent1 : agent2;
  //     RCLCPP_INFO(this->get_logger(), "_HighLevelCollisionAvoidance_timer_callback -> Accelerating agent %s", accel_agent.agent_id.c_str());
  //     accel_agent = tools::reaccelerate_agent_safely(accel_agent, this->_detected_agent_list,  this->tolerance_distance);
  //     Agent* agent = this->getAgent(accel_agent.agent_id);
  //     agent->current_task.objectives[0] = accel_agent.current_task.objectives[0];
      
  //     // Send the task update to the slowed agent
  //     this->_sendAgentTask(agent->agent_id);

  //     // If the nominal speed is reached again
  //     if (agent->current_task.objectives[0].speed > 0.9*agent->collision_avoidance.original_speed)
  //     {
  //       RCLCPP_INFO(this->get_logger(), "_HighLevelCollisionAvoidance_timer_callback -> Agent back to nominal speed: %s", agent->agent_id.c_str());
  //       agent->collision_avoidance.speed_modulated = false;
  //     }
  //   }
  // }
}   




void FleetManagerNode::_EdgeConnection_timer_callback()
{
  // Publish connection check to edge
  auto msg = std_msgs::msg::String();
  msg.data = "edge connection check";
  this->_edge_connection_check_publisher->publish(msg);

  // Count disconnection time for vehicles that were connected before, according to DB.
  std::vector<std::string> connected_agent_id_list = this->_runtime_database.databaseGetConnectedVehicles();
  for (std::string agent_id : connected_agent_id_list)
  {
    Agent* agent = this->getAgent(agent_id);
    if(agent==nullptr) // Vehicle was not yet registered
    {
      RCLCPP_INFO(this->get_logger(), "_edge_connection_timer_callback -> agent in connected vehicles database but no corresponding structure, creating one for: %s", agent_id.c_str());
      this->_publishSwarmLog(1,"", "_edge_connection_timer_callback -> agent in connected vehicles database but no corresponding structure, creating one for: "+agent_id);
    }
    else 
    {
      agent->edge_client.disconnection_count += 1;
      if (agent->edge_client.disconnection_count > this->_edge_connection_timeout)
      {
        this->_runtime_database.databaseRemoveDisconnectedVehicle(agent_id);
      }
    }
  }
}

void FleetManagerNode::_TimerLoop_callback()
{
  // std::cout << "fleet manager timer loop" << std::endl;
  if (this->_send_tasks_flag)
  {
    this->_sendAllTasksForMission(this->_targeted_mission_id);
    this->_send_tasks_flag = false;
  }

  if (this->_change_agent_task_status_flag)
  {
    this->_changeMissionTaskStatuses(this->_targeted_mission_id, this->_requested_task_status);
    this->_change_agent_task_status_flag = false;
  }
}

/************************************************************/
// Publish Swarm Log (Publisher)                  //
/************************************************************/
void FleetManagerNode::_publishSwarmLog(int log_type, std::string mission_id, std::string log_message)
{
  try
  {
    auto msg = c2_msgs::msg::SwarmLog();
    msg.log_type = log_type;
    msg.log = "[FLEET MANAGER " +mission_id+"]"+log_message;
    if(!mission_id.empty()) msg.mission_id = convertStringUuidtoRosUuid(mission_id);
    this->_swarm_log_publisher->publish(msg);
    // RCLCPP_WARN(this->get_logger(), "LOG PUBLISHED");
  }

  catch (const std::exception &e)
  {
    RCLCPP_ERROR(this->get_logger(), "An error occured during _publishSwarmLog");
  }
}


void FleetManagerNode::_agent_profile_subscriber_callback(const std_msgs::msg::String::SharedPtr msg)
{
  // RCLCPP_INFO(this->get_logger(), "I heard I received Agent Profile data from edge");
  std::string agent_profile_str = msg->data;
  auto agent_profile = this->_json_parser.deserialzeStringToJson(agent_profile_str);
  std::string agent_id = agent_profile["agent_id"];

  if (this->getAgent(agent_id)==nullptr) // Vehicle was not yet registered
  {
    RCLCPP_INFO(this->get_logger(), "_agent_profile_subscriber_callback -> Connected to new agent: %s", agent_id.c_str());
    this->_publishSwarmLog(0,"", "_agent_profile_subscriber_callback -> Connected to new agent: "+agent_id);

    // init edge client
    this->_initAgent(agent_id, agent_profile_str);
  }
  else
  {
    // Update agent_profile in database
    this->_vehicle_database.databaseUpdateVehicle(agent_id, agent_profile_str);
  }

  // Update agent_profile in Agent_list
  Agent* agent = this->getAgent(agent_id);
  agent->agent_profile = agent_profile_str;


  // Add vehicle to connected vehicles list
  this->_runtime_database.databaseAddConnectedVehicle(agent_id); 

  // Set disconnection time back to zero for this agent
  agent->edge_client.disconnection_count = 0;
}


void FleetManagerNode::_edge_feedback_subscriber_callback(const task_msgs::msg::Feedback::SharedPtr msg)
{
  std::string agent_id = msg->agent_id;

  // Update agent information
  Agent* agent = this->getAgent(agent_id);
  if (agent == nullptr)
  {
    return; // Profile of this agent not received yet
  }
  agent->odometry = msg->odometry;
  agent->speed = msg->odometry.twist.twist.linear.x;
  
  
  if (!msg->tasks.empty() && msg->tasks[0].task_state != (uint8_t) 3)
  {
    agent->current_task.status = msg->tasks[0].task_state;
    std::string objective_id = msg->tasks[0].current_objective_id;


    // Remove the previous objectives from the current task
    long unsigned int N = 0;
    for (N = 0; N <= agent->current_task.objectives.size(); N++) {
      if (N == agent->current_task.objectives.size())
      {
        break;
      }

      if (objective_id == agent->current_task.objectives[N].objective_id) {
          break;
      }
    }
    if (N > 0 && N < agent->current_task.objectives.size()) 
    {
      agent->current_task.objectives.erase(agent->current_task.objectives.begin(),agent->current_task.objectives.begin() + N);
    } 
  }
  
  // Publish for Swarm Planner
  this->_agent_publisher->publish(this->toPlannerAgentMsg(agent)); 


}

void FleetManagerNode::_initAgent(std::string agent_id, std::string agent_profile_str)
{
  // Create Agent data structure
  Agent agent;
  agent.agent_id = agent_id;
  agent.agent_profile = agent_profile_str;
  agent.edge_client = this->_createEdgeClient(agent_id);

  this->_detected_agent_list.push_back(agent);
  this->_vehicle_database.databaseUpdateVehicle(agent_id, agent_profile_str);
}

void FleetManagerNode::_recover_agent_task_callback() // re-send task to agent if edge node was restarted
{
 // TODO: when edge initialization is detected (through subscriber), send task if it was running before, starting from the last waypoint
}


EdgeClient FleetManagerNode::_createEdgeClient(std::string agent_id)
{
// Create clients for intra process communication with multi agent mission service nodes

  std::string agent_id_underscores = agent_id;
  std::replace( agent_id_underscores.begin(), agent_id_underscores.end(), '-', '_'); // replace all '-' to '_'

  EdgeClient edge_clients_structure;
  edge_clients_structure.add_task_client = this->create_client<task_msgs::srv::AddTask>("multi_robot/edge/agent_"+agent_id_underscores+"/add_task", rmw_qos_profile_default, this->cb_grp_ext_);
  edge_clients_structure.change_state_client = this->create_client<task_msgs::srv::ChangeState>("multi_robot/edge/agent_"+agent_id_underscores+"/change_state", rmw_qos_profile_default, this->cb_grp_ext_);
  edge_clients_structure.change_task_state_client = this->create_client<task_msgs::srv::ChangeTaskState>("multi_robot/edge/agent_"+agent_id_underscores+"/change_task_state", rmw_qos_profile_default, this->cb_grp_ext_);
  edge_clients_structure.disconnection_count = 0;

  while (!edge_clients_structure.add_task_client->wait_for_service(1s) || !edge_clients_structure.change_state_client->wait_for_service(1s) || !edge_clients_structure.change_task_state_client->wait_for_service(1s))
  {
    if (!rclcpp::ok())
    {
      RCLCPP_ERROR(rclcpp::get_logger("rclcpp"), "_createEdgeClient -> Interrupted while waiting for the Edge services. Exiting. Agent: %s", agent_id.c_str());
      this->_publishSwarmLog(1,"", "_createEdgeClient -> Interrupted while waiting for the Edge services. Exiting. Agent: " + agent_id);

      exit(1);
    }
    RCLCPP_INFO(rclcpp::get_logger("rclcpp"), "_createEdgeClient -> Edge services not available yet, waiting again... agent: %s", agent_id.c_str());
    this->_publishSwarmLog(1,"", "_createEdgeClient -> Edge services not available yet, waiting again... Agent: " + agent_id);
  }

  return edge_clients_structure;
}

Agent* FleetManagerNode::getAgent(const std::string& agent_id) {
    auto agent_it = std::find_if(std::begin(this->_detected_agent_list), std::end(this->_detected_agent_list),
                                [&agent_id](const Agent &a) { return a.agent_id == agent_id; });
    if (agent_it != std::end(this->_detected_agent_list)) {
        return &*agent_it;
    } else {
        RCLCPP_ERROR(this->get_logger(), "getAgent -> AGENT NOT REGISTERED YET: %s", agent_id.c_str());
        return nullptr; 
        // throw std::runtime_error("Agent not found");
    }
}


centralized_msgs::msg::Agent FleetManagerNode::toPlannerAgentMsg(Agent* agent)
{
  // Generate Agent message object from Agent struct
  centralized_msgs::msg::Agent agent_msg;
  
  agent_msg.agent_id = agent->agent_id;
  agent_msg.agent_profile = agent->agent_profile;
  agent_msg.odometry = agent->odometry;

  return agent_msg;
}





void FleetManagerNode::GetAgents_callback(const centralized_msgs::srv::GetAgents::Request::SharedPtr request, centralized_msgs::srv::GetAgents::Response::SharedPtr response)
{
  try
  {
    std::vector<std::string> agent_id_list;
    for(auto agent_uuid : request->agent_id_list) 
    {
      agent_id_list.push_back(convertByteArrayToString(agent_uuid));
    }

    std::vector<centralized_msgs::msg::Agent> agents;
    for (const std::string &agent_id : agent_id_list)
    {
      RCLCPP_INFO(this->get_logger(), "GetAgents_callback -> Collecting agent information from database for: %s", agent_id.c_str());
      this->_publishSwarmLog(0,"", "GetAgents_callback -> Collecting agent information from database for: "+agent_id);

      std::string agent_profile = this->_vehicle_database.databaseFindVehicle(agent_id);

      if (agent_profile == "")
      {
        RCLCPP_ERROR(this->get_logger(), "GetAgents_callback -> AGENT NOT FOUND IN DATABASE: %s", agent_id.c_str());
        this->_publishSwarmLog(1,"", "GetAgents_callback -> AGENT "+agent_id+" NOT FOUND IN DATABASE ");
        response->agents = agents;
        response->error_message = "one of the agents was not found in the vehicle database: "+agent_id;
      }

      Agent* agent = this->getAgent(agent_id);
      if (agent!=nullptr)
      {
        centralized_msgs::msg::Agent agent_msg = this->toPlannerAgentMsg(agent);    
        agents.push_back(agent_msg);
      }
      
    }
    RCLCPP_INFO(this->get_logger(), "GetAgents_callback -> number of agents: %ld",agents.size());

    response->agents = agents;
    response->error_message = "ok";
  }

  catch (const std::exception &e)
  {
    RCLCPP_ERROR(this->get_logger(), "GetAgents_callback -> An error occured during GetAgents_callback");
    this->_publishSwarmLog(2,"", "GetAgents_callback -> An error occured during GetAgents_callback");
  }

}

void FleetManagerNode::SendTasks_callback(const c2_msgs::srv::InitMission::Request::SharedPtr request, c2_msgs::srv::InitMission::Response::SharedPtr response)
{
  try
  {
    RCLCPP_INFO(this->get_logger(), "SendTasks_callback -> Tasks will be sent to agents");
    this->_publishSwarmLog(0,"", "SendTasks_callback -> Tasks will be sent to agents");
    this->_send_tasks_flag = true;
    this->_targeted_mission_id = convertByteArrayToString(request->mission_id);

    response->mission_id = request->mission_id;
    response->mission_feedback = ""; // Does not matter
  }

  catch (const std::exception &e)
  {
    RCLCPP_ERROR(this->get_logger(), "SendTasks_callback -> An error occured during SendTasks_callback, agents will not receive tasks");
    this->_publishSwarmLog(2,"", "SendTasks_callback -> An error occured during SendTasks_callback, agents will not receive tasks");
  }
}


void FleetManagerNode::_setAgentTasksFromPlanning(std::string mission_id) {
    nlohmann::json planning_json = this->_json_parser.deserialzeStringToJson(_runtime_database.databaseFindPlanning(mission_id));
    
    for (const auto& agent_task_json : planning_json["tasks"].items()) {
        std::string agent_id = agent_task_json.key();
        Agent* agent = this->getAgent(agent_id);
        
        if (!agent) {
            RCLCPP_ERROR(this->get_logger(), "_updateAgentTasks -> client was not found for requested agent with id: %s", agent_id.c_str());
            this->_publishSwarmLog(1, "", "_updateAgentTasks -> client was not found for requested agent with id: " + agent_id);
            continue;
        }
        
        RCLCPP_INFO(this->get_logger(), "_updateAgentTasks -> Registering task for agent %s", agent_id.c_str());
        this->_publishSwarmLog(0, mission_id, "_updateAgentTasks -> Registering task for agent " + agent_id);
        
        agent->current_task.task_id = agent_task_json.value()["task_id"].get<std::string>();
        agent->current_task.primitives.clear();
        agent->current_task.objectives.clear();
        
        // Parse primitives
        for (const auto& primitive_json : agent_task_json.value()["primitives"]) {
            Primitive primitive;
            primitive.primitive_id = primitive_json["primitive_id"].get<std::string>();
            primitive.primitive_type = primitive_json["primitive_type"].get<std::string>();
            
            if (primitive_json.contains("parameters")) {
                primitive.parameters = primitive_json["parameters"];
            }
            
            if (primitive_json.contains("primitive_intputs")) {
                primitive.primitive_inputs = primitive_json["primitive_intputs"].get<std::vector<std::string>>();
            }
            
            if (primitive_json.contains("primitive_outputs")) {
                primitive.primitive_outputs = primitive_json["primitive_outputs"].get<std::vector<std::string>>();
            }
            
            auto completion_json = primitive_json["completion"];
            primitive.completion.ends_objective = completion_json["ends_objective"].get<bool>();
            primitive.completion.ends_task = completion_json["ends_task"].get<bool>();
            primitive.completion.followed_by_primitives = completion_json["followed_by_primitives"].get<std::vector<std::string>>();
            primitive.completion.inherit_other_primitives = completion_json["inherit_other_primitives"].get<bool>();
            primitive.completion.resume_after = completion_json["resume_after"].get<bool>();
            
            agent->current_task.primitives.push_back(std::move(primitive));
        }
        
        // Parse objectives
        for (const auto& objective_json : agent_task_json.value()["objectives"]) {
            Objective objective;
            objective.objective_id = objective_json["objective_id"].get<std::string>();
            objective.objective_type = objective_json["objective_type"].get<std::string>();
            objective.parallel_execution = objective_json["parallel_execution"].get<bool>();
            
            for (const auto& primitive_json : objective_json["primitives"]) {
                Primitive primitive;
                primitive.primitive_id = primitive_json["primitive_id"].get<std::string>();
                
                if (primitive_json.contains("parameters")) {
                    primitive.parameters = primitive_json["parameters"];
                }
                
                objective.primitives.push_back(std::move(primitive));
            }
            
            agent->current_task.objectives.push_back(std::move(objective));
        }
    }
}

void FleetManagerNode::_sendAgentTask(std::string agent_id, nlohmann::json agent_task_json)
{
  Agent* agent = this->getAgent(agent_id);
  if(agent==nullptr) // Vehicle was not yet registered
  {
    RCLCPP_ERROR(this->get_logger(), "_sendAgentTask -> client was not found for requested agent with id: %s", agent_id.c_str());
    this->_publishSwarmLog(1,"", "_sendAgentTask -> client was not found for requested agent with id: " + agent_id);
  }
  else
  {
    RCLCPP_INFO(this->get_logger(), "_sendAgentTask -> Sending task to agent %s", agent_id.c_str());
    this->_publishSwarmLog(0, "", "_sendAgentTask -> Sending task to agent " + agent_id);


    auto request = std::make_shared<task_msgs::srv::AddTask::Request>();
    request->task_id = agent->current_task.task_id;
    request->task_type = 0;
    request->override = true;
    request->task_config = agent_task_json.dump();
    // RCLCPP_INFO(this->get_logger(), "task_config json string: %s", request->task_config.c_str());

    using ServiceResponseFuture = rclcpp::Client<task_msgs::srv::AddTask>::SharedFuture;
    auto response_received_callback = [this, agent_id](ServiceResponseFuture future) 
    {
      auto result = future.get();
      RCLCPP_INFO(this->get_logger(), "_sendAgentTask -> agent received task: %s", agent_id.c_str());
      // RCLCPP_INFO(this->get_logger(), "_sendAgentTask -> agent task status was set to %d", result->task_state);
      this->_publishSwarmLog(0,"", "_sendAgentTask -> agent received task, task status was set to " + std::to_string(result->task_state) + " for agent " +agent_id);
    };
    
    auto future_result = agent->edge_client.add_task_client->async_send_request(request, response_received_callback);
  }
  
}

void FleetManagerNode::_sendAllTasksForMission(std::string mission_id)
{
  this->_setAgentTasksFromPlanning(mission_id);

  nlohmann::json planning = this->_json_parser.deserialzeStringToJson(_runtime_database.databaseFindPlanning(mission_id));
  for (const auto& agent_task : planning["tasks"].items())
  {
    std::string agent_id = agent_task.key();
    this->_sendAgentTask(agent_id, agent_task.value());
  }
}

void FleetManagerNode::ChangeMissionTaskStatuses_callback(const c2_msgs::srv::ChangeMissionStatus::Request::SharedPtr request, c2_msgs::srv::ChangeMissionStatus::Response::SharedPtr response)
{
  try
  {
    RCLCPP_INFO(this->get_logger(), "ChangeMissionTaskStatuses_callback -> Individual task statuses will be changed");
    this->_publishSwarmLog(0,"", "ChangeMissionTaskStatuses_callback -> Individual task statuses will be changed");
    this->_change_agent_task_status_flag = true;
    this->_targeted_mission_id = convertByteArrayToString(request->mission_id);
    this->_requested_task_status = request->mission_request_status; // !! it is actually a TASK STATUS, not a mission status ! This message type was used but a new one should be made

    response->mission_id = request->mission_id;
    response->mission_status = this->_requested_task_status; 
    response->error_message = ""; // Does not matter

  }

  catch (const std::exception &e)
  {
    RCLCPP_ERROR(this->get_logger(), "ChangeMissionTaskStatuses_callback -> An error occured during ChangeMissionTaskStatuses_callback");
    this->_publishSwarmLog(2,"", "ChangeMissionTaskStatuses_callback -> An error occured during ChangeMissionTaskStatuses_callback");
  }
}

void FleetManagerNode::_changeMissionTaskStatuses(std::string mission_id, int requested_agent_task_status)
{
    nlohmann::json planning = this->_json_parser.deserialzeStringToJson(_runtime_database.databaseFindPlanning(mission_id));
    for (const auto& agent_task : planning["tasks"].items())
    {
      std::string agent_id = agent_task.key();
      std::string task_id = agent_task.value()["task_id"].get<std::string>();
      this->_changeAgentTaskStatus(agent_id, task_id, requested_agent_task_status);
    }
}

void FleetManagerNode::_changeAgentTaskStatus(std::string agent_id,std::string task_id, int requested_agent_task_status)
{
  Agent* agent = this->getAgent(agent_id);
  if (agent==nullptr) // Vehicle was not yet registered
  {
    RCLCPP_ERROR(this->get_logger(), "_changeAgentTaskStatus -> client was not found for requested agent with id: %s", agent_id.c_str());
    this->_publishSwarmLog(1,"", " _changeAgentTaskStatus ->client was not found for requested agent with id: " + agent_id);
  }
  else
  {
    RCLCPP_INFO(this->get_logger(), "_changeAgentTaskStatus -> Changing task state for agent %s", agent_id.c_str());
    this->_publishSwarmLog(0, "", "_changeAgentTaskStatus -> Changing task state for agent " + agent_id);

    auto request = std::make_shared<task_msgs::srv::ChangeTaskState::Request>();
    request->task_id = task_id;
    request->task_requested_state = requested_agent_task_status;

    using ServiceResponseFuture = rclcpp::Client<task_msgs::srv::ChangeTaskState>::SharedFuture;
    auto response_received_callback = [this, agent_id](ServiceResponseFuture future) 
    {
      auto result = future.get();
      RCLCPP_INFO(this->get_logger(), "_changeMissionTaskStatuses -> agent task status was set to %s", this->_taskStatusToString(result->task_state).c_str());
      this->_publishSwarmLog(0,"", "_changeMissionTaskStatuses -> agent task status was set to: " + std::to_string(result->task_state)+ " for agent " +agent_id);
    };
    
    auto future_result = agent->edge_client.change_task_state_client->async_send_request(request, response_received_callback);
  }
  
}

std::string FleetManagerNode::_taskStatusToString(int task_status)
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

