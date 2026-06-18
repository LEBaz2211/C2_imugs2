/****************************************************************/
/*    Code to test custom message which are sent from SwarmPlanner        */
/*    Emile Le Flecher - RMA - 24.02.2022                       */
/****************************************************************/
# include <centralized_coordination/test/test_planner.hpp>

SwarmPlanner::SwarmPlanner(/* args */) : Node("test_swarm_planner_node")
{
  
  this->_SwarmPlanner_callback_group_ptr = this->create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
  this->_initPlannerServices();
  RCLCPP_INFO(this->get_logger(), "test_swarm_planner_node init done");
}

/****************************************************************/

SwarmPlanner::~SwarmPlanner()
{
}

/****************************************************************/

void SwarmPlanner::_initPlannerServices()
{
  this->create_planner_server_ = this->create_service<centralized_msgs::srv::CreatePlanner>("/swarm/planner/create", std::bind(&SwarmPlanner::createPlanner_callback, this, _1, _2), rmw_qos_profile_services_default, this->_SwarmPlanner_callback_group_ptr);
  this->delete_planner_server_ = this->create_service<centralized_msgs::srv::DeletePlanner>("/swarm/planner/delete", std::bind(&SwarmPlanner::deletePlanner_callback, this, _1, _2), rmw_qos_profile_services_default, this->_SwarmPlanner_callback_group_ptr);

  this->get_plan_server_ = this->create_service<centralized_msgs::srv::GetPlan>("/swarm/planner/get_plan", std::bind(&SwarmPlanner::GetPlan_callback, this, _1, _2), rmw_qos_profile_services_default, this->_SwarmPlanner_callback_group_ptr);

  this->update_planner_agents_server_ = this->create_service<centralized_msgs::srv::UpdatePlannerAgents>("/swarm/planner/set_agents", std::bind(&SwarmPlanner::updatePlannerAgents_callback, this, _1, _2), rmw_qos_profile_services_default, this->_SwarmPlanner_callback_group_ptr);
}

void SwarmPlanner::createPlanner_callback(const centralized_msgs::srv::CreatePlanner::Request::SharedPtr request, centralized_msgs::srv::CreatePlanner::Response::SharedPtr response)
{
  RCLCPP_INFO(this->get_logger(), "Planner created");
  std::string mission_id = request->id;
  std::string mission_config_str = request->config;
  this->_planner_agents = request->agents;
  RCLCPP_INFO(this->get_logger(), "I heard that I should create a planner for this many agents: %ld",this->_planner_agents.size());


  response->id = mission_id;
  response->state = 0;

  this->mission_id = mission_id;
  std::string mission_id_underscores = mission_id;
  std::replace(mission_id_underscores.begin(), mission_id_underscores.end(), '-', '_'); // replace all '-' to '_'

  // this->calculate_plan_server_ = this->create_service<centralized_msgs::srv::CalculatePlan>("swarm/planner/mission_" + mission_id_underscores + "/calculate", std::bind(&SwarmPlanner::CalculatePlan_callback, this, _1, _2), rmw_qos_profile_services_default, this->_SwarmPlanner_callback_group_ptr);
}

void SwarmPlanner::deletePlanner_callback(const centralized_msgs::srv::DeletePlanner::Request::SharedPtr request, centralized_msgs::srv::DeletePlanner::Response::SharedPtr response)
{
  RCLCPP_INFO(this->get_logger(), "Planner deleted");
  std::string mission_id = request->id;

  response->id = mission_id;
  response->state = 1;
}

void SwarmPlanner::updatePlannerAgents_callback(const centralized_msgs::srv::UpdatePlannerAgents::Request::SharedPtr request, centralized_msgs::srv::UpdatePlannerAgents::Response::SharedPtr response)
{
  RCLCPP_INFO(this->get_logger(), "Updating Agents");
  std::string mission_id = request->id;

  this->_planner_agents = request->agents;

  response->id = mission_id;
}




void SwarmPlanner::GetPlan_callback(const centralized_msgs::srv::GetPlan::Request::SharedPtr request, centralized_msgs::srv::GetPlan::Response::SharedPtr response)
{
  RCLCPP_INFO(this->get_logger(), "GetPlan_callback");
  try
  {
    std::string mission_id = request->id;
    nlohmann::json planning_result = this->planning_result_example;
    auto task_array = nlohmann::json::array();

    RCLCPP_INFO(this->get_logger(), "I heard that I should give a plan for this many agents: %ld",this->_planner_agents.size());
    for (centralized_msgs::msg::Agent agent : this->_planner_agents)
    {
      RCLCPP_INFO(this->get_logger(), "agent: %s",agent.agent_id.c_str());
      auto task = this->planning_result_example["tasks"].at(0);
      task["agent_id"] = agent.agent_id;
      task_array.push_back(task);
    }
    planning_result["tasks"] = task_array;

    // Simulated plan calculation
    response->id = this->mission_id;
    // response->state = 1;
    response->plan = planning_result.dump();
  }

  catch (const std::exception &e)
  {
    RCLCPP_INFO(this->get_logger(), "An error occured during GetPlan_callback");
  }
}


json SwarmPlanner::_readJsonFile(std::string json_path, std::string json_file_name)
{
   return this->_json_parser.readJsonFile(json_path, json_file_name);
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
  auto test_swarm_planner_node = std::make_shared<SwarmPlanner>();
  // add node
  executor_ptr->add_node(test_swarm_planner_node);
  // spin execution
  executor_ptr->spin();
  // Shutdown executor
  rclcpp::shutdown();
  return 0;
}


