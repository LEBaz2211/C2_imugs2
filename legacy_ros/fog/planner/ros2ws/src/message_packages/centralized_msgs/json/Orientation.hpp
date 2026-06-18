#pragma once

#include "include/picojson.h"
#include "include/JsonResult.h"

namespace centralized_msgs::json
{
    class Orientation
    {
    public:
        double Yaw;
        double Pitch;
        double Roll;
        
        Orientation(){};
        Orientation(double yaw, double pitch, double roll): Yaw(yaw), Pitch(pitch), Roll(roll){};

        // From Orientation object to Json
        picojson::object ToJson() const
        {
            picojson::object result;
            
            result["pitch"] = picojson::value(this->Pitch);
            result["roll"] = picojson::value(this->Roll);
            result["yaw"] = picojson::value(this->Yaw);

            return result;
        }
    };
}