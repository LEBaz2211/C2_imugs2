/****************************************************************/
// Swarm manager - TOOLS
// Emile Le Flecher & Alexandre La Grappe - RMA - alexandre.lagrappe@mil.be or emile.leflecher@mil.be 
// 21.02.2022 - V1.0.0
/****************************************************************/

#ifndef TOOLS_HPP
#define TOOLS_HPP

#include <vector>
#include <utility>
#include <optional>

// Custom models & structures
#include "models.hpp"
using models::EdgeClient;
using models::Agent;
using models::Task;
using models::Waypoint;


namespace tools {

    // Return all possible pair combinations from given list
    template <typename T>
    inline std::list<std::pair<T, T>> get_all_pairs(std::list<T> const &elements)
    {
        std::list<std::pair<T, T>> pairs;
        for (auto first = elements.begin(); first != elements.end(); ++first) {
            for (auto second = std::next(first); second != elements.end(); ++second) {
                pairs.emplace_back(*first, *second);
            }
        }
        return pairs;
    }

    // Check if agent is in a list, given its agent_id
    inline bool agent_is_in_list(std::string agent_id, std::list<Agent> agent_list)
    {
        auto agent_it = std::find_if(std::begin(agent_list), std::end(agent_list),
                                    [&agent_id](const Agent &a) { return a.agent_id == agent_id; });
        return agent_it != std::end(agent_list);
    }

    // Calculate distance between two poses
    inline double distance_between_poses(geographic_msgs::msg::GeoPose pose1, geographic_msgs::msg::GeoPose pose2) {
        double dlat = pose1.position.latitude - pose2.position.latitude;
        double dlong = pose1.position.longitude - pose2.position.longitude;
        return sqrt(dlat * dlat + dlong * dlong);
    }

    // Get the normalized direction vector from  pose1 to pose2 (normalized to +- one meter)
    inline std::vector<double> direction_vector(geographic_msgs::msg::GeoPose pose1, geographic_msgs::msg::GeoPose pose2) {
        double dlat = pose2.position.latitude - pose1.position.latitude;
        double dlong = pose2.position.longitude - pose1.position.longitude;

        double L = sqrt(dlat * dlat + dlong * dlong)*111000; // 1 deg= 111000 m

        std::vector<double> direction_vector = (L > 0.0) ? std::vector<double>{dlong/L, dlat/L} : std::vector<double>{0, 0};
        return direction_vector;
    }

    // Dot product of two vectors
    inline double dot_product(std::vector<double> &v1, std::vector<double> &v2){
        double product = 0;
        for(size_t i=0;i<v1.size();i++)
            product += v1[i] * v2[i];
        return product;
    }


    // Function to check if the relative distance between the midpoints of two normalized direction vectors
    // is smaller than the relative distance between the start points
    inline bool are_agents_approaching(Agent agent1, Agent agent2)
    {
        // Compute midpoints of the normalized (to +- one meter) direction vectors for both agents, 
        // then check if their relative distance < distance between current agent positions
        geographic_msgs::msg::GeoPose mid1;
        if (agent1.collision_avoidance.is_executing_task)
        {
            mid1.position.longitude = (agent1.pose.position.longitude + direction_vector(agent1.pose, agent1.current_task.waypoints[0].pose)[0])/2;
            mid1.position.latitude = (agent1.pose.position.latitude + direction_vector(agent1.pose, agent1.current_task.waypoints[0].pose)[1])/2; 
        }
        else
        {
            mid1 = agent1.pose;
        }
        

        geographic_msgs::msg::GeoPose mid2;
        if (agent1.collision_avoidance.is_executing_task)
        {
            mid2.position.longitude = (agent2.pose.position.longitude + direction_vector(agent2.pose, agent1.current_task.waypoints[0].pose)[0])/2;
            mid2.position.latitude = (agent2.pose.position.latitude + direction_vector(agent2.pose, agent1.current_task.waypoints[0].pose)[1])/2;
        }
        else
        {
            mid2 = agent2.pose;
        }

        return (distance_between_poses(mid1, mid2) < distance_between_poses(agent1.pose, agent2.pose));
    }


