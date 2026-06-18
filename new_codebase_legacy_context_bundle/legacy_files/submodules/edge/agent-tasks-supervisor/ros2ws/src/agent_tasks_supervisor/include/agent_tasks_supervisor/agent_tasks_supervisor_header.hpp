/****************************************************************/
// Node swarm manager - Mission & vehicles management module
// Emile Le Flecher - RMA - emile.leflecher@mil.be 
// 21.02.2022 - V0.1
/****************************************************************/

#ifndef AGENT_TASKS_SUPERVISOR_HEADER_HPP
#define AGENT_TASKS_SUPERVISOR_HEADER_HPP

// standard ros include
#include <iostream>
#include <string>
#include <cstdio>
#include <rclcpp/rclcpp.hpp>
#include <rclcpp/callback_group.hpp>

#include <chrono> // to use sleep_for
#include <unistd.h> // to use sleep
 #include <numeric> // to use accumulate and reduce function (compute average)
#include <cctype> // to use lowercase transformation

#include <nlohmann/json.hpp>

// Custom libraries
#include <custom_libraries/geo_computation.hpp> // custom library for geographical transformations
#include <custom_libraries/uuid_library.hpp> // custom library for uuid


// Standard messages
#include <std_msgs/msg/int8.hpp>
#include <std_msgs/msg/string.hpp>
#include <std_srvs/srv/trigger.hpp>
#include <unique_identifier_msgs/msg/uuid.hpp>
#include <geographic_msgs/msg/geo_pose_with_covariance_stamped.hpp>
#include <geometry_msgs/msg/pose.hpp>
#include <geometry_msgs/msg/twist.hpp>
#include "nav_msgs/msg/odometry.hpp"
#include "geometry_msgs/msg/quaternion.hpp"


// Custom messages

#include <task_msgs/msg/feedback.hpp>
#include <task_msgs/msg/task_feedback.hpp>
#include <task_msgs/srv/add_task.hpp>
#include <task_msgs/srv/change_state.hpp>
#include <task_msgs/srv/change_task_state.hpp>

#include <task_msgs/json/include/Isotime.h> // custom standard time conversions

// Custom Autonomy Interface
#include "autonomy_msgs/msg/detected_obstacle.hpp"
#include "autonomy_msgs/msg/autonomy_objective.hpp"
#include "autonomy_msgs/msg/autonomy_set_objective.hpp"
#include "autonomy_msgs/msg/vehicle_profile.hpp"
#include "autonomy_msgs/msg/localization.hpp"
#include "autonomy_msgs/msg/sensor_properties.hpp"
#include "autonomy_msgs/msg/autonomy_status.hpp"
#include "autonomy_msgs/msg/autonomy_primitive_status.hpp"
#include "autonomy_msgs/msg/autonomy_trajectory.hpp"
#include "autonomy_msgs/msg/vehicle_constraints.hpp"
#include "autonomy_msgs/msg/vehicle_info.hpp"
#include <autonomy_msgs/msg/localization.hpp>

// Custom Unity Simulator Interface
// #include <swarm_simulation_msgs/msg/trackball_target.hpp>



using namespace std::chrono_literals;

class Interface;
class AgentTaskSupervisorNode : public rclcpp::Node
{
private:
  /************** PRIVATE ATTRIBUTES **************/

  std::string AUTONOMY_TOPIC_PREFIX = std::getenv("AUTONOMY_TOPIC_PREFIX");

  // ROS parameters from config file
  bool _use_start_time = false;
  int _waypoint_switching_mode = 1;
  float _objective_distance_tolerance = 3;
  int _speed_control_mode = 1;
  bool _edge_only_testing_mode;

  // Structures:
  struct WayPoint {
	std::string objective_id;
	std::vector<float> position{0.0 , 0.0};
  float speed;
  float wait_time = 0.0;
  std::string eta;
  };

  struct TaskStructure {
  std::vector<WayPoint> waypoints;
	std::string task_id;
  int task_type;
  bool override;
  int task_state;
  };  


  // Structure for individual primitives
  struct Primitive {
      std::string id;
      std::string type;
      bool continuous;
      int status;

      std::vector<std::string> primitive_inputs;
      std::vector<std::string> primitive_outputs;
      
      nlohmann::json parameters;

      struct Transition {
          bool ends_objective;
          bool ends_task;
          std::vector<std::string> followed_by_primitives; // Now a std::vector<std::string>
          bool inherit_other_primitives;
          bool resume_after;
      };

      Transition completion; // completion is now a member of the Primitive class

