/****************************************************************/
// Central Coordination - MODELS
// Alexandre La Grappe & Emile Le Flecher  - RMA - alexandre.lagrappe@mil.be or emile.leflecher@mil.be 
// 03.12.2024 - V1.0
/****************************************************************/
#pragma once

#ifndef AGENT_H
#define AGENT_H

#include <string>
#include <vector>
#include <optional>
#include "rclcpp/client.hpp"

// Standard messages & services
#include "nav_msgs/msg/odometry.hpp"
#include "geometry_msgs/msg/pose.hpp"

// Custom messages & services
// C2 msgs
#include <c2_msgs/json/MissionConfig.hpp>
#include <c2_msgs/json/Enums.hpp>

// Swarm client msgs
#include "task_msgs/srv/add_task.hpp"
#include "task_msgs/srv/change_state.hpp"
#include "task_msgs/srv/change_task_state.hpp"

namespace models {

  
  
  class Primitive {
  public:
      std::string primitive_id;
      std::string primitive_type;
      std::vector<std::string> primitive_inputs;
      std::vector<std::string> primitive_outputs;
      nlohmann::json parameters;
      
      struct Completion {
          bool ends_objective;
          bool ends_task;
          std::vector<std::string> followed_by_primitives;
          bool inherit_other_primitives;
          bool resume_after;
      } completion;
  };

  class Objective {
  public:
      std::string objective_id;
      std::string objective_type;
      bool parallel_execution;
      std::vector<Primitive> primitives;
  };

  class Task {
  public:
      std::string task_id;
      int status;
      std::vector<Objective> objectives;
      std::vector<Primitive> primitives;
  };

  // Define an EdgeClient class to hold RCLCPP clients for interacting with the edge
  class EdgeClient {
    public:
      rclcpp::Client<task_msgs::srv::AddTask>::SharedPtr add_task_client;
      rclcpp::Client<task_msgs::srv::ChangeState>::SharedPtr change_state_client;
      rclcpp::Client<task_msgs::srv::ChangeTaskState>::SharedPtr change_task_state_client;
      int disconnection_count;
  };
  
   // Define a CollisionAvoidance class to handle collision avoidance logic
  class CollisionAvoidance {
    public:
      bool is_executing_task = false;
      bool speed_modulated = false;
      double original_speed;
  };
  class Agent {
    public:
      std::string agent_id;
      std::string agent_profile;
      nav_msgs::msg::Odometry odometry;
      double speed;
      Task current_task;
      EdgeClient edge_client;
      CollisionAvoidance collision_avoidance;
  };

  
}


// Custom structures (for c2_interface_node)
struct VehicleChange
{
    std::uint8_t action;
    std::vector<std::string> vehicles_list;
};

struct MissionInfo
{
  c2_msgs::json::MissionConfig mission_config;
  VehicleChange vehicle_change_config;
};

// C2 interface class to store flags
class InterfaceC2State
{
public:
  /** mission **/
  std::string mission_id = "";
  /** Flags **/
  bool flag_new_mission = false;
  bool flag_vehicle_changes = false;

  /** Info **/
  MissionInfo mission_info;

  void flush()
  {
    this->mission_id = "";
    this->flag_new_mission = false;
    this->flag_vehicle_changes = false;
  }
};


// Result class to work with optional types and return success indicators with log messages
template <class T>
class ResultFct
{
public:
        const std::optional<T> Result;
        const bool Success;
        const std::string Log;

        ResultFct(const T result) : Result(result), Success(true), Log(""){};
        ResultFct(const T result, bool success, std::string log) : Result(result), Success(success), Log(log){};
        ResultFct(const std::string error) : Success(false), Log(error){};
};

#endif
