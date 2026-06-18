#pragma once

#include <ctime>
#include <string>
#include <vector>

#include "include/picojson.h"
#include "include/JsonResult.h"


#include "Enums.hpp"
#include "MissionFeedbackTask.hpp"
#include "GPSCoordinate.hpp"
#include "FeedbackObjective.hpp"

namespace centralized_msgs::json
{
    class MissionFeedback
    {
    public:
        std::string MissionId;
        enums::Behavior Behavior;
        enums::MissionStatus Status;
        enums::MissionStatusRequest RequestedStatus;
        std::optional<enums::MissionIssue> Issue;
        std::optional<std::vector<MissionFeedbackTask>> Tasks;
        time_t Date;
        std::optional<std::vector<FeedbackObjective>> Objective;

        // MissionFeedback(enums::Behavior behavior, enums::MissionStatus status, enums::MissionStatusRequest requestedStatus, std::optional<enums::MissionIssue> issue, std::optional<std::vector<MissionFeedbackTask>> &tasks = {}, time_t date = std::time(NULL))
            // : Behavior(behavior), Status(status), RequestedStatus(requestedStatus), Issue(issue), Tasks(tasks), Date(date){};

        static JsonResult<MissionFeedback> FromJsonString(const std::string &str)
        {
            picojson::value feedbackJson;
            std::string errFeedbackParsing = picojson::parse(feedbackJson, str);
            if (!errFeedbackParsing.empty())
                return {"Parsing of json config failed"};

            return FromJson(feedbackJson.get<picojson::object>());
        };
        static JsonResult<MissionFeedback> FromJson(picojson::object &obj)
        {
            if (obj.empty())
                return {"Feedback is empty"};

            MissionFeedback result;

            //  MissionId
            if (!obj["mission_id"].is<std::string>())
                return{"'mission_id' property is not defined as a string"};
            result.MissionId = obj["mission_id"].get<std::string>();

            // Behavior
            if (!obj["behavior"].is<double>())
                return{"'behavior' property is not defined as a number"};
            result.Behavior = (enums::Behavior)obj["behavior"].get<double>();

            // Status
            if (!obj["status"].is<double>())
                return{"'status' property is not defined as a number"};
            result.Status = (enums::MissionStatus)obj["status"].get<double>();

            // Requested_status
            if (!obj["requested_status"].is<double>())
                return{"'requested_status' property is not defined as a number"};
            result.RequestedStatus = (enums::MissionStatusRequest)obj["requested_status"].get<double>();

            // Date - Date of feedback as ISO in UTC
            if(!obj["date"].is<std::string>())
                return{"'date'property is not defined as a string"};
            result.Date = Isotime::FromIso8601(obj["date"].get<std::string>());

            // Issue - Optional
            if (!obj["issue"].is<picojson::null>())
            {
                if (!obj["issue"].is<double>())
                    return{"'issue' property is not defined as a number"};
                result.Issue = (enums::MissionIssue)obj["issue"].get<double>();
            }
            
            // Tasks - Optional
            std::vector<MissionFeedbackTask> tasks;

            if (obj["tasks"].is<picojson::array>())
            {
                auto tasksJson = obj["tasks"].get<picojson::array>();
                for (auto &&taskJson : tasksJson)
                {
                    auto task = MissionFeedbackTask::FromJson(taskJson.get<picojson::object>());
                    if (!task.Success)
                        return {"error in 'tasks' property: " + task.Log};
                    tasks.push_back(task.Result.value());
                }
                result.Tasks = tasks;
            }

            
            if(!obj["objective"].is<picojson::null>())
            {
                std::vector<FeedbackObjective> objectives;
                if(!obj["objective"].is<picojson::array>())
                    return{"'objective' property is not defined as an array"};
                
                std::vector<FeedbackObjective> tracked_obj;
                for(auto &object : obj["objective"].get<picojson::array>())
                {
                    if(!object.is<picojson::object>())
                        return{"'objective' property does not contain object"};

                    auto res = FeedbackObjective::FromJson(object.get<picojson::object>());
                    if(!res.Success)
                        return{"Error in Objective property: " + res.Log};
                    tracked_obj.push_back(res.Result.value());
                }
                result.Objective = tracked_obj;
            }
            
            

            return {result};
        };

        std::string ToJsonString() const
        {
            return picojson::value(this->ToJson()).serialize();
        };

        picojson::object ToJson() const
        {
            picojson::object result;

            result["mission_id"] = picojson::value(this->MissionId);
            result["behavior"] = picojson::value(static_cast<double>(this->Behavior));
            result["status"] = picojson::value(static_cast<double>(this->Status));
            result["requested_status"] = picojson::value(static_cast<double>(this->RequestedStatus));
            result["date"] = picojson::value(Isotime::ToIso8601(this->Date));
            if(this->Issue.has_value())
            {
                result["issue"] = picojson::value((double)this->Issue.value());
            }

            if (this->Tasks.has_value())
            {
                if (!this->Tasks.value().empty())
                {
                    picojson::array tasksJson;
                    for (auto &&task : this->Tasks.value())
                    {
                        tasksJson.push_back(picojson::value(task.ToJson()));
                    }
                    result["tasks"] = picojson::value(tasksJson);
                }
            }

            return result;
        };
    };
}