      // Use default values for constructor parameters:
      Primitive(std::string _id, std::string _type, bool _continuous = false, nlohmann::json _parameters = {},
                std::vector<std::string> _inputs = {}, std::vector<std::string> _outputs = {},
                bool _ends_objective = false, bool _ends_task = false, std::vector<std::string> _followed_by_primitives = {}, bool _inherit_other_primitives = false, bool _resume_after = false)
            : id(_id), type(_type), continuous(_continuous), status(autonomy_msgs::msg::AutonomyPrimitiveStatus::PENDING), parameters(_parameters),
              primitive_inputs(_inputs), primitive_outputs(_outputs)
      {
          completion.ends_objective = _ends_objective;
          completion.ends_task = _ends_task;
          completion.followed_by_primitives = _followed_by_primitives;
          completion.inherit_other_primitives = _inherit_other_primitives;
          completion.resume_after = _resume_after;
      }
  };

  struct GoalNode {
    std::string id;
    std::unordered_map<std::string, Primitive*> primitives; // Active primitives in this goal
    GoalNode* parent;  // Parent goal (for resumption)
    Primitive* origin_primitive; // The primitive that led to THIS goal
    std::vector<std::unique_ptr<GoalNode>> children; // Next possible goals

    GoalNode(std::string _id, Primitive* _origin_primitive = nullptr) 
        : id(_id), parent(nullptr), origin_primitive(_origin_primitive) {}

    void addPrimitive(Primitive* primitive) {
        primitives[primitive->id] = primitive;
    }

    void setParent(GoalNode* _parent) {
        parent = _parent;
    }

    void addChild(std::unique_ptr<GoalNode> child) {
        child->setParent(this);
        children.push_back(std::move(child));
    }
};

  struct Objective {
    std::string id;
    bool parallel_execution;
    std::vector<std::unique_ptr<GoalNode>> goal_nodes;  // Stores all goal nodes
    GoalNode* current_goal;  // The active goal node

    Objective(std::string _id, bool _parallel_execution)
        : id(_id), parallel_execution(_parallel_execution), current_goal(nullptr) {}

    void initializeGoalGraph(std::vector<Primitive*> starting_primitives) {
        auto start_node = std::make_unique<GoalNode>("start");
        for (auto* primitive : starting_primitives) {
            start_node->addPrimitive(primitive);
        }
        current_goal = start_node.get();
        goal_nodes.push_back(std::move(start_node));
    }

    void transitionTo(GoalNode* new_goal) {
        current_goal = new_goal;
    }
};


  // Structure for a full task (contains objectives)
  struct Task {
      std::string task_id;
      int task_type;
      bool override;
      std::vector<Objective> objectives;
      std::unordered_map<std::string, Primitive*> primitive_map; // Global lookup for all primitives
      int task_state; // 0: Pending, 1: In Progress, 2: Paused, 3: Completed
      size_t current_objective_index; // Tracks which objective is active

      Task(std::string _task_id, int _task_type, bool _override)
          : task_id(_task_id), task_type(_task_type), override(_override), task_state(0), current_objective_index(0) {}

      void addObjective(Objective objective) {
          objectives.push_back(std::move(objective));
      }

      void registerPrimitive(Primitive* primitive) {
          primitive_map[primitive->id] = primitive;
      }
  };


  // Agent profile
  std::string agent_id;
  std::string agent_id_underscores;
  int agent_state;
  nav_msgs::msg::Odometry _odometry;
  float _current_speed = 0;
  nlohmann::json agent_profile;
  float _max_speed_limit = 10;
  float _distance_to_objective;
  float _remaining_time_to_objective;


  // Task Management
  Task _current_task;
  std::string _current_task_id;
  int _current_task_state;
  time_t _current_task_std;
  bool _task_received = false;
    std::vector<bool> _allowed_transitions;
  int _requested_task_status;
  // Waypoints
  std::vector<std::string> _objective_id_list;
  std::string _current_objective_id;
  size_t _current_objective_index =0;
  
  bool _waiting_here = false;
  float _wait_time_clock = 0;

  // Autonomy interface
  bool _localization_received = false;
  bool _null_objective = true;
  int _mobility_profile = 0;
  bool _autonomy_objective_finished = false;

  
  // Speed control
  float _target_average_speed;
  float _required_speed;
  int _count_of_previous_speeds = 0;
  float _sum_of_previous_speeds = 0;
  std::vector<float> previous_speeds_list;


    // Connection
  bool _connected_to_fog = false;
  bool _connected_to_autonomy = false;
  int _fog_connection_check_counter = 0;
  int _autonomy_connection_check_counter = 0;
  int _fog_connection_timeout = 5;
  int _autonomy_connection_timeout = 5;
  // bool _use_unity_simulator = false; //enable Unity sim

  // Flags
  bool _change_task_status_flag = false;
  bool _start_time_passed = false;


  // RCLCPP
  rclcpp::CallbackGroup::SharedPtr _cb_grp_int;  // callback group for internal processes
  rclcpp::CallbackGroup::SharedPtr cb_grp_ext_;  // callback group for internal processes

