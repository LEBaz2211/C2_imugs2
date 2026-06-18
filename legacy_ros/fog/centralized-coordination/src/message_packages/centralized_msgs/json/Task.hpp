#pragma once

#include <vector>
#include <string>

#include "include/picojson.h"
#include "include/JsonResult.h"
#include "include/Isotime.h"

#include "Waypoint.hpp"

namespace centralized_msgs::json
{
        class Task
        {
        public:
                std::string AgentId;
                time_t Std;
                std::vector<Waypoint> Waypoints;

                Task();
                Task(std::string agentId, time_t std, std::vector<Waypoint> &waypoints) : AgentId(agentId), Std(std), Waypoints(waypoints){};

                static JsonResult<Task> FromJson(picojson::object &obj)
                {
                        if (obj.empty())
                                return {"Task is empty"};

                        std::vector<Waypoint> waypoints;
                        if (obj["waypoints"].is<picojson::array>())
                        {
                                auto waypointsJson = obj["waypoints"].get<picojson::array>();
                                for (auto &&waypointJson : waypointsJson)
                                {
                                        if (waypointJson.is<picojson::object>())
                                        {
                                                auto waypoint = Waypoint::FromJson(waypointJson.get<picojson::object>());
                                                if (!waypoint.Success)
                                                        return {"Unable to parse waypoint: " + waypoint.Log};

                                                waypoints.push_back(waypoint.Result.value());
                                        }
                                }
                        }

                        if (!obj["agent_id"].is<std::string>())
                                return {"AgentId is empty"};

                        if (!obj["std"].is<std::string>())
                                return {"Std is empty"};

                        auto std = Isotime::FromIso8601(obj["std"].get<std::string>());

                        return {Task(obj["agent_id"].get<std::string>(), std, waypoints)};
                };

                picojson::object ToJson() const
                {
                        picojson::object result;
                        picojson::array waypointsJson;
                        for (auto &&wpt : this->Waypoints)
                                waypointsJson.push_back(picojson::value(wpt.ToJson()));

                        result["agent_id"] = picojson::value(this->AgentId);
                        result["waypoints"] = picojson::value(waypointsJson);
                        result["std"] = picojson::value(Isotime::ToIso8601(this->Std));
                        return result;
                };
        };
}