#pragma once

#include <vector>
#include <string>

#include "include/picojson.h"
#include "include/JsonResult.h"
#include "include/Isotime.h"

namespace centralized_msgs::json
{
        class Waypoint
        {
        public:
                double X;
                double Y;
                double Yaw;
                double Speed;
                time_t Eta;
                double WaitTime;
                std::map<std::string, std::string> Tags = {};

                Waypoint();
                Waypoint(double x, double y, double yaw, double speed, time_t eta, double waittime) : X(x), Y(y), Yaw(yaw), Speed(speed), Eta(eta), WaitTime(waittime) {};

                static JsonResult<Waypoint> FromJson(picojson::object &obj)
                {
                        if (obj.empty())
                                return {"Waypoint is empty"};

                        if (!obj["position"].is<picojson::array>())
                                return {"Position is empty"};

                        auto pos = obj["position"].get<picojson::array>();
                        if (pos.size() < 2)
                                return {"Position array must contain x & y"};

                        if (!obj["speed"].is<double>())
                                return {"Speed is empty"};

                        if (!obj["yaw"].is<double>())
                                return {"Yaw is empty"};

                        if (!obj["eta"].is<std::string>())
                                return {"Eta is empty"};
                        
                        if (!obj["wait_time"].is<double>())
                                return {"wait_time is empty"};


                        auto eta = Isotime::FromIso8601(obj["eta"].get<std::string>());
                        auto result = Waypoint(pos[0].get<double>(), pos[1].get<double>(), obj["yaw"].get<double>(), obj["speed"].get<double>(), eta, obj["wait_time"].get<double>());

                        if (obj["tags"].is<picojson::object>())
                        {
                                auto tagsJson = obj["tags"].get<picojson::object>();
                                for (auto &&taskJson : tagsJson)
                                {
                                        result.Tags[taskJson.first] = taskJson.second.get<std::string>();
                                }
                        }

                        return {result};
                };

                picojson::object ToJson() const
                {
                        picojson::object result;
                        picojson::array posJson;
                        posJson.push_back(picojson::value(this->X));
                        posJson.push_back(picojson::value(this->Y));

                        result["position"] = picojson::value(posJson);
                        result["speed"] = picojson::value(this->Speed);
                        result["yaw"] = picojson::value(this->Yaw);
                        result["eta"] = picojson::value(Isotime::ToIso8601(this->Eta));
                        result["wait_time"] = picojson::value(this->WaitTime);

                        std::map<std::string, picojson::value> tags = {};
                        for (auto &&tag : this->Tags)
                        {
                                tags[tag.first] = picojson::value(tag.second);
                        }

                        result["tags"] = picojson::value(picojson::object(tags));
                        return result;
                };
        };
}