  // Publishers
  rclcpp::Publisher<task_msgs::msg::Feedback>::SharedPtr _feedback_publisher;
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr _node_init_publisher;
  rclcpp::Publisher<autonomy_msgs::msg::AutonomySetObjective>::SharedPtr _objective_publisher;
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr _agent_profile_publisher;

  // Subscribers
  rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr _localization_subscriber;
  rclcpp::Subscription<autonomy_msgs::msg::VehicleProfile>::SharedPtr _vehicle_profile_subscriber;
  rclcpp::Subscription<autonomy_msgs::msg::DetectedObstacle>::SharedPtr _detected_obstacle_subscriber; 
  rclcpp::Subscription<autonomy_msgs::msg::AutonomyStatus>::SharedPtr _autonomy_status_subscriber;
  rclcpp::Subscription<autonomy_msgs::msg::AutonomyTrajectory>::SharedPtr _autonomy_trajectory_subscriber;
  rclcpp::Subscription<std_msgs::msg::String>::SharedPtr _connection_check_subscriber;

  // Services
  rclcpp::Service<std_srvs::srv::Trigger>::SharedPtr cmd_server_;
  rclcpp::Service<task_msgs::srv::AddTask>::SharedPtr _add_task_server;
  rclcpp::Service<task_msgs::srv::ChangeState>::SharedPtr _change_state_server;
  rclcpp::Service<task_msgs::srv::ChangeTaskState>::SharedPtr _change_task_state_server;


  // Timers
  rclcpp::TimerBase::SharedPtr _objective_control_timer;
  rclcpp::TimerBase::SharedPtr _speed_control_timer; 
  rclcpp::TimerBase::SharedPtr _task_control_timer;
  rclcpp::TimerBase::SharedPtr _connection_check_timer; 
  rclcpp::TimerBase::SharedPtr _wait_timer;
  rclcpp::TimerBase::SharedPtr _set_objective_timer;
  rclcpp::TimerBase::SharedPtr _feedback_timer;
  rclcpp::TimerBase::SharedPtr _agent_profile_timer;

  
   /************** PRIVATE METHODS **************/

  // Initializations
  void _ReadConfigurationFile();
  void _initAutonomyInterface();
  // void _initSimulatorInterface();
  void _initFogInterface();
  void _initCmdServices();
  void _publishNodeInit();

  bool _check_if_primitive_completed(Primitive* current_primitive, bool is_last_objective);
  void _switch_to_next_objective();
  void _task_completed();


  // Callback functions
  void _stateMachineCallback();
  void _objectiveControl_timer_callback();
  void _speed_control_timer_callback();
  void _taskControl_timer_callback();
  void _connection_check_subscriber_callback(const std_msgs::msg::String::SharedPtr msg);
  void _connection_check_timer_callback();
  void _wait_timer_callback();
  void _set_connected_to_autonomy();
  void commandService_callback(const std_srvs::srv::Trigger::Request::SharedPtr request, std_srvs::srv::Trigger::Response::SharedPtr response);
  void _addTaskService_callback(const task_msgs::srv::AddTask::Request::SharedPtr request, task_msgs::srv::AddTask::Response::SharedPtr response);
  void _changeStateService_callback(const task_msgs::srv::ChangeState::Request::SharedPtr request, task_msgs::srv::ChangeState::Response::SharedPtr response);
  void _changeTaskStateService_callback(const task_msgs::srv::ChangeTaskState::Request::SharedPtr request, task_msgs::srv::ChangeTaskState::Response::SharedPtr response);
  void _set_objective_publisher_callback();
  void _feedback_publisher_callback();
  void _agent_profile_publisher_callback();
  void _localization_subscriber_callback(const nav_msgs::msg::Odometry::SharedPtr msg);
  void _vehicle_profile_subscriber_callback(const autonomy_msgs::msg::VehicleProfile::SharedPtr msg);
  void _detected_obstacle_subscriber_callback(const autonomy_msgs::msg::DetectedObstacle::SharedPtr msg);
  void _autonomy_status_subscriber_callback(const autonomy_msgs::msg::AutonomyStatus::SharedPtr msg);
  void _autonomy_trajectory_subscriber_callback(const autonomy_msgs::msg::AutonomyTrajectory::SharedPtr msg);



  // Helper functions
  void _updateAllowedTransitions(int new_state);
  std::string _taskStatusToString(int task_status);

  
  // For Unity simulator
  // void _set_simu_objective_publisher_callback();
  // void _localization_simu_subscriber_callback(const autonomy_msgs::msg::Localization msg);


public:
  /************** PUBLIC METHODS **************/
  AgentTaskSupervisorNode(std::string node_name);
  ~AgentTaskSupervisorNode();
  
};

#endif // AGENT_TASKS_SUPERVISOR_HEADER_HPP
