#pragma once

namespace c2_msgs::json::enums
{
    enum class MissionIssue
    {
        NONE = 0 ,//	No issue
        MISSION_WARN_ID_ALREADY_USED = 10,//	Mission ID is already in use. The corresponding mission configuration will be overwritten. Mission state will be set to INIT.
        MISSION_WARN_UGV_UNAVAILABLE = 11,//	At least one UGV is unavailable. Reduced set of UGVs will be used. Mission state will be set to PLANNED_ALTERNATIVE
        MISSION_WARN_CONFIG_UNKNOWN_DATA = 12,//	The provided mission_config file contains unknown keys. The latter data will simply be ignored. 
        MISSION_WARN_STATUS_NOT_CHANGED = 13,//	The requested mission status change was not valid. The transition will be ignored.
        MISSION_WARN_DISCONNECTED_SWARM_PLANNER = 14,//	Could not communicate with swarm planner. Mission state will not change
        MISSION_WARN_DISCONNECTED_SWARMING_EDGE = 15,//	Could not communicate with at least one  edge module. Mission state will not change
        MISSION_WARN_DISCONNECTED_AUTONOMY = 16,//	Could not communicate with at least one autonomy module. Mission state will not change
        MISSION_FAILED_CONFIG_PARSING_UNSUCCESSFUL = 20,//	The provided mission_config file could not be parsed. Mission state will be set to FAILED.
        MISSION_FAILED_CONFIG_MISSING_DATA = 21,//	The provided mission_config file does not contain sufficient data for plannification. Mission state will be set to FAILED.
        MISSION_FAILED_MISSION_COMPROMISED = 22,//	The mission is compromised and is unable to continue. Mission state will be set to FAILED.
        MISSION_FAILED_DISCONNECTED_SWARM_PLANNER = 23,//	Could not communicate with swarm planner, results in process failure. Mission state will be set to FAILED.
        MISSION_FAILED_DISCONNECTED_EDGE = 24,//	Could not communicate with  edge modules, results in process failure. Mission state will be set to FAILED.
        MISSION_FAILED_DISCONNECTED_AUTONOMY = 25,//	Could not communicate with at least one autonomy module, timeout results in mission failure. Mission state will be set to FAILED
        PLANNING_WARN_VEHICLES_MISMATCH	= 30,// Not enough vehicles for the given mission configuration. Mission state will be set to PLANNED_ALTERNATIVE
        PLANNING_WARN_NOT_ENOUGH_COVERAGE = 31,//	not enough coverage for the given mission configuration. Mission state will be set to PLANNED_ALTERNATIVE
        PLANNING_WARN_DATE_COMPROMISED = 32,//	Requested start or end date is compromised in planning solution. Mission state will be set to PLANNED anyway
        PLANNING_FAILED_NO_SOLUTION_FOUND = 40,//	No planning solution found. New init_mission needed with adjusted configuration. Mission state will be set to PLANNED_FAILED
        PLANNING_FAILED = 41//	Swarm planner process fail,  Mission state will be set to PLANNED_FAILED.
    };

    enum class MissionStatus
    {
        NONE = 0,                // NOT USED
        PLANNED = 1,             // Mission is correctly planned
        PLANNED_ALTERNATIVE = 2, // Mission has alternative planned
        PLANNED_FAILED = 3,      // Mission planning failed
        ACCEPTED = 4,            // Mission is accepted
        STARTED = 5,             // Mission is started
        PAUSED = 6,              // Mission is paused
        FAILED = 7,              // Mission has failed
        STOPPED = 8,             // Mission is finished by request.  it will not stop a mission, except if FAILED or another mission is started.
        DELETED = 9,              // Missio is deleted from the system.
        COMPLETED = 10
    };

    enum class MissionStatusRequest
    {
        INIT = 0,    // Initialize mission
        APPROVE = 1, // Approve mission
        START = 2,   // Start mission
        PAUSE = 3,   // Pause mission
        STOP = 4,    // Stop mission
        DELETE = 5   // Delete mission
    };

    enum class Behavior
    {
        NAVIGATE = 0,             // Navigation/driving based behavior. Used for mission types: Good transportation, CASEVAC, Comm relay, Screen mission, Ballistic protection
        COVERAGE = 1,             // Monitoring/patrolling the objective. Used for mission types: Reconnaissance mission, Patrolling mission
        NAVIGATE_NO_PLANNING = 2, // Navigation/driving based behavior, but without using the planner: Used to test the navigation (local space)
    };

    enum class VehicleFormation
    {
        NONE = 0,
        COLUMN = 1,
        LINE = 2,
        WEDGE = 3,
        VEE = 4,
        LEFT_FLANK = 5,
        RIGHT_FLANK = 6
    };

    enum class VehicleChanges
    {
        ADD = 1,   // Add the vehicles in the list to the mission
        REMOVE = 0 // Remove the vehicles in the list from the mission
    };

    enum class LogType
    {
        INFO = 0,
        WARNING = 1,
        ERROR = 2,
        FATAL = 3
    };

    enum class EnvironmentDataResultStatus
    {
        SUCCESS = 0,
        ERROR = 1
    };

    enum class EnvironmentDataUploadResultStatus
    {
        SUCCESS = 0,
        INVALID_VERSION = 1,
        ALREADY_EXECUTING_ANOTHER_UPLOAD = 2,
        ERROR_WHILE_UPDATING_DATABASE = 3
    };

    enum class ObjectiveType
    {
        TRACKING_TARGET_INFORMATION = 2
    };
}