#include <rclcpp/rclcpp.hpp>
#include <cstdio>
#include <fstream>

#include <custom_libraries/json_parser.hpp>
#include <custom_libraries/uuid_library.hpp>

#include <nlohmann/json.hpp>

//srv
#include <c2_msgs/srv/init_mission.hpp>
#include <c2_msgs/srv/change_mission_status.hpp>
#include <c2_msgs/srv/change_mission_vehicle.hpp>

#include <centralized_msgs/srv/get_plan.hpp>
#include <centralized_msgs/msg/plan_calculated.hpp>
#include <centralized_msgs/srv/create_planner.hpp>
#include <centralized_msgs/srv/delete_planner.hpp>
#include <centralized_msgs/srv/update_planner_agents.hpp>



// msg
#include <c2_msgs/msg/mission_feedback.hpp>
#include <c2_msgs/msg/swarm_log.hpp>

#include <centralized_msgs/msg/agent.hpp>

// json parser
#include <c2_msgs/json/MissionConfig.hpp>

// Enum lib
#include <c2_msgs/json/Enums.hpp>


using json = nlohmann::json;

using namespace std::chrono_literals;
using namespace std::placeholders;


/***********************************************************************/
class SwarmPlanner : public rclcpp::Node
{
private:
  std::string mission_id;
  centralized_coordination::json_lib::JsonParser _json_parser;
  nlohmann::json planning_result_example = this->_json_parser.readJsonFile("test/json_example/", "planning_result.json");
  nlohmann::json mission_config_example = this->_json_parser.readJsonFile("test/json_example/", "mission_config.json");
  std::vector<centralized_msgs::msg::Agent> _planner_agents;
  // Service
  rclcpp::Service<centralized_msgs::srv::GetPlan>::SharedPtr get_plan_server_;
  rclcpp::Service<centralized_msgs::srv::CreatePlanner>::SharedPtr create_planner_server_;
  rclcpp::Service<centralized_msgs::srv::DeletePlanner>::SharedPtr delete_planner_server_;
  rclcpp::Service<centralized_msgs::srv::UpdatePlannerAgents>::SharedPtr update_planner_agents_server_;

  // ros attributes
  rclcpp::CallbackGroup::SharedPtr _SwarmPlanner_callback_group_ptr;

  // Timers
  rclcpp::TimerBase::SharedPtr _timer;

  // METHODS
  void _initPlannerServices();
  void GetPlan_callback(const centralized_msgs::srv::GetPlan::Request::SharedPtr request, centralized_msgs::srv::GetPlan::Response::SharedPtr response);
  void createPlanner_callback(const centralized_msgs::srv::CreatePlanner::Request::SharedPtr request, centralized_msgs::srv::CreatePlanner::Response::SharedPtr response);
  void deletePlanner_callback(const centralized_msgs::srv::DeletePlanner::Request::SharedPtr request, centralized_msgs::srv::DeletePlanner::Response::SharedPtr response);
  void updatePlannerAgents_callback(const centralized_msgs::srv::UpdatePlannerAgents::Request::SharedPtr request, centralized_msgs::srv::UpdatePlannerAgents::Response::SharedPtr response);
  
  json _readJsonFile(std::string json_path, std::string json_file_name);

public:
  SwarmPlanner(/* args */);
  ~SwarmPlanner();
};