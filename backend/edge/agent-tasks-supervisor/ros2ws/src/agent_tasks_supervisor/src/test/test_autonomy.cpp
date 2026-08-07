/****************************************************************/
/*    Code to test custom message which are sent from Autonomy        */
/*    Emile Le Flecher - RMA - 24.02.2022                       */
/****************************************************************/
#include <agent_tasks_supervisor/test/test_autonomy.hpp>

Autonomy::Autonomy(std::string node_name) : Node(node_name)
{

  this->_cb_grp_int = this->create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
  // this->_initActionServer();
  this->_initInterface();
  this->_initOdometry();
  this->_initVehicleProfile();

  this->_motion_control_timer = this->create_wall_timer(100ms, std::bind(&Autonomy::_motion_control_callback, this));

  RCLCPP_INFO(this->get_logger(), "test_autonomy_node init done");
}

/****************************************************************/

Autonomy::~Autonomy()
{
}

/****************************************************************/

// void Autonomy::_initActionServer()
// {
//     _action_server = rclcpp_action::create_server<SetObjective>(
//         this,
//         "set_objective",
//         std::bind(&Autonomy::_goal_callback, this, std::placeholders::_1, std::placeholders::_2),
//         std::bind(&Autonomy::_cancel_callback, this, std::placeholders::_1),
//         std::bind(&Autonomy::_execute_callback, this, std::placeholders::_1));

//     RCLCPP_INFO(this->get_logger(), "Action server for 'set_objective' initialized.");
// }

void Autonomy::_initInterface()
{
  /*********** Objective Subscriber ****************/
  this->_objective_subscriber = this->create_subscription<autonomy_msgs::msg::AutonomySetObjective>(this->AUTONOMY_TOPIC_PREFIX +"/edge/multi_robot/autonomy_set_objective", 10, std::bind(&Autonomy::_objective_subscriber_callback, this, _1));
  
  /*********** Localization Publisher ****************/
  this->_localization_publisher = this->create_publisher<nav_msgs::msg::Odometry>(this->AUTONOMY_TOPIC_PREFIX +"/edge/multi_robot/localization", 10);
  _localization_timer = this->create_wall_timer(500ms, std::bind(&Autonomy::_localization_publisher_callback, this));

  /*********** Swarming Status Publisher ****************/
  this->_autonomy_status_publisher = this->create_publisher<autonomy_msgs::msg::AutonomyStatus>(this->AUTONOMY_TOPIC_PREFIX +"/edge/multi_robot/autonomy_status", 10);

  /*********** Vehicle Profile Publisher ****************/
  this->_vehicle_profile_publisher = this->create_publisher<autonomy_msgs::msg::VehicleProfile>(this->AUTONOMY_TOPIC_PREFIX +"/edge/multi_robot/vehicle_profile", 10);
  _vehicle_profile_timer = this->create_wall_timer(1000ms, std::bind(&Autonomy::_vehicle_profile_publisher_callback, this));


  /*********** Detected Obstacle Client ****************/
  // this->_detected_obstacle_client = this->create_client<std_srvs::srv::Trigger>(this->AUTONOMY_TOPIC_PREFIX +"/edge/multi_robot/detected_obstacle", rmw_qos_profile_default, this->_cb_grp_int);
}



void Autonomy::_objective_subscriber_callback(const autonomy_msgs::msg::AutonomySetObjective::SharedPtr msg)
{
    if (!msg->null_objective)
    {
        this->_current_objective = msg->objective;
        this->_autonomy_status.primitive_statuses.clear();
        // Loop through primitives to find a "waypoint" primitive
        for (const std::string& primitive_json_str : this->_current_objective.primitives)
        {
            nlohmann::json primitive_json = nlohmann::json::parse(primitive_json_str);

            if (primitive_json["type"] == "waypoint")
            {
                // Extract arrival point from parameters
                auto parameters = primitive_json["parameters"];
                if (parameters.contains("coordinates"))
                {
          
                    this->_current_arrival_point = parameters.at("coordinates").get<std::vector<float>>();
                    break; // Stop after the first waypoint found
                }
                this->_current_primitive_status.primitive_id  = convertStringUuidtoRosUuid(primitive_json["id"]) ;
                this->_current_primitive_status.primitive_type  = primitive_json["type"] ;
                this->_current_primitive_status.status  = autonomy_msgs::msg::AutonomyStatus::ACTIVE;
                
                this->_autonomy_status.primitive_statuses.push_back(this->_current_primitive_status);
            }
        }

        this->_null_objective = false;
        RCLCPP_INFO(this->get_logger(), "I heard an objective and set the arrival point.");
    }
    else
    {
        this->_null_objective = true;
        RCLCPP_INFO(this->get_logger(), "NO OBJECTIVE");
    }
}

