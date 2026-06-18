#pragma once

#include "include/picojson.h"
#include "include/JsonResult.h"

namespace centralized_msgs::json
{
        class GPSCoordinate
        {
        public:
                double Lat;
                double Lng;

                GPSCoordinate(){};
                GPSCoordinate(double lat, double lng) : Lat(lat), Lng(lng){};

                picojson::object ToJson() const
                {
                        picojson::object result;
                        result["lat"] = picojson::value(this->Lat);
                        result["lng"] = picojson::value(this->Lng);
                        return result;
                }
        };
}