    // Give time at which tolerance distance might be transgressed for two given agents
    inline std::optional<double> check_collision(Agent agent1, Agent agent2,  double tolerance_distance) {
        double a1_long = agent1.pose.position.longitude;
        double a1_lat = agent1.pose.position.latitude;
        double a2_long = agent2.pose.position.longitude;
        double a2_lat = agent2.pose.position.latitude;
        double a1_dest_long = agent1.current_task.waypoints[0].pose.position.longitude;
        double a1_dest_lat = agent1.current_task.waypoints[0].pose.position.latitude;
        double a2_dest_long = agent2.current_task.waypoints[0].pose.position.longitude;
        double a2_dest_lat = agent2.current_task.waypoints[0].pose.position.latitude;


        // Project speed values on x-y axes:
        double speed1 = agent1.current_task.waypoints[0].speed;
        double speed2 = agent2.current_task.waypoints[0].speed;

        double dlong1 = a1_dest_long - a1_long;
        double dlat1 = a1_dest_lat - a1_lat;
        double distance1 = sqrt(dlong1*dlong1 + dlat1*dlat1);
        double unit_long1 = dlong1 / distance1;
        double unit_lat1 = dlat1 / distance1;

        double dlong2 = a2_dest_long - a2_long;
        double dlat2 = a2_dest_lat - a2_lat;
        double distance2 = sqrt(dlong2*dlong2 + dlat2*dlat2);
        double unit_long2 = dlong2 / distance2;
        double unit_lat2 = dlat2 / distance2;

        double a1_vlong = speed1 * unit_long1;
        double a1_vlat = speed1 * unit_lat1;
        double a2_vlong = speed2 * unit_long2;
        double a2_vlat = speed2 * unit_lat2;

        // Calculate the time at which the agents are closest to each other, 
        // by solving the quadratic equation t = (-b ± √(b^2 - 4ac)) / 2a, 
        // since the condition " |agent1_pose(t) - agent2_pose(t)| <= tolerance "  is of the form at^2 + bt + c <= 0
        // and check if the solutions of time are within the time frame of the agents. 
        // If the discriminant is negative, it means there are no real solutions and therefore the agents will not collide.

        double a = pow(a1_vlong - a2_vlong, 2) + pow(a1_vlat - a2_vlat, 2);
        double b = 2 * ((a1_long - a2_long) * (a1_vlong - a2_vlong) + (a1_lat - a2_lat) * (a1_vlat - a2_vlat));
        double c = pow(a1_long - a2_long, 2) + pow(a1_lat - a2_lat, 2) - pow(tolerance_distance/111000, 2);


        double discriminant = pow(b, 2) - 4 * a * c;
        if (discriminant < 0) return std::nullopt; // no real solutions

        // Solutions:
        double t_a = (-b + sqrt(discriminant)) / (2 * a);
        double t_b = (-b - sqrt(discriminant)) / (2 * a);


        // Select minimum positive time solution:
        double time_to_collision = std::fmin(std::fmax(t_a, 0.0), std::fmax(t_b, 0.0));

        // calculate the time until each agent reaches its destination
        double t1_dest = sqrt(pow(a1_dest_long - a1_long, 2) + pow(a1_dest_lat - a1_lat, 2)) / speed1;
        double t2_dest = sqrt(pow(a2_dest_long - a2_long, 2) + pow(a2_dest_lat - a2_lat, 2)) / speed2;


        // check if solution is within the time frame of both agents' destinations 
        if ( 0 < time_to_collision && time_to_collision <= t1_dest  && time_to_collision <= t2_dest){
            // std::cout << "tools:check_collision -> POTENTIAL COLLISION " << std::endl;
            return time_to_collision;
        }
        return std::nullopt;
    }
        // Modulate speed for two given agents
    inline Agent avoid_collision_in_pair(Agent decel_agent, Agent other_agent,  double tolerance_distance, std::optional<double> time_to_collision, double max_deceleration_factor) {

        double original_speed = decel_agent.collision_avoidance.original_speed;
        double new_speed = original_speed;
        std::cout << "- new speed - " << new_speed << "- Original speed - " << original_speed <<  std::endl; 
        while(time_to_collision && new_speed>max_deceleration_factor*original_speed) // don't go below 10 percent of original speed
        {
            new_speed*= 0.9; // reduce by 10 percent
            
            decel_agent.current_task.waypoints[0].speed = new_speed;
            time_to_collision = check_collision( decel_agent,  other_agent,  tolerance_distance) ;
        }

        // if (time_to_collision) // if collision can't be avoided at very low speed
        // {
        // }
        return decel_agent;
    }

    // Accelerate agent after slowing it down
    inline Agent reaccelerate_agent_safely(Agent accel_agent, std::list<Agent> agent_list,  double tolerance_distance) {
 
        std::optional<double> time_to_collision;
        double new_speed =  accel_agent.current_task.waypoints[0].speed; 
        double original_speed = accel_agent.collision_avoidance.original_speed;
        
        while(!time_to_collision && new_speed<=original_speed) // don't go below 10 percent of original speed
        {
            new_speed*= 1.1; // Increase by 10 percent
            accel_agent.current_task.waypoints[0].speed = (new_speed < original_speed)? new_speed : original_speed;

            // Check with all other agents if this acceleration does not introduce collision risks:
            for (Agent other_agent : agent_list)
            {
                if (other_agent.agent_id != accel_agent.agent_id)
                {
                    time_to_collision = check_collision( accel_agent,  other_agent,  tolerance_distance) ;
                    if (time_to_collision)
                    {   // Collision risk, stop accelerating here
                        accel_agent.current_task.waypoints[0].speed *= 0.9;   
                        break; 
                    }
                }
            }
        }
        return accel_agent;
    }
}



#endif