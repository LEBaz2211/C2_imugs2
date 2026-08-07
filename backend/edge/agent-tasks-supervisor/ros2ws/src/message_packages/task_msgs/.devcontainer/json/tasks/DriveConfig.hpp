#pragma once

#include <vector>

#include "../include/picojson.h"
#include "../include/JsonResult.h"

#include "../Pose.hpp"

namespace task_msgs::json::tasks
{
        class DriveConfig
        {
        public:
                std::vector<Pose> Waypoints;

                DriveConfig(){};

                static JsonResult<DriveConfig> FromJson(picojson::object &obj)
                {
                        if (obj.empty())
                                return {"Config is empty"};

                        if (!obj["waypoints"].is<picojson::array>())
                                return {"Waypoints property is empty!"};

                        DriveConfig config;
                        for (auto &wptJson : obj["waypoints"].get<picojson::array>())
                        {
                                auto wpt = Pose::FromJson(wptJson.get<picojson::object>());
                                if (!wpt.Success)
                                        return {"error in parsing object from 'waypoints' list: " + wpt.Log};

                                config.Waypoints.push_back(wpt.Result.value());
                        }

                        return {config};
                };

                static JsonResult<DriveConfig> FromJsonString(const std::string &str)
                {
                        picojson::value configJson;
                        std::string errConfigParsing = picojson::parse(configJson, str);
                        if (!errConfigParsing.empty())
                                return {"Parsing of json config failed: " + errConfigParsing};

                        return FromJson(configJson.get<picojson::object>());
                };

                picojson::object ToJson() const
                {
                        picojson::object result;
                        picojson::array wptsJson;
                        for (auto &&wpt : this->Waypoints)
                                wptsJson.push_back(picojson::value(wpt.ToJson()));

                        result["waypoints"] = picojson::value(wptsJson);
                        return result;
                };

                std::string ToJsonString() const
                {
                        return picojson::value(this->ToJson()).serialize();
                };
        };
}