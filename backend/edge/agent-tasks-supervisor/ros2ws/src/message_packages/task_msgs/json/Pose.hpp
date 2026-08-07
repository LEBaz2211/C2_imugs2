#pragma once

#include <vector>

#include "include/picojson.h"
#include "include/JsonResult.h"

namespace task_msgs::json
{
        class Pose
        {
        public:
                double X;
                double Y;
                double Yaw;
                double Speed;
                double WaitTime;

                Pose();
                Pose(double x, double y, double yaw, double speed, double waittime) : X(x), Y(y), Yaw(yaw), Speed(speed),  WaitTime(waittime) {};

                static JsonResult<Pose> FromJson(picojson::object &obj)
                {
                        if (obj.empty())
                                return {"Pose is empty"};

                        if (!obj["x"].is<double>())
                                return {"x value is empty"};

                        if (!obj["y"].is<double>())
                                return {"y value is empty"};

                        if (!obj["yaw"].is<double>())
                                return {"yaw value is empty"};
                        
                        if (!obj["speed"].is<double>())
                                return {"speed value is empty"};

                        if (!obj["wait_time"].is<double>())
                                return {"wait_time value is empty"};

                        return {Pose(obj["x"].get<double>(), obj["y"].get<double>(), obj["yaw"].get<double>(), obj["speed"].get<double>(), obj["wait_time"].get<double>())};
                };

                picojson::object ToJson() const
                {
                        picojson::object result;
                        result["x"] = picojson::value(this->X);
                        result["y"] = picojson::value(this->Y);
                        result["yaw"] = picojson::value(this->Yaw);
                        result["speed"] = picojson::value(this->Speed);
                        result["wait_time"] = picojson::value(this->WaitTime);
                        return result;
                };
        };
}