void Autonomy::_initOdometry()
{
  // Create message
  nav_msgs::msg::Odometry odom_msg;

  // Set frame_id
  declare_parameter<int>("coordinate_mode", 0);
  this->coordinate_mode = get_parameter("coordinate_mode").as_int();
  if (this->coordinate_mode == 0) {
      odom_msg.header.frame_id = "map";  // Global frame
  }
  else {
      odom_msg.header.frame_id = this->AUTONOMY_TOPIC_PREFIX;  // Local frame
  }
  // Set initial location
  declare_parameter<std::vector<double>>("start_location", std::vector<double>(0.0, 0.0));
  std::vector<double> start_location = get_parameter("start_location").as_double_array();
  odom_msg.header.stamp = this->get_clock()->now();
  odom_msg.child_frame_id = "base_link";

  odom_msg.pose.pose.position.x = start_location[0];
  odom_msg.pose.pose.position.y = start_location[1];
  odom_msg.pose.pose.position.z = 0.0;

  odom_msg.pose.pose.orientation.x = 0.0;
  odom_msg.pose.pose.orientation.y = 0.0;
  odom_msg.pose.pose.orientation.z = 0.0;
  odom_msg.pose.pose.orientation.w = 1.0;

  odom_msg.twist.twist.linear.x = 0.0;
  odom_msg.twist.twist.linear.y = 0.0;
  odom_msg.twist.twist.linear.z = 0.0;

  this->_odometry = odom_msg;
}

void Autonomy::_initVehicleProfile()
{
  // Declare general vehicle parameters
  this->declare_parameter<std::string>("vehicle_type", "ugv");
  this->declare_parameter<int>("active_autonomy_mode", 1);
  this->declare_parameter<double>("max_speed", 3.65);
  this->declare_parameter<double>("max_acceleration", 7.65);
  this->declare_parameter<double>("max_weight", 15.5);
  this->declare_parameter<double>("max_tilt_angle", 1.5);
  this->declare_parameter<double>("fuel_status_pct", 90.0);
  this->declare_parameter<double>("fuel_hours", 1.43);
  this->declare_parameter<double>("battery_status_pct", 95.0);
  this->declare_parameter<double>("battery_hours", 3.25);
  this->declare_parameter<std::vector<double>>("vehicle_dimensions", {0.85, 0.52, 0.56});

  // Fix: Explicitly use std::vector<std::string>() instead of {}
  this->declare_parameter<std::vector<std::string>>("sensors", std::vector<std::string>());

  // Retrieve general vehicle parameters
  this->vehicle_profile.active_autonomy_mode = this->get_parameter("active_autonomy_mode").as_int();

  auto vehicle_constraints = autonomy_msgs::msg::VehicleConstraints();
  vehicle_constraints.max_speed.linear.x = this->get_parameter("max_speed").as_double();
  vehicle_constraints.max_acceleration.linear.x = this->get_parameter("max_acceleration").as_double();
  vehicle_constraints.max_weight = this->get_parameter("max_weight").as_double();
  vehicle_constraints.max_tilt_angle = this->get_parameter("max_tilt_angle").as_double();

  auto vehicle_info = autonomy_msgs::msg::VehicleInfo();
  vehicle_info.vehicle_type = this->get_parameter("vehicle_type").as_string();
  vehicle_info.fuel_status_pct = this->get_parameter("fuel_status_pct").as_double();
  vehicle_info.fuel_hours = this->get_parameter("fuel_hours").as_double();
  vehicle_info.battery_status_pct = this->get_parameter("battery_status_pct").as_double();
  vehicle_info.battery_hours = this->get_parameter("battery_hours").as_double();

  // Fix: Convert std::vector<double> to std::vector<float>
  std::vector<double> dimensions_double = this->get_parameter("vehicle_dimensions").as_double_array();
  std::vector<float> dimensions_float(dimensions_double.begin(), dimensions_double.end());
  vehicle_info.vehicle_dimensions = dimensions_float;

  // Retrieve sensor list
  std::vector<std::string> sensor_names = this->get_parameter("sensors").as_string_array();
  std::vector<autonomy_msgs::msg::SensorProperties> sensor_list;

  for (const auto& sensor_name : sensor_names)
  {
    std::string type_param = sensor_name + ".type";
    std::string status_param = sensor_name + ".status";
    std::string fov_param = sensor_name + ".field_of_view";

    this->declare_parameter<int>(type_param, 1);
    this->declare_parameter<int>(status_param, 1);
    this->declare_parameter<std::vector<double>>(fov_param, {60.0, 3.14});

    auto sensor = autonomy_msgs::msg::SensorProperties();
    sensor.type = this->get_parameter(type_param).as_int();
    sensor.status = this->get_parameter(status_param).as_int();

    // Fix: Convert std::vector<double> to std::vector<float> for field_of_view
    std::vector<double> fov_double = this->get_parameter(fov_param).as_double_array();
    // std::vector<float> fov_float(fov_double.begin(), fov_double.end());
    sensor.field_of_view = fov_double;

    sensor_list.push_back(sensor);
  }

  vehicle_info.sensor_list = sensor_list;

  // Assign profiles
  this->vehicle_profile.vehicle_constraints = vehicle_constraints;
  this->vehicle_profile.vehicle_info = vehicle_info;

  RCLCPP_INFO(this->get_logger(), "Vehicle Profile Initialized with %lu sensors", sensor_list.size());
}


