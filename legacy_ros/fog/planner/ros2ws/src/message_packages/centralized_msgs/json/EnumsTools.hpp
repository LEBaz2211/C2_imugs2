#ifndef ENUMSTOOL_HPP
#define ENUMSTOOL_HPP

#include "Enums.hpp"
#include <string>
#include <cstdio>

namespace centralized_msgs::json::enums
{
    class EnumsTools
    {
    public:

        static enums::MissionIssue MissionIssueToEnum(int issue)
        {
            enums::MissionIssue result;
            switch (issue)
            {
            case 0:
                result = enums::MissionIssue::NONE;
            case 10:
                result = enums::MissionIssue::MISSION_WARN_ID_ALREADY_USED;
            case 11:
                result = enums::MissionIssue::MISSION_WARN_UGV_UNAVAILABLE;
            case 12:
                result = enums::MissionIssue::MISSION_WARN_CONFIG_UNKNOWN_DATA;
            case 13:
                result = enums::MissionIssue::MISSION_WARN_STATUS_NOT_CHANGED;
            case 14:
                result = enums::MissionIssue::MISSION_WARN_DISCONNECTED_SWARM_PLANNER;
            case 15:
                result = enums::MissionIssue::MISSION_WARN_DISCONNECTED_SWARMING_EDGE;
            case 16:
                result = enums::MissionIssue::MISSION_WARN_DISCONNECTED_AUTONOMY;
            case 20:
                result = enums::MissionIssue::MISSION_FAILED_CONFIG_PARSING_UNSUCCESSFUL;
            case 21:
                result = enums::MissionIssue::MISSION_FAILED_CONFIG_MISSING_DATA;
            case 22:
                result = enums::MissionIssue::MISSION_FAILED_MISSION_COMPROMISED;
            case 23:
                result = enums::MissionIssue::MISSION_FAILED_DISCONNECTED_SWARM_PLANNER;
            case 24:
                result = enums::MissionIssue::MISSION_FAILED_DISCONNECTED_EDGE;
            case 25:
                result = enums::MissionIssue::MISSION_FAILED_DISCONNECTED_AUTONOMY;
            case 30:
                result = enums::MissionIssue::PLANNING_WARN_VEHICLES_MISMATCH;
            case 31:
                result = enums::MissionIssue::PLANNING_WARN_NOT_ENOUGH_COVERAGE;
            case 32:
                result = enums::MissionIssue::PLANNING_WARN_DATE_COMPROMISED;
            case 40:
                result = enums::MissionIssue::PLANNING_FAILED_NO_SOLUTION_FOUND;
            case 41:
                result = enums::MissionIssue::PLANNING_FAILED;
            default:
                printf("Error in MissionIssue enum, enum unknown");
            }
            return result;
        };

        static enums::MissionStatus MissionStatusEnum(int status)
        {
            enums::MissionStatus result;
            switch (status)
            {
            case 0:
                result = enums::MissionStatus::NONE;
            case 1:
                result = enums::MissionStatus::PLANNED;
            case 2:
                result = enums::MissionStatus::PLANNED_ALTERNATIVE;
            case 3:
                result = enums::MissionStatus::PLANNED_FAILED;
            case 4:
                result = enums::MissionStatus::ACCEPTED;
            case 5:
                result = enums::MissionStatus::STARTED;
            case 6:
                result = enums::MissionStatus::PAUSED;
            case 7:
                result = enums::MissionStatus::FAILED;
            case 8:
                result = enums::MissionStatus::STOPPED;
            case 9:
                result = enums::MissionStatus::DELETED;
            case 10:
                result = enums::MissionStatus::COMPLETED;
            default:
                printf("Error in 'MissionStatus', enum unknown");
            }
            return result;
        };

        static enums::MissionStatusRequest MissionStatusRequestToEnum(int status)
        {
            enums::MissionStatusRequest result;
            switch (status)
            {
            case 0:
                result = enums::MissionStatusRequest::INIT;
            case 1:
                result = enums::MissionStatusRequest::APPROVE;
            case 2:
                result = enums::MissionStatusRequest::START;
            case 3:
                result = enums::MissionStatusRequest::PAUSE;
            case 4:
                result = enums::MissionStatusRequest::STOP;
            case 5:
                result = enums::MissionStatusRequest::DELETE;
            default:
                printf("Error in 'MissionStatus', enum unknown");
            }
            return result;
        };

        static enums::Behavior BehaviorToEnum(int behavior)
        {
            enums::Behavior result;
            switch (behavior)
            {
            case 0:
                result = enums::Behavior::NAVIGATE;
            case 1:
                result = enums::Behavior::COVERAGE;
            default:
                printf("Error in 'Behavior', enum unknown");
            }
            return result;
        };

        static enums::VehicleFormation VehicleFormationEnum(int formation)
        {
            enums::VehicleFormation result;
            switch (formation)
            {
            case 0:
                result = enums::VehicleFormation::NONE;
                break;
            case 1:
                result = enums::VehicleFormation::COLUMN;
                break;
            case 2:
                result = enums::VehicleFormation::LINE;
                break;
            case 3:
                result = enums::VehicleFormation::WEDGE;
                break;
            case 4:
                result = enums::VehicleFormation::VEE;
                break;
            case 5:
                result = enums::VehicleFormation::LEFT_FLANK;
                break;
            case 6:
                result = enums::VehicleFormation::RIGHT_FLANK;
                break;
            default:
                printf("Error in 'VehicleFormation', enum unknown, setup default value: NONE");
                result = enums::VehicleFormation::NONE;
                break;
            }
            return result;
        };

        static enums::VehicleChanges VehicleChangeToEnum(int action)
        {
            enums::VehicleChanges result;
            switch (action)
            {
            case 0:
                result = enums::VehicleChanges::ADD;
            case 1:
                result = enums::VehicleChanges::REMOVE;
            default:
                printf("Error in 'VehicleChange', enum unknown");
            }
            return result;
        };

        static enums::LogType LogTypeToEnum(int type)
        {
            enums::LogType result;
            switch (type)
            {
            case 0:
                result = enums::LogType::INFO;
            case 1:
                result = enums::LogType::WARNING;
            case 2:
                result = enums::LogType::ERROR;
            case 3:
                result = enums::LogType::ERROR;
            case 4:
                result = enums::LogType::FATAL;
            default:
                printf("Error in 'LogType', enum unknown");
            }
            return result;
        };

        static enums::EnvironmentDataResultStatus EnvResultStatusToEnum(int status)
        {
            enums::EnvironmentDataResultStatus result;
            switch (status)
            {
            case 0:
                result = enums::EnvironmentDataResultStatus::SUCCESS;
            case 1:
                result = enums::EnvironmentDataResultStatus::ERROR;
            default:
                printf("Error in 'environment_data_result_status', enum unknown");
            }
            return result;
        };

        static enums::EnvironmentDataUploadResultStatus EnvUploadStatusToEnum(int status)
        {
            enums::EnvironmentDataUploadResultStatus result;
            switch (status)
            {
            case 0:
                result = enums::EnvironmentDataUploadResultStatus::SUCCESS;
            case 1:
                result = enums::EnvironmentDataUploadResultStatus::INVALID_VERSION;
            case 2:
                result = enums::EnvironmentDataUploadResultStatus::ALREADY_EXECUTING_ANOTHER_UPLOAD;
            case 3:
                result = enums::EnvironmentDataUploadResultStatus::ERROR_WHILE_UPDATING_DATABASE;
            default:
                printf("Error in 'environment_data_upload_result_status', enum unknown");
            }
            return result;
        };
    };
}


#endif