#ifndef C2_HPP
#define C2_HPP

#include <rclcpp/rclcpp.hpp>

#include <string>
#include <iostream>
#include <functional>  // For std::bind and std::placeholders

#include <nlohmann/json.hpp>

#include <custom_libraries/uuid_library.hpp>
#include <custom_libraries/json_parser.hpp>


#include <c2_msgs/srv/init_mission.hpp>
#include <c2_msgs/msg/init_mission_request.hpp>
#include <c2_msgs/msg/init_mission_response.hpp>
#include <c2_msgs/msg/change_mission_status_request.hpp>
#include <c2_msgs/msg/change_mission_status_response.hpp>
#include <c2_msgs/msg/change_mission_vehicle_request.hpp>
#include <c2_msgs/msg/change_mission_vehicle_response.hpp>
#include <environment_msgs/msg/environment_data_reset_request.hpp>
#include <environment_msgs/msg/environment_data_upload_request.hpp>
#include <environment_msgs/msg/environment_data_get_version_request.hpp>
#include <environment_msgs/msg/environment_data_reset_response.hpp>
#include <environment_msgs/msg/environment_data_upload_response.hpp>
#include <environment_msgs/msg/environment_data_get_version_response.hpp>

#include <c2_msgs/srv/change_mission_status.hpp>
#include <c2_msgs/srv/change_mission_vehicle.hpp>

#include <environment_msgs/srv/environment_data_reset.hpp>
#include <environment_msgs/srv/environment_data_upload.hpp>
#include <environment_msgs/srv/environment_data_get_version.hpp>


class C2 : public rclcpp::Node{
public:
    C2();
    ~C2();

    // Mission management methods
    void setMissionConfig(const nlohmann::json& missionConfig);
    void sendInitMission();
    void sendChangeStatus(int requestedState);

    


private:
    // Quality of Service 
    std::string C2_INTERFACE_AVOID_ROS_PREFIX = std::getenv("C2_INTERFACE_AVOID_ROS_PREFIX");
    bool _swarm_manager_qos_avoid_ros_prefix = (C2_INTERFACE_AVOID_ROS_PREFIX=="TRUE") ? true : false;

    // Pub/Sub
    rclcpp::Subscription<c2_msgs::msg::InitMissionResponse>::SharedPtr _init_mission_sub_ptr;
    rclcpp::Publisher<c2_msgs::msg::InitMissionRequest>::SharedPtr _init_mission_pub_ptr;

    rclcpp::Subscription<c2_msgs::msg::ChangeMissionStatusResponse>::SharedPtr _change_mission_status_sub_ptr;
    rclcpp::Publisher<c2_msgs::msg::ChangeMissionStatusRequest>::SharedPtr _change_mission_status_pub_ptr;


    std::string _mission_id;
    nlohmann::json _mission_config;

    // std::shared_ptr<rclcpp::Publisher<c2_msgs::msg::InitMissionRequest>> _init_mission_pub_ptr;
    // std::shared_ptr<rclcpp::Publisher<c2_msgs::msg::ChangeMissionStatusRequest>> _change_mission_status_pub_ptr;
    
    // methods
    void initSwarmManagerInterface();

    // callbacks
    void _initMissionResponseCallback(const c2_msgs::msg::InitMissionResponse::SharedPtr msg);
    void _changeMissionStatusResponseCallback(const c2_msgs::msg::ChangeMissionStatusResponse::SharedPtr msg);
};

#endif
