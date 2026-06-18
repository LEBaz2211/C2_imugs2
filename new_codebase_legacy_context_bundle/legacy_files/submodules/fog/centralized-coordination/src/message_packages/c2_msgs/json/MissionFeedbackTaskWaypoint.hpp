#pragma once

#include <ctime>
#include <string>
#include <vector>

#include "include/picojson.h"
#include "include/JsonResult.h"
#include "include/Isotime.h"

#include "Enums.hpp"
#include "GPSCoordinate.hpp"


namespace c2_msgs::json
{
    class MissionFeedbackTaskWaypoint
    {
    public:
        GPSCoordinate Coordinates;
        std::optional<double> Orientation;
        double AverageSpeed;
        time_t Eta;
        std::string waypoint_id;

        // MissionFeedbackTaskWaypoint(const GPSCoordinate &position, const double orientation, const double averageSpeed, const Isotime eta) : Position(position), Orientation(orientation), AverageSpeed(averageSpeed), Eta(eta){};

        static JsonResult<MissionFeedbackTaskWaypoint> FromJson(picojson::object &obj)
        {
            if(obj.empty())
                return{"'waypoints' property is empty"};

            MissionFeedbackTaskWaypoint result;

            // Position
            if(obj["coordinates"].is<picojson::null>())
                return{"'coordinates' property is empty"};
            if(!obj["coordinates"].is<picojson::array>())
                return{"'coordinates' property is not defined as an array"};
            
            auto &positionJson = obj["coordinates"].get<picojson::array>();
            if(!positionJson[0].is<double>())
                return{"lat not defined as a number"};
            if(!positionJson[1].is<double>())
                return{"lng not defined as a number"};
            GPSCoordinate position(positionJson[0].get<double>(), positionJson[1].get<double>());
            result.Coordinates = position;

            // Orientation - Optional
            if(!obj["orientation"].is<picojson::null>())
            {
                if(!obj["orientation"].is<double>())
                    return{"'orientation' property is not defined as a number"}; 
                result.Orientation = obj["orientation"].get<double>();
            }

            // Average speed
            if(obj["average_speed"].is<picojson::null>())
                return{"'average_speed' property is empty"};
            if(!obj["average_speed"].is<double>())
                return{"'average_speed' property is not defined as a number"};
            result.AverageSpeed = obj["average_speed"].get<double>();

            // Eta - Estimation time of arrival
            if(obj["eta"].is<picojson::null>())
                return{"'eta' property is empty"};
            if(!obj["eta"].is<std::string>())
                return{"'eta' property is not defined as a string"};

            result.Eta = Isotime::FromIso8601(obj["eta"].get<std::string>());
            return{result};
        };

        picojson::object ToJson() const
        {
            picojson::array wptCoordinatesJson;
            wptCoordinatesJson.push_back(picojson::value(this->Coordinates.Lat));
            wptCoordinatesJson.push_back(picojson::value(this->Coordinates.Lng));

            picojson::object result;
            result["coordinates"] = picojson::value(wptCoordinatesJson);
            result["average_speed"] = picojson::value(this->AverageSpeed);
            result["eta"] = picojson::value(Isotime::ToIso8601(this->Eta));
            if(this->Orientation.has_value())
            {
                result["orientation"] = picojson::value(this->Orientation.value());
            }
            
            return result;
        };

        std::string ToJsonString() const
        {
            return picojson::value(this->ToJson()).serialize();
        };
    };
}