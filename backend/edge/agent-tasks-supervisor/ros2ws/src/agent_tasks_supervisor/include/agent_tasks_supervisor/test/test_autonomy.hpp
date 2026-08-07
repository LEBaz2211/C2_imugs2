#include <rclcpp/rclcpp.hpp>
// #include <rclcpp_action/rclcpp_action.hpp>

#include <cstdio>
#include <fstream>
#include <cmath>

#include <custom_libraries/geo_computation.hpp> // custom library for geographical transformations

//srv


#include <geographic_msgs/msg/geo_pose_with_covariance_stamped.hpp>
// #include <swarm_planner_msgs/srv/calculate_plan.hpp>


// msg
#include "nav_msgs/msg/odometry.hpp"
#include "geometry_msgs/msg/quaternion.hpp"

#include <geometry_msgs/msg/pose.hpp>
#include <geometry_msgs/msg/twist.hpp>

#include <std_msgs/msg/string.hpp>
#include <std_srvs/srv/trigger.hpp>

#include "autonomy_msgs/msg/autonomy_objective.hpp"
#include "autonomy_msgs/msg/autonomy_set_objective.hpp"
#include "autonomy_msgs/msg/vehicle_profile.hpp"
#include "autonomy_msgs/msg/localization.hpp"
#include "autonomy_msgs/msg/sensor_properties.hpp"
#include "autonomy_msgs/msg/autonomy_status.hpp"
#include "autonomy_msgs/msg/autonomy_trajectory.hpp"
#include "autonomy_msgs/msg/vehicle_constraints.hpp"
#include "autonomy_msgs/msg/vehicle_info.hpp"

// #include <autonomy_msgs/action/set_objective.hpp>

#include <custom_libraries/uuid_library.hpp> // custom library for uuid







// json parser
// #include <json/json_parser.hpp>
#include <nlohmann/json.hpp>



using json = nlohmann::json;

using namespace std::chrono_literals;
using namespace std::placeholders;


/***********************************************************************/
class Autonomy : public rclcpp::Node
{
private:
  std::string AUTONOMY_TOPIC_PREFIX = std::getenv("AUTONOMY_TOPIC_PREFIX");

  bool _null_objective = true;
  float _objective_distance_tolerance = 0.0;
  nav_msgs::msg::Odometry _odometry;
  int coordinate_mode;
  autonomy_msgs::msg::AutonomyObjective _current_objective;
  std::vector<float> _current_arrival_point;
  autonomy_msgs::msg::VehicleProfile vehicle_profile;
  autonomy_msgs::msg::AutonomyStatus _autonomy_status;
  autonomy_msgs::msg::AutonomyPrimitiveStatus _current_primitive_status;
  bool _objective_received = false;

  // swarm_manager::json_lib::JsonParser _json_parser;

  // Messages
  // rclcpp_action::Server<SetObjective>::SharedPtr _action_server;

  rclcpp::Subscription<autonomy_msgs::msg::AutonomySetObjective>::SharedPtr _objective_subscriber;
  rclcpp::Publisher<nav_msgs::msg::Odometry>::SharedPtr _localization_publisher;
  rclcpp::Publisher<autonomy_msgs::msg::AutonomyStatus>::SharedPtr _autonomy_status_publisher;
  rclcpp::Publisher<autonomy_msgs::msg::VehicleProfile>::SharedPtr _vehicle_profile_publisher;
  rclcpp::Client<std_srvs::srv::Trigger>::SharedPtr _detected_obstacle_client;


  // ros attributes
  rclcpp::CallbackGroup::SharedPtr _cb_grp_int;

  // Timers
  rclcpp::TimerBase::SharedPtr _localization_timer;
  rclcpp::TimerBase::SharedPtr _motion_control_timer;
  rclcpp::TimerBase::SharedPtr _vehicle_profile_timer;


  // METHODS

  
  // void _initActionServer();
  // rclcpp_action::GoalResponse _goal_callback(const rclcpp_action::GoalUUID &uuid,
  //                                             std::shared_ptr<const SetObjective::Goal> goal);
  // rclcpp_action::CancelResponse _cancel_callback(const std::shared_ptr<GoalHandleSetObjective> goal_handle);
  // void _execute_callback(const std::shared_ptr<GoalHandleSetObjective> goal_handle);

  void _initInterface();
  void _initOdometry();
  void _initVehicleProfile();
  void _objective_subscriber_callback(const autonomy_msgs::msg::AutonomySetObjective::SharedPtr msg);
  void _localization_publisher_callback();
  void _vehicle_profile_publisher_callback();
  void _motion_control_callback();

  // json _readJsonFile(std::string json_path, std::string json_file_name);

public:
  // using SetObjective = autonomy_msgs::action::SetObjective;
  // using GoalHandleSetObjective = rclcpp_action::ServerGoalHandle<SetObjective>;

  Autonomy(std::string node_name);
  ~Autonomy();
};