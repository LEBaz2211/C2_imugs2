#include "json.hpp"

#include <string>

nlohmann::json interface_mission_config = {
    {"mission_id", "IUBI123"},
    {"behavior", 0},
    {"vehicles", {"ddobn321", "ddobn321", "ddobn321", "ddobn321"}},
    {"start", {
        {"geometry", {
            {"feature_id", "1234RDF"},
            {"geometry_type", "square"},
            {"coordinate", {1, 0, 2, 4}}
        }},
        {"tolerance_distance", 42.99},
        {"vehicle_formation", 1},
        {"vehicle_formation_distance", 10},
        {"vehicle_orientation", {1, 0, 2, 4}},
        {"maximize_coverage", true},
        {"start_time", {
            {"latest", "01/03/2022"},
            {"target", "01/02/2022"},
            {"earliest", "02/03/2022"}
        }},
    }},
    {"transit", {
        {"geofence", {
            {"feature_id", "1234RDF"},
            {"geometry_type", "square"},
            {"coordinate", {1, 0, 2, 4}}
        }},
        {"geofence_maximize_coverage", false},
        {"vehicle_formation", 3},
        {"vehicle_formation_distance", 5},
        {"optimalization", {
            {"visibility", 7},
            {"energy", 5},
            {"road_usage", 4}
        }},
        {"desired_vehicule_constraints", {
            {"max_speed", 7},
            {"max_acceleration", 5},
            {"max_jerk", 4},
            {"max_deceleration", 7},
            {"max_straight_slope", 5},
            {"max_side_slope", 4}
        }},

    }},

    {"objective", {
        {"geometry", {
            {"feature_id", "1234RDF"},
            {"geometry_type", "square"},
            {"coordinate", {1, 0, 2, 4}}
        }},
        {"minimum_distance", 42.99},
        {"maximum_distance", 1},
        {"vehicle_formation", 4},
        {"vehicle_formation_distance", 10},
        {"vehicle_orientation", {1, 0, 2, 4}},
        {"vehicle_orientation_origin", {
            {"feature_id", "1234RDF"},
            {"geometry_type", "square"},
            {"coordinate", {1, 0, 2, 4}}
        }},
        {"vehicle_order", true},
        {"maximize_coverage", true},
        {"maximize_coverage_distance", {1, 0, 2, 4}},
        {"arrival_time", {
            {"latest", "01/03/2022"},
            {"target", "01/02/2022"},
            {"earliest", "02/03/2022"}
        }},

    }},

    {"mission_end_time", "04/03/2022"},
};

nlohmann::json interface_mission_feedback = {
    {"mission_id", "IUBI123"},
    {"behavior", 0},
    {"request_status", 1},
    {"status", 2},
    {"issue", 2},
    {"date", "2022-03-26T22:15:00Z"},
    {"tasks", {
        {"vehicle_id", "JIFN12"},
        {"est", "2022-03-26T22:15:00Z"},
        
        {"waypoints", {
            {"coordinate", {1, 0, 2, 4}},
            {"orientation", 23},
            {"average_speed", 5.40},
            {"eta", "2022-03-26T22:15:00Z"}
            
        }},
    }},
};


nlohmann::json interface_swarm_log = {
    {"log_type", 0},
    {"date", "2022-03-26T22:15:00Z"},
    {"log_message", "Planning calculation started"},
};