void Autonomy::_motion_control_callback()
{
    if (!this->_null_objective)
    {
        float long_dist = this->_current_arrival_point[0] - this->_odometry.pose.pose.position.x;
        float lat_dist = this->_current_arrival_point[1] - this->_odometry.pose.pose.position.y;

        float dist_to_objective;
        float travel_dist;

        if (this->coordinate_mode == 1)  // Local coordinates mode
        {
            dist_to_objective = std::sqrt(pow(long_dist, 2) + pow(lat_dist, 2));
            travel_dist = this->_current_objective.max_speed * 0.1;  // dist = speed * time
        }
        else  // Global (GPS) coordinates mode
        {
            dist_to_objective = 111000 * std::sqrt(pow(long_dist, 2) + pow(lat_dist, 2));
            travel_dist = (0.00000901 * this->_current_objective.max_speed) * 0.1; // Convert meters to degrees
        }

        RCLCPP_INFO(this->get_logger(), "Distance to objective: %f meters", dist_to_objective);

        if (dist_to_objective <= this->_objective_distance_tolerance)
        {
            RCLCPP_INFO(this->get_logger(), " ---------- Objective reached");
            this->_autonomy_status.status = autonomy_msgs::msg::AutonomyStatus::COMPLETED;
            this->_current_primitive_status.status =  autonomy_msgs::msg::AutonomyPrimitiveStatus::COMPLETED;
        }
        else
        {
            this->_autonomy_status.status = autonomy_msgs::msg::AutonomyStatus::ACTIVE;

            float d_long = 0;
            float d_lat = 0;

            if (fabs(long_dist) <= travel_dist * std::sqrt(2))
            {
                d_long = 0;
                d_lat = travel_dist;
            }
            if (fabs(lat_dist) <= travel_dist * std::sqrt(2))
            {
                d_long = travel_dist;
                d_lat = 0;
            }
            else
            {
                d_long = fabs(std::sqrt(pow(travel_dist, 2) / (1 + pow(lat_dist / long_dist, 2))));
                d_lat = (fabs(long_dist) <= travel_dist) ? travel_dist : fabs(std::sqrt(pow(travel_dist, 2) / (1 + pow(lat_dist / long_dist, 2))) * lat_dist / long_dist);
            }

            if (long_dist < 0)
            {
                d_long = -d_long;
            }
            if (lat_dist < 0)
            {
                d_lat = -d_lat;
            }

            // Update position
            this->_odometry.pose.pose.position.x += d_long;
            this->_odometry.pose.pose.position.y += d_lat;
        }
    }
}


void Autonomy::_localization_publisher_callback()
{ 
  
  if(!this->_null_objective)
  {
    RCLCPP_INFO(this->get_logger(), "--- Requested speed: %f", this->_current_objective.max_speed);
  }
  
  // RCLCPP_INFO(this->get_logger(), "Publishing Odometry");
  this->_localization_publisher->publish(this->_odometry);
}

void Autonomy::_vehicle_profile_publisher_callback()
{ 
  // this->vehicle_profile.vehicle_info.fuel_hours -= 0.01; // lower battery and fuel level with time
  // this->vehicle_profile.vehicle_info.battery_hours -= 0.01;

  _vehicle_profile_publisher->publish(this->vehicle_profile);

  _autonomy_status_publisher->publish(this->_autonomy_status);
}



/****************************************************************/
/****************************************************************/
/****************************************************************/

int main(int argc, char **argv)
{
  std::string node_name = argv[1];
  std::replace( node_name.begin(), node_name.end(), '-', '_'); // replace all '-' to '_'
  std::cout << "Node name will be: " << node_name << std::endl;
  rclcpp::init(argc, argv);


  // rclcpp::executors::MultiThreadedExecutor executor;
  auto executor_ptr = std::make_shared<rclcpp::executors::MultiThreadedExecutor>();
  // Ros node
  auto test_swarm_planner_node = std::make_shared<Autonomy>(node_name);
  // add node
  executor_ptr->add_node(test_swarm_planner_node);
  // spin execution
  executor_ptr->spin();
  // Shutdown executor
  rclcpp::shutdown();
  return 0;
}
