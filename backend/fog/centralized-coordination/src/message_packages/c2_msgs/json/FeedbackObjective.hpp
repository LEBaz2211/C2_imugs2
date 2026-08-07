#pragma once

#include <string>
#include <vector>

#include "include/picojson.h"
#include "include/JsonResult.h"

#include "GPSCoordinate.hpp"
#include "Enums.hpp"

namespace c2_msgs::json
{

    class Location
    {
    public:
        std::vector<GPSCoordinate> Coordinates;
        std::vector<double> Velocity;
        time_t TimeStamp;

        static JsonResult<Location> FromJson(picojson::object &obj)
        {
            if(obj.empty())
                return{"'location' property is empty"};

            Location result;

            // Coordinates
            if(!obj["coordinates"].is<picojson::array>())
                return{"'coordinate'property is not define as an array"};

            std::vector<GPSCoordinate> coordinates_vec;
            
            for( auto &coord : obj["coordinates"].get<picojson::array>())
            {
                if (!coord.is<picojson::array>())
                    return{"Some points are not included in an array"};

                auto &coord_pt = coord.get<picojson::array>();

                if(coord_pt.size()>(size_t)2 || coord_pt.size()<(size_t)2)
                    return{"Point coordinates are defined with a wrong size"};
                if(!coord_pt[0].is<double>() || !coord_pt[1].is<double>())
                    return{"Point coordinates are defined with a wrong size"};

                auto gps = GPSCoordinate(coord_pt[0].get<double>(), coord_pt[1].get<double>());
                
                coordinates_vec.push_back(gps);
            }
            result.Coordinates = coordinates_vec;

            // Velocity
            if(!obj["velocity"].is<picojson::array>())
                return{"'velocity'property is not define as an array"};
            
            std::vector<double> velocity;
            for(auto &vel : obj["velocity"].get<picojson::array>())
            {
                if(!vel.is<double>())
                    return{"'velocity' property is not define as a number"};
                velocity.push_back(vel.get<double>());
            }
            result.Velocity = velocity;

            // Date

            if(!obj["timestamp"].is<std::string>())
                return{"'timestamp' is not define as a string"};
            result.TimeStamp = Isotime::FromIso8601(obj["timestamp"].get<std::string>());

            return{result};
        };

        picojson::object ToJson() const
        {
            picojson::object result;

            for(auto coord : this->Coordinates)
            {
                result["coordinates"] = picojson::value(coord.ToJson());
            }
            
            for(auto vel : this->Velocity)
            {
                result["velocity"] = picojson::value(vel);
            }
            
            result["timestamp"] = picojson::value(Isotime::ToIso8601(this->TimeStamp));

            return {result};
        };

        std::string ToJsonString() const
        {
            return picojson::value(this->ToJson()).serialize();
        };
    };
    
    
    class FeedbackObjective
    {
    public:
        std::string FeatureId;
        enums::ObjectiveType Type;
        std::optional<std::vector<Location>> ObjectLocations;

        static JsonResult<FeedbackObjective> FromJson(picojson::object &obj)
        {
            
            if(obj.empty())
                return{"'Objective' property empty"};

            FeedbackObjective result;
            
            // Feature Id
            if(obj["feature_id"].is<picojson::null>())
                return{"feature_id does not have values"};
            if(!obj["feature_id"].is<std::string>())
                return{"'feature_id' property is not defined as a string"};
            result.FeatureId = obj["feature_id"].get<std::string>();

            // Type
            if(obj["type"].is<picojson::null>())
                return{"'type' does not have values"};
            if(!obj["type"].is<double>())
                return{"'type' property is not defined as a number"};
            result.Type = (enums::ObjectiveType)obj["type"].get<double>();

            // Object location - Optional - array of objects
            if(!obj["location"].is<picojson::null>())
            {
                if(!obj["location"].is<picojson::array>())
                    return{"'location' property is not defined as an array"};

                std::vector<Location> locations;
                for(auto &loc : obj["location"].get<picojson::array>())
                {
                    auto local = Location::FromJson(loc.get<picojson::object>());
                    if(!local.Success)
                        return{"Error in 'Location' property: " + local.Log};
                    locations.push_back(local.Result.value());
                }
                result.ObjectLocations = locations;
            }

            return{result};
        };

        picojson::object ToJson() const
        {
            picojson::object result;

            return result;
        };

        std::string ToJsonString() const
        {
            return picojson::value(this->ToJson()).serialize();
        };
    };
    
}