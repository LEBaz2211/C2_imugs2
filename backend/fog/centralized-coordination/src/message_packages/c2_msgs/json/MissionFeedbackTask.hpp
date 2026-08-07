#pragma once

#include <ctime>
#include <string>
#include <vector>
#include <sstream>

#include "include/picojson.h"
#include "include/JsonResult.h"

#include "Enums.hpp"
#include "GPSCoordinate.hpp"
#include "MissionFeedbackTaskWaypoint.hpp"

namespace c2_msgs::json
{
    class MissionFeedbackTask
    {
    public:
        std::string VehicleId;
        std::string TaskId;
        std::optional<std::vector<MissionFeedbackTaskWaypoint>> Waypoints;
        std::optional<time_t> Est; // Estimated start time

        // MissionFeedbackTask(const std::string &VehicleId, const std::vector<MissionFeedbackTaskWaypoint> &waypoints = {}) : VehicleId(VehicleId), Waypoints(waypoints){};
        static JsonResult<MissionFeedbackTask> FromJson(picojson::object &obj)
        {
            if(obj.empty())
                return{"'tasks' property is empty"};

            MissionFeedbackTask result;

            // Vehicle id
            if(!obj["vehicle_id"].is<std::string>())
                    return{"'vehicle_id' property is not defined as a string"};
            result.VehicleId = obj["vehicle_id"].get<std::string>();

            // Waypoints - Optional
            if(!obj["waypoints"].is<picojson::null>())
            {
                if(!obj["waypoints"].is<picojson::array>())
                    return{"'waypoints' property is not defined as an array"};
                auto waypointsJson = obj["waypoints"].get<picojson::array>();
                std::vector<MissionFeedbackTaskWaypoint> waypoints;

                for (auto &&wptJson : waypointsJson)
                {
                    auto wpt = MissionFeedbackTaskWaypoint::FromJson(wptJson.get<picojson::object>());
                    if (!wpt.Success)
                        return {"error in parsing 'waypoint' from 'waypoints' property: " + wpt.Log};
                    waypoints.push_back(wpt.Result.value());
                }
                result.Waypoints = waypoints;
            }

            // Estimated start time - Optional
            if(!obj["est"].is<picojson::null>())
            {
                if(!obj["est"].is<std::string>())
                    return{"'estimated start time' property is not defined as a string"};
                
                result.Est = Isotime::FromIso8601(obj["est"].get<std::string>());
            }
            
            return {result};
        };

        picojson::object ToJson() const
        {
            picojson::object taskJson;
            taskJson["vehicle_id"] = picojson::value(this->VehicleId);

            if(this->Waypoints.has_value())
            {
                picojson::array waypointsJson;
                for (auto &&wpt : this->Waypoints.value())
                {
                    waypointsJson.push_back(picojson::value(wpt.ToJson()));
                }
                taskJson["waypoints"] = picojson::value(waypointsJson);
            }

            if(this->Est.has_value())
            {
                taskJson["est"] = picojson::value(Isotime::ToIso8601(this->Est.value()));
            }

            return {taskJson};
        };

        std::string ToJsonString() const
        {
            return picojson::value(this->ToJson()).serialize();
        };
    };
}