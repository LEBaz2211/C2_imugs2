#include "c2_ros2_rest_api/c2_rest.hpp"

C2::C2() : Node("c2_node") {
    this->_mission_id = "";  // Initialize with empty mission ID
    this->initSwarmManagerInterface();
}

C2::~C2() {
    // Destructor code
}

void C2::setMissionConfig(const nlohmann::json& missionConfig) {
    RCLCPP_INFO(this->get_logger(), "setMissionConfig...");
    this->_mission_id = missionConfig["mission_id"];
    this->_mission_config = missionConfig;
}

void C2::sendInitMission() {
    RCLCPP_INFO(this->get_logger(), "sendInitMission...");
    c2_msgs::msg::InitMissionRequest request;
    request.mission_id = convertStringUuidtoRosUuid(this->_mission_id);
    request.mission_config = this->_mission_config.dump();  // Serialize the mission config to string
    this->_init_mission_pub_ptr->publish(request);
}
void C2::_initMissionResponseCallback(const c2_msgs::msg::InitMissionResponse::SharedPtr msg)
{
  std::cout << "response from the swarm: " << convertRosUuidtoStringUuid(msg.get()->mission_id) << " with the feedback: " << msg.get()->mission_feedback << std::endl;
}




void C2::sendChangeStatus(int requestedState) {
    RCLCPP_INFO(this->get_logger(), "sendChangeStatus...");
    c2_msgs::msg::ChangeMissionStatusRequest request;
    request.mission_id = convertStringUuidtoRosUuid(this->_mission_id);
    request.mission_request_status = requestedState;  // Set the mission status
    this->_change_mission_status_pub_ptr->publish(request);
}
void C2::_changeMissionStatusResponseCallback(const c2_msgs::msg::ChangeMissionStatusResponse::SharedPtr msg)
{
  std::cout << "response for mission status change received for mission: " << convertRosUuidtoStringUuid(msg.get()->mission_id) << std::endl;
}

void C2::initSwarmManagerInterface() {
    rclcpp::QoS swarm_manager_qos = rclcpp::QoS(
        rclcpp::QoSInitialization(
        rmw_qos_profile_services_default.history,
        rmw_qos_profile_services_default.depth
        ),
        rmw_qos_profile_services_default);
    if (this->_swarm_manager_qos_avoid_ros_prefix){swarm_manager_qos.avoid_ros_namespace_conventions(true);};

    this->_init_mission_sub_ptr = this->create_subscription<c2_msgs::msg::InitMissionResponse>("/multi_robot/mission_init_response", swarm_manager_qos, std::bind(&C2::_initMissionResponseCallback, this, std::placeholders::_1));
    this->_init_mission_pub_ptr = this->create_publisher<c2_msgs::msg::InitMissionRequest>("/multi_robot/mission_init_request", swarm_manager_qos);

    this->_change_mission_status_sub_ptr = this->create_subscription<c2_msgs::msg::ChangeMissionStatusResponse>("/multi_robot/change_mission_status_response", swarm_manager_qos, std::bind(&C2::_changeMissionStatusResponseCallback, this, std::placeholders::_1));
    this->_change_mission_status_pub_ptr = this->create_publisher<c2_msgs::msg::ChangeMissionStatusRequest>("/multi_robot/change_mission_status_request", swarm_manager_qos);

    RCLCPP_INFO(this->get_logger(), "ROS2 interface initialized...");
}

