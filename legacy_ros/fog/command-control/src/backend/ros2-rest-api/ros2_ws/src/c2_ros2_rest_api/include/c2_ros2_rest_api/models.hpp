/****************************************************************/
// Swarm manager - MODELS
// Emile Le Flecher & Alexandre La Grappe - RMA - alexandre.lagrappe@mil.be or emile.leflecher@mil.be 
// 21.02.2022 - V1.0.0
/****************************************************************/
#pragma once

#ifndef AGENT_H
#define AGENT_H

#include <string>
#include <vector>
#include <optional>
#include "rclcpp/client.hpp"

// Standard messages & services
#include "geographic_msgs/msg/geo_pose.hpp"

// Custom messages & services
// Swarm manager msgs
#include <c2_msgs/json/MissionConfig.hpp>
#include <c2_msgs/json/Enums.hpp>

// Swarm client msgs
#include "swarm_client_msgs/srv/add_task.hpp"
#include "swarm_client_msgs/srv/change_state.hpp"
#include "swarm_client_msgs/srv/change_task_state.hpp"

namespace models {

  // Define a Waypoint class to represent a single waypoint
  class Waypoint {
    public:
      std::string waypoint_id;
      geographic_msgs::msg::GeoPose pose;
      double speed;
      double wait_time;
  };

  // Define a Task class to represent a sequence of Waypoints
  class Task {
    public:
      std::string task_id;
      int status;
      std::vector<Waypoint> waypoints;
  };

  // Define an EdgeClient class to hold RCLCPP clients for interacting with the edge
  class EdgeClient {
    public:
      rclcpp::Client<swarm_client_msgs::srv::AddTask>::SharedPtr add_task_client;
      rclcpp::Client<swarm_client_msgs::srv::ChangeState>::SharedPtr change_state_client;
      rclcpp::Client<swarm_client_msgs::srv::ChangeTaskState>::SharedPtr change_task_state_client;
      int disconnection_count;
  };
  
   // Define a CollisionAvoidance class to handle collision avoidance logic
  class CollisionAvoidance {
    public:
      bool is_executing_task = false;
      bool speed_modulated = false;
      double original_speed;
  };

  // Define an Agent class to represent a single agent
  class Agent {
    public:
      std::string agent_id;
      std::string agent_profile;
      geographic_msgs::msg::GeoPose pose;
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
