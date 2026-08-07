#pragma once
#include <string>
#include <map>
#include <vector>
#include <optional>
#include <ctime>
#include <string>
#include <cctype>
#include <locale>

#include "include/picojson.h"
#include "include/JsonResult.h"
#include "include/Isotime.h"
#include "Enums.hpp"
#include "EnumsTools.hpp"

#include "GPSCoordinate.hpp"
#include "Orientation.hpp"

namespace c2_msgs::json
{
    class MissionGeometry
    {
    public:
        std::optional<std::vector<GPSCoordinate>> Coordinates;
        std::optional<std::string> FeatureId;
        std::optional<std::string> GeometryType;

        // Parse from JSON object
        static JsonResult<MissionGeometry> FromJson(picojson::object &obj)
        {
            MissionGeometry result;
            if (obj.empty())
                return {"Geometry is empty"};

            // If feature_id exists, use it and skip geometry data
            if (obj.count("feature_id") > 0 && obj["feature_id"].is<std::string>())
            {
                result.FeatureId = obj["feature_id"].get<std::string>();
            }
            else
            {
                // Check if "geometry" object exists
                if (obj.count("geometry") == 0 || !obj["geometry"].is<picojson::object>())
                    return {"Missing 'geometry' object in JSON!"};

                picojson::object geometryObj = obj["geometry"].get<picojson::object>();

                // Extract Geometry Type (Optional, default to "MultiPoint")
                if (geometryObj.count("geometry_type") > 0 && geometryObj["geometry_type"].is<std::string>())
                    result.GeometryType = geometryObj["geometry_type"].get<std::string>();
                else
                    result.GeometryType = "MultiPoint";

                // Extract Coordinates
                if (!geometryObj["coordinates"].is<picojson::array>())
                    return {"Coordinates property is missing or not an array!"};

                picojson::array coordArray = geometryObj["coordinates"].get<picojson::array>();
                std::vector<GPSCoordinate> coordinates;

                if (!coordArray.empty() && coordArray[0].is<picojson::array>())
                {
                    for (const auto &c : coordArray)
                    {
                        if (!c.is<picojson::array>())
                            return {"Some coordinates are not arrays!"};

                        auto &cc = c.get<picojson::array>();
                        if (cc.size() < 2)
                            return {"Some coordinates contain fewer than 2 values!"};

                        if (!cc[0].is<double>() || !cc[1].is<double>())
                            return {"Longitude or latitude is not a double!"};

                        coordinates.push_back({cc[0].get<double>(), cc[1].get<double>()});
                    }
                }
                else if (coordArray.size() >= 2 && coordArray[0].is<double>())
                {
                    coordinates.push_back({coordArray[0].get<double>(), coordArray[1].get<double>()});
                }

                result.Coordinates = coordinates;
            }
            return {result};
        }


        // Convert to JSON object
        picojson::object ToJson() const
        {
            picojson::object result;

            if (FeatureId.has_value())
            {
                result["feature_id"] = picojson::value(FeatureId.value());
            }
            else
            {
                picojson::object geometryObj;  // Create geometry object

                geometryObj["geometry_type"] = picojson::value(GeometryType.value());

                picojson::array coordinatesJson;
                for (const auto &coord : Coordinates.value())
                {
                    picojson::array coordinateJson;
                    coordinateJson.push_back(picojson::value(coord.Lat));
                    coordinateJson.push_back(picojson::value(coord.Lng));
                    coordinatesJson.push_back(picojson::value(coordinateJson));
                }
                geometryObj["coordinates"] = picojson::value(coordinatesJson);

                result["geometry"] = picojson::value(geometryObj);  // Embed in "geometry" object
            }

            return result;
        }


        // Convert to JSON string
        std::string ToJsonString() const
        {
            return picojson::value(this->ToJson()).serialize();
        }
    };


    class MissionTime // is a double can be cast in long?
    {
    public:
        bool IsNull = true;
        time_t Latest;
        time_t Target;
        time_t Earliest;

        // From json to data structure
        static JsonResult<MissionTime> FromJson(picojson::object &obj)
        {
            MissionTime result;
            std::string latest_str, target_str, earliest_str;

            if (obj.empty())
                return {"The mission time property is empty"};

            // latest time property
            if (obj["latest"].is<picojson::null>())
                return {"latest time property is empty"};
            if (!obj["latest"].is<std::string>())
                return {"'latest' property is not define as ISO8601"};
            result.Latest = Isotime::FromIso8601(obj["latest"].get<std::string>());

            // target time property
            if (obj["target"].is<picojson::null>())
                return {"target time property is empty"};
            if (!obj["target"].is<std::string>())
                return {"'target' property is not define as ISO8601"};
            result.Target = Isotime::FromIso8601(obj["target"].get<std::string>());

            // earliest time property
            if (obj["earliest"].is<picojson::null>())
                return {"earliest time property is empty"};
            if (!obj["earliest"].is<std::string>())
                return {"'earliest' property is not define as ISO8601"};
            result.Earliest = Isotime::FromIso8601(obj["earliest"].get<std::string>());

            result.IsNull = false;

            return {result};
        };

        // From data structure to json
        picojson::object ToJson() const
        {
            picojson::object result;
            result["latest"] = picojson::value(Isotime::ToIso8601(this->Latest));
            result["target"] = picojson::value(Isotime::ToIso8601(this->Target));
            result["earliest"] = picojson::value(Isotime::ToIso8601(this->Earliest));

            return {result};
        };

        std::string ToJsonString() const
        {
            return picojson::value(this->ToJson()).serialize();
        };
    };

    class VehicleOrientationOrigin
    {
    public:
        std::optional<std::string> FeatureId;
        std::optional<std::string> GeometryType;
        std::optional<Orientation> Coordinates;

        // From Json to cpp objects
        static JsonResult<VehicleOrientationOrigin> FromJson(picojson::object &obj)
        {
            VehicleOrientationOrigin result;
            if (obj.empty())
                return {"Error in 'vehicle_orientation_origin' property is empty"};

            // feature_id
            if (!obj["feature_id"].is<picojson::null>())
            {
                auto feature_id = obj["feature_id"];
                if (!feature_id.is<std::string>())
                    return {"'feature_id property is not defined as a string"};
                result.FeatureId = feature_id.get<std::string>();
            }
            else
            {
                // Geometry_type
                if (obj["geometry_type"].is<picojson::null>())
                    return {"'geometry_type property is empty"};

                if (obj["geometry_type"].is<std::string>())
                    return {"'geometry_type' is not defined as a string"};
                result.GeometryType = obj["geometry_type"].get<std::string>();

                // Coordinates
                if (!obj["coordinates"].is<picojson::null>())
                {
                    if (!obj["coodinates"].is<picojson::array>())
                        return {"'coordinates is not define as an array"};
                    auto ori = obj["coordinates"].get<picojson::array>();
                    std::vector<double> tmp;
                    tmp.resize(3);
                    if (ori.size() < 3 || ori.size() > 3)
                        return {"'coordinates' property does not match orientation size"};
                    for (auto &&c : ori)
                    {
                        tmp.push_back(c.get<double>());
                    }
                    Orientation orientation(tmp.at(0), tmp.at(1), tmp.at(2));

                    result.Coordinates = orientation;
                }
            }
            return {result};
        };

        // From cpp objects to Json
        picojson::object ToJson() const
        {
            picojson::object result;
            std::string err;
            // Feature_id
            if (this->FeatureId.has_value())
            {
                picojson::value feature_id;
                err = picojson::parse(feature_id, this->FeatureId.value());
                if (!err.empty())
                    std::cerr << "Error while parsing feature_id: " << err << std::endl;
                result["feature_id"] = feature_id;
            }
            // Geometry_type
            else
            {
                // picojson::value geometry_type;
                // err = picojson::parse(geometry_type, this->GeometryType.value());
                // if (!err.empty())
                //     std::cerr << "Error while parsing geometry_type property: " << err << std::endl;

                result["geometry_type"] = picojson::value(this->GeometryType.value());

                // Coordinates
                picojson::value coordinates;
                coordinates = picojson::value(this->Coordinates->ToJson());
                if (!coordinates.is<picojson::object>())
                    std::cerr << "Error parsing orientation as an object" << std::endl;
                result["coordinates"] = coordinates;
            }
            return result;
        };

        std::string ToJsonString() const
        {
            return picojson::value(this->ToJson()).serialize();
        };
    };

    class MissionStart
    {
    public:
        MissionGeometry Geometry;
        std::optional<double> ToleranceDistance;
        std::optional<json::enums::VehicleFormation> VehicleFormation;
        std::optional<double> VehicleFormationDistance;
        std::optional<std::vector<double>> VehicleOrientation;
        std::optional<bool> MaximizeCoverage;
        std::optional<MissionTime> StartTime;

        static JsonResult<MissionStart> FromJson(picojson::object &obj)
        {
            MissionStart result;

            if (obj.empty())
                return {"start property is empty"};

            // Geometry
            if (!obj["geometry"].is<picojson::object>())
                return {"geometry property is empty!"};

            auto geometry = MissionGeometry::FromJson(obj["geometry"].get<picojson::object>());
            if (!geometry.Success)
                return {"error in 'start.geometry' property: " + geometry.Log};

            result.Geometry = geometry.Result.value();

            // Tolerance distance
            if (!obj["tolerance_distance"].is<picojson::null>()) // optional parameter
            {
                if (!obj["tolerance_distance"].is<double>())
                    return {"'tolerance_distance'property is not define as a number"};
                result.ToleranceDistance = obj["tolerance_distance"].get<double>();
            }

            // Vehicle formation
            if (!obj["vehicle_formation"].is<picojson::null>()) // optional parameter
            {
                if (!obj["vehicle_formation"].is<double>())
                    return {"'vehicle_formation'property is not defined as a number"};
                result.VehicleFormation = c2_msgs::json::enums::EnumsTools::VehicleFormationEnum(uint8_t(obj["vehicle_formation"].get<double>()));
            }

            // Vehicle formation distance
            if (!obj["vehicle_formation_distances"].is<picojson::null>()) // optional parameter
            {
                if (!obj["vehicle_formation_distances"].is<double>())
                    return {"'vehicle_formation_distances' property is not define as a number"};
                result.VehicleFormationDistance = obj["vehicle_formation_distances"].get<double>();
            }

            // vehicle orientation - array of three number
            if (!obj["vehicle_orientation"].is<picojson::null>()) // optional parameter
            {
                if (!obj["vehicle_orientation"].is<picojson::array>())
                    return {"'vehicle_orientation' property is not an array"};

                std::vector<double> orientation_array;
                // auto size = obj["vehicle_orientation"].get<picojson::array>().size();
                for (auto &c : obj["vehicle_orientation"].get<picojson::array>())
                {
                    if (!c.is<double>())
                        return {"in 'vehicle_orientation' property, some orientations are not numbers"};
                    orientation_array.push_back({c.get<double>()});
                }
                result.VehicleOrientation = orientation_array;
            }

            // Maximized coverage
            if (!obj["maximize_coverage"].is<picojson::null>())
            {
                auto maximize_coverage = obj["maximize_coverage"];
                if (!maximize_coverage.is<bool>())
                    return {"'maximum_coverage' property in not a boolean"};
                result.MaximizeCoverage = maximize_coverage.get<bool>();
            }

            // Start time
            if (!obj["start_time"].is<picojson::null>())
            {
                auto start_time = obj["start_time"];
                if (!start_time.is<picojson::object>())
                    return {"'start_time' property is not an object"};
                auto time_result = MissionTime::FromJson(start_time.get<picojson::object>());
                if (!time_result.Success)
                    return {"Error in 'time' property: " + time_result.Log};
                result.StartTime = time_result.Result;
            }
            return result;
        };

        picojson::object ToJson() const
        {
            picojson::object result;
            std::string err;

            // Geometry
            result["geometry"] = picojson::value(this->Geometry.ToJson());

            if (this->ToleranceDistance.has_value())
            {
                result["tolerance_distance"] = picojson::value(this->ToleranceDistance.value());
            }
            if (this->VehicleFormation.has_value())
            {
                result["vehiculeFormation"] = picojson::value(static_cast<double>(this->VehicleFormation.value()));
            }
            if (this->VehicleFormationDistance.has_value())
            {
                result["vehicle_formation_distance"] = picojson::value(this->VehicleFormationDistance.value());
            }
            if (this->VehicleOrientation.has_value())
            {
                picojson::array orientation_json;
                for (auto &ori : this->VehicleOrientation.value())
                {
                    orientation_json.push_back(picojson::value(ori));
                }
                result["vehicle_orientation"] = picojson::value(orientation_json);
            }
            if (this->MaximizeCoverage.has_value())
            {
                result["maximize_coverage"] = picojson::value(this->MaximizeCoverage.value());
            }

            if (this->StartTime.has_value())
            {
                result["start_time"] = picojson::value(this->StartTime->ToJson());
            }

            return {result};
        };

        std::string ToJsonString() const
        {
            return picojson::value(this->ToJson()).serialize();
        };
    };

    class MissionObjective
    {
    public:
        std::vector<MissionGeometry> Geometries;
        MissionTime ArrivalTime;
        std::optional<double> MinimumDistance;
        std::optional<double> MaximumDistance;
        std::optional<json::enums::VehicleFormation> VehicleFormation;
        std::optional<double> VehicleFormationDistance;
        std::optional<std::vector<double>> VehicleOrientation;
        std::optional<VehicleOrientationOrigin> VehicleOrientationOri;
        std::optional<bool> VehicleOrder;
        std::optional<MissionGeometry> LineOfSight;
        std::optional<bool> LineOfSightPropagation;
        std::optional<bool> MaximizeCoverage;
        std::optional<std::vector<double>> MaximizeCoverageDistances;

        static JsonResult<MissionObjective> FromJson(picojson::object &obj)
        {
            MissionObjective result;
            if (obj.empty())
                return {"Objective config property is empty"};

            // Parse Geometries
            if (!obj["geometries"].is<picojson::array>())
                return {"geometries property is missing or not an array!"};

            picojson::array geometriesArray = obj["geometries"].get<picojson::array>();
            for (auto &geometryObj : geometriesArray)
            {
                if (!geometryObj.is<picojson::object>())
                    return {"Some elements in 'geometries' are not objects!"};

                auto geometry = MissionGeometry::FromJson(geometryObj.get<picojson::object>());
                if (!geometry.Success)
                    return {"Error in 'geometries' property: " + geometry.Log};

                result.Geometries.push_back(geometry.Result.value());
            }

            // Minimum distance - Optional
            if (!obj["minimum_distance"].is<picojson::null>())
            {
                if (!obj["minimum_distance"].is<double>())
                    return {"'minimum_distance' property not defined as a double"};
                result.MinimumDistance.value() = obj["minimum_distance"].get<double>();
            }

            // Max distance - Optional
            if (!obj["maximum_distance"].is<picojson::null>())
            {
                if (!obj["maximum_distance"].is<double>())
                    return {"'maximum_distance' property not defined as a double"};
                result.MaximumDistance.value() = obj["maximum_distance"].get<double>();
            }

            // Vehicle formation - Optional
            if (!obj["vehicle_formation"].is<picojson::null>())
            {
                if (!obj["vehicle_formation"].is<double>())
                    return {"'vehicle_formation' property not defined as a double"};
                result.VehicleFormation = c2_msgs::json::enums::EnumsTools::VehicleFormationEnum(uint8_t(obj["vehicle_formation"].get<double>()));
            }

            // Vehicle_formation_distance - Optional
            if (!obj["vehicle_formation_distance"].is<picojson::null>())
            {
                if (!obj["vehicle_formation_distance"].is<double>())
                    return {"'vehicle_formation_distance' property not defined as a double"};
                result.VehicleFormationDistance.value() = obj["vehicle_formation_distance"].get<double>();
            }

            // vehicle orientation - array of three number
            if (!obj["vehicle_orientation"].is<picojson::null>()) // optional parameter
            {
                if (!obj["vehicle_orientation"].is<picojson::array>())
                    return {"'vehicle_orientation' property is not an array"};

                std::vector<double> orientation_array;
                // auto size = obj["vehicle_orientation"].get<picojson::array>().size();
                for (auto &c : obj["vehicle_orientation"].get<picojson::array>())
                {
                    if (!c.is<double>())
                        return {"in 'vehicle_orientation' property, some orientations are not numbers"};
                    orientation_array.push_back({c.get<double>()});
                }
                result.VehicleOrientation = orientation_array;
            }

            // Vehicle orientation_origin - Optional
            if (!obj["vehicle_orientation_origin"].is<picojson::null>())
            {
                if (!obj["vehicle_orientation_origin"].is<picojson::object>())
                    return {"'vehicle_orientation_origin' property is not define as an object"};
                auto vehicle_orientation_origin = VehicleOrientationOrigin::FromJson(obj["vehicle_orientation_origin"].get<picojson::object>());
                result.VehicleOrientationOri = vehicle_orientation_origin.Result.value();
            }

            // Vehicle order - Optional
            if (!obj["vehicle_order"].is<picojson::null>())
            {
                if (!obj["vehicle_order"].is<bool>())
                    return {"'vehicle_order' property is not defined as a boolean"};
                result.VehicleOrder = obj["vehicle_order"].get<bool>();
            }

            // Line of sight order - Optional
            if (!obj["line_of_sight"].is<picojson::null>())
            {
                if (!obj["line_of_sight"].is<picojson::object>())
                    return {"'line_of_sight' property is not defined as an object"};
                auto line_of_sight = MissionGeometry::FromJson(obj["line_of_sight"].get<picojson::object>());
                if (!line_of_sight.Success)
                    return {"Error in 'line_of_sight' property: " + line_of_sight.Log};
                result.LineOfSight = line_of_sight.Result.value();
            }
            // Line of sight order propagation - Optional
            if (!obj["line_of_sight_propagation"].is<picojson::null>())
            {
                if (!obj["line_of_sight_propagation"].is<bool>())
                    return {"'line_of_sight_propagation' property is not defined as a boolean"};
                result.LineOfSightPropagation = obj["line_of_sight_propagation"].get<bool>();
            }

            // Maximize coverage - Optional
            if (!obj["maximize_coverage"].is<picojson::null>())
            {
                if (!obj["maximize_coverage"].is<bool>())
                    return {"'maximize_coverage' property is not defined as a boolean"};
                result.MaximizeCoverage = obj["maximize_coverage"].get<bool>();
            }

            // Maximum coverage distance - Optional
            if (!obj["maximize_coverage_distances"].is<picojson::null>())
            {
                if (!obj["maximize_coverage_distances"].is<picojson::array>())
                    return {"'maximize_coverage_distances' property is not defined as an array"};
                std::vector<double> distances;
                for (auto &col : obj["maximize_coverage_distances"].get<picojson::array>())
                {
                    if (!col.is<double>())
                        return {"distance inside 'maximize_coverage_distance' property is not a number"};
                    distances.push_back(col.get<double>());
                }
                result.MaximizeCoverageDistances = distances;
            }

            // Arrival time
            if (!obj["arrival_time"].is<picojson::null>())
            {
                if (!obj["arrival_time"].is<picojson::object>())
                    return {"arrival_time property is empty"};

                auto arrival_time = MissionTime::FromJson(obj["arrival_time"].get<picojson::object>());
                if (!arrival_time.Success)
                    return {"error in 'objective.arrival_time' property: " + arrival_time.Log};

                result.ArrivalTime = arrival_time.Result.value();
            }
            else
            {
                result.ArrivalTime = MissionTime();
            }

            return {result};
        };

        // From data structure to Json
        picojson::object ToJson() const
        {
            picojson::object result;
            std::string err;

            // Geometries
            picojson::array geometriesJson;
            for (const auto &geometry : Geometries)
            {
                geometriesJson.push_back(picojson::value(geometry.ToJson()));
            }
            result["geometries"] = picojson::value(geometriesJson);

            // // geometry
            // result["geometry"] = picojson::value(this->Geometry.ToJson());

            // arrival time
            result["arrival_time"] = picojson::value(this->ArrivalTime.ToJson());

            // Min distance
            if (this->MinimumDistance.has_value())
            {
                result["minimum_distance"] = picojson::value(this->MinimumDistance.value());
            }
            // Max distance
            if (this->MaximumDistance.has_value())
            {
                result["maximum_distance"] = picojson::value(this->MaximumDistance.value());
            }
            // Vehicle formation
            if (this->VehicleFormation.has_value())
            {
                result["vehicle_formation"] = picojson::value(static_cast<double>(this->VehicleFormation.value()));
            }
            // Vehicle formation distance
            if (this->VehicleFormationDistance.has_value())
            {
                result["vehicle_formation_distance"] = picojson::value(this->VehicleFormationDistance.value());
            }
            // Vehicle orientation
            if (this->VehicleOrientation.has_value())
            {
                picojson::array orientation_json;
                for (auto &ori : this->VehicleOrientation.value())
                {
                    orientation_json.push_back(picojson::value(ori));
                }
                result["vehicle_orientation"] = picojson::value(orientation_json);
            }
            // Vehicle orientation orientation
            if (this->VehicleOrientationOri.has_value())
            {
                result["vehicle_orientation_origin"] = picojson::value(this->VehicleOrientationOri->ToJson());
            }
            // Vehicle order
            if (this->VehicleOrder.has_value())
            {
                result["vehicle_order"] = picojson::value(this->VehicleOrder.value());
            }
            // Line of sight
            if (this->LineOfSight.has_value())
            {
                result["line_of_sight"] = picojson::value(this->LineOfSight->ToJson());
            }
            // Line of sight propagation
            if (this->LineOfSightPropagation.has_value())
            {
                result["line_of_sight_propagation"] = picojson::value(this->LineOfSightPropagation.value());
            }
            // Max coverage
            if (this->MaximizeCoverage.has_value())
            {
                result["maximize_coverage"] = picojson::value(this->MaximizeCoverage.value());
            }
            // Maximize coverage distance
            if (this->MaximizeCoverageDistances.has_value())
            {
                picojson::array distances;
                for (auto &dist : this->MaximizeCoverageDistances.value())
                {
                    distances.push_back(picojson::value(dist));
                }
                result["MaximizeCoverageDistances"] = picojson::value(distances);
            }
            return result;
        };

        std::string ToJsonString() const
        {
            return picojson::value(this->ToJson()).serialize();
        };
    };

    class MissionOptimalization
    {
    public:
        std::optional<double> Visibility;
        std::optional<double> Energy;
        std::optional<double> RoadUsage;

        static JsonResult<MissionOptimalization> FromJson(picojson::object &obj)
        {
            // check if the message is not empty
            if (obj.empty())
                return {"'Optimalization' property is empty!"};

            MissionOptimalization result;

            // Visibility
            if (!obj["visibility"].is<picojson::null>())
            {
                if (!obj["visibility"].is<double>())
                    return {"'visibility' property is not defined as a number"};
                result.Visibility = obj["visibility"].get<double>();
            }

            // Energy
            if (!obj["energy"].is<picojson::null>())
            {
                if (!obj["energy"].is<double>())
                    return {"'energy' property is not defined as a number"};
                result.Energy = obj["energy"].get<double>();
            }

            // RoadUsage
            if (!obj["road_usage"].is<picojson::null>())
            {
                if (!obj["road_usage"].is<double>())
                    return {"'road_usage' property is not defined as a number"};
                if (obj["road_usage"].get<double>() > 100 || obj["road_usage"].get<double>() < 0)
                    return {"'road_usage' property is not set in the range 0-100"};
                result.RoadUsage = obj["road_usage"].get<double>();
            }

            return {result};
        };

        picojson::object ToJson() const
        {
            picojson::object result;

            if (this->Visibility.has_value())
            {
                result["visibility"] = picojson::value(this->Visibility.value());
            }
            if (this->Energy.has_value())
            {
                result["energy"] = picojson::value(this->Energy.value());
            }
            if (this->RoadUsage.has_value())
            {
                result["road_usage"] = picojson::value(this->RoadUsage.value());
            }

            return {result};
        };

        std::string ToJsonString() const
        {
            return picojson::value(this->ToJson()).serialize();
        };
    };

    /* Optional Class */
    class VehicleDesiredConstraints
    {
    public:
        std::optional<double> MaxSpeed;
        std::optional<double> MaxAccel;
        std::optional<double> MaxJerk;
        std::optional<double> MaxDecel;
        std::optional<double> MaxStraightSlope;
        std::optional<double> MaxSideSlope;

        static JsonResult<VehicleDesiredConstraints> FromJson(picojson::object &obj)
        {
            VehicleDesiredConstraints result;

            // MaxSpeed
            if (!obj["max_speed"].is<picojson::null>())
            {
                if (!obj["max_speed"].is<double>())
                    return {"'max_speed' property is not defined as a number"};
                result.MaxSpeed = obj["max_speed"].get<double>();
            }

            // MaxAccel
            if (!obj["max_acceleration"].is<picojson::null>())
            {
                if (!obj["max_acceleration"].is<double>())
                    return {"'max_acceleration' property is not defined as a number"};
                result.MaxAccel = obj["max_acceleration"].get<double>();
            }

            // MaxJerk
            if (!obj["max_jerk"].is<picojson::null>())
            {
                if (!obj["max_jerk"].is<double>())
                    return {"'max_jerk' property is not defined as a number"};
                result.MaxJerk = obj["max_jerk"].get<double>();
            }

            // MaxDecel
            if (!obj["max_deceleration"].is<picojson::null>())
            {
                if (!obj["max_deceleration"].is<double>())
                    return {"'max_deceleration' property is not defined as a number"};
                result.MaxDecel = obj["max_deceleration"].get<double>();
            }

            // MaxStraightSlope
            if (!obj["max_straight_slope"].is<picojson::null>())
            {
                if (!obj["max_straight_slope"].is<double>())
                    return {"'max_straight_slope' property is not defined as a number"};
                result.MaxStraightSlope = obj["max_straight_slope"].get<double>();
            }

            // MaxSideSlope
            if (!obj["max_side_slope"].is<picojson::null>())
            {
                if (!obj["max_side_slope"].is<double>())
                    return {"'max_side_slope' property is not defined as a number"};
                result.MaxSideSlope = obj["max_side_slope"].get<double>();
            }

            return {result};
        };

        picojson::object ToJson() const
        {
            picojson::object result;

            // MaxSpeed
            if (this->MaxSpeed.has_value())
                result["max_speed"] = picojson::value(this->MaxSpeed.value());

            // MaxAccel
            if (this->MaxAccel.has_value())
                result["max_acceleration"] = picojson::value(this->MaxAccel.value());

            // MaxJerk
            if (this->MaxJerk.has_value())
                result["max_jerk"] = picojson::value(this->MaxJerk.value());

            // MaxDecel
            if (this->MaxDecel.has_value())
                result["max_deceleration"] = picojson::value(this->MaxDecel.value());

            // MaxStraightSlope
            if (this->MaxStraightSlope.has_value())
                result["max_straight_slope"] = picojson::value(this->MaxStraightSlope.value());

            // MaxSideSlope
            if (this->MaxSideSlope.has_value())
                result["max_side_slope"] = picojson::value(this->MaxSideSlope.value());

            return {result};
        };

        std::string ToJsonString() const
        {
            return picojson::value(this->ToJson()).serialize();
        };
    };

    class MissionTransit
    {
    public:
        std::optional<MissionGeometry> Geofence;
        std::optional<bool> GeofenceMaximizeCoverage;
        std::optional<double> VehicleFormation;
        std::optional<double> VehicleFormationDistance;
        std::optional<MissionOptimalization> Optimalization;
        std::optional<VehicleDesiredConstraints> DesiredVehicleConstraints;

        static JsonResult<MissionTransit> FromJson(picojson::object &obj)
        {
            if (obj.empty())
                return {"'Optimalization' property is empty!"};

            MissionTransit result;

            // Geofence property
            if (!obj["geofence"].is<picojson::null>())
            {
                if (!obj["geofence"].is<picojson::object>())
                    return {"'geofence'property is not defined as an object"};

                auto geofence = MissionGeometry::FromJson(obj["geofence"].get<picojson::object>());
                if (!geofence.Success)
                    return {"Error in ǵeofence' property: " + geofence.Log};

                result.Geofence = geofence.Result.value();
            }

            // GeofenceMaximizeCoverage - Optional
            if (!obj["geofence_maximum_coverage"].is<picojson::null>())
            {
                if (!obj["geofence_maximum_coverage"].is<bool>())
                    return {"'geofence_maximum_coverage' property is not defined as a boolean"};

                result.GeofenceMaximizeCoverage = obj["geofence_maximum_coverage"].get<bool>();
            }

            // VehicleFormation property - Optional
            if (!obj["vehicle_formation"].is<picojson::null>())
            {
                if (!obj["vehicle_formation"].is<double>())
                    return {"'vehicle_formation' property is not defined as a number"};
                result.VehicleFormation = obj["vehicle_formation"].get<double>();
            }

            // VehicleFormationDistance property - Optional
            if (!obj["vehicle_formation_distance"].is<picojson::null>())
            {
                if (!obj["vehicle_formation_distance"].is<double>())
                    return {"'vehicle_formation_distance' property is not defined as a number"};
                result.VehicleFormationDistance = obj["vehicle_formation_distance"].get<double>();
            }

            // Optimalization property - Optional
            if (!obj["optimalization"].is<picojson::null>())
            {
                if (!obj["optimalization"].is<picojson::object>())
                    return {"'vehicle_formation' property is not defined as an object"};
                auto optimalization = MissionOptimalization::FromJson(obj["optimalization"].get<picojson::object>());
                if (!optimalization.Success)
                    return {"Error in 'optimalization' property: " + optimalization.Log};
                result.Optimalization = optimalization.Result.value();
            }

            // DesiredVehicleConstraints - Optional
            if (!obj["desired_vehicle_constraints"].is<picojson::object>())
                return {"'desired_vehicle_constraints' property is not defined as an object"};

            auto constraints = VehicleDesiredConstraints::FromJson(obj["desired_vehicle_constraints"].get<picojson::object>());
            if (!constraints.Success)
                return {"Error in 'desired_vehicle_constraints' property: " + constraints.Log};
            result.DesiredVehicleConstraints = constraints.Result.value();

            return {result};
        }

        picojson::object ToJson() const
        {
            picojson::object result;

            if (this->Geofence.has_value())
            {
                result["geofence"] = picojson::value(this->Geofence.value().ToJson());
            }
            if (this->GeofenceMaximizeCoverage.has_value())
            {
                result["geofence_maximum_coverage"] = picojson::value(this->GeofenceMaximizeCoverage.value());
            }
            if (this->VehicleFormation.has_value())
            {
                result["vehicle_formation"] = picojson::value(this->VehicleFormation.value());
            }
            if (this->VehicleFormationDistance.has_value())
            {
                result["vehicle_formation_distance"] = picojson::value(this->VehicleFormationDistance.value());
            }
            if (this->Optimalization.has_value())
            {
                result["optimalization"] = picojson::value(this->Optimalization.value().ToJson());
            }
            if (this->DesiredVehicleConstraints.has_value())
            {
                result["desired_vehicle_constraints"] = picojson::value(this->DesiredVehicleConstraints.value().ToJson());
            }

            return {result};
        };

        std::string ToJsonString() const
        {
            return picojson::value(this->ToJson()).serialize();
        };
    };

    class MissionConfig
    {
    public:
        std::string MissionId;
        json::enums::Behavior Behavior;
        std::vector<std::string> Vehicles;
        std::optional<MissionStart> Start;
        MissionObjective Objective;
        std::optional<MissionTransit> Transit;
        // std::optional<double> MissionEndTime; // todo

        static JsonResult<MissionConfig> FromJsonString(const std::string &str)
        {
            picojson::value configJson;
            std::string errConfigParsing = picojson::parse(configJson, str);
            if (!errConfigParsing.empty())
                return {"Parsing of json config failed: " + errConfigParsing};

            return FromJson(configJson.get<picojson::object>());
        };

        static JsonResult<MissionConfig> FromJson(picojson::object &obj)
        {
            MissionConfig result;

            if (obj.empty())
                return {"Config is empty"};

            // Mission Id property
            if (!obj["mission_id"].is<picojson::null>())
            {
                // return{"'mission_id' property is empty!"};
                if (!obj["mission_id"].is<std::string>())
                    return {"'mission_id' is not defined as a string"};
                result.MissionId = obj["mission_id"].get<std::string>();
            }

            // Behavior property
            if (obj["behavior"].is<picojson::null>())
                result.Behavior = json::enums::Behavior::NAVIGATE;
            // return {"'behavior' property is empty!"};
            if (!obj["behavior"].is<double>())
                return {"'behavior is not defined as a number"};
            result.Behavior = json::enums::Behavior(obj["behavior"].get<double>());

            // Vehicle property
            if (!obj["vehicles"].is<picojson::array>())
                return {"Vehicles property is empty!"};

            for (auto &&vehicle : obj["vehicles"].get<picojson::array>())
                result.Vehicles.push_back(vehicle.get<std::string>());

            // Objective property
            if (obj["objective"].is<picojson::null>())
                return {"objective property is empty!"};
            if (!obj["objective"].is<picojson::object>())
                return {"objective property is not defined as an object!"};

            auto objective = MissionObjective::FromJson(obj["objective"].get<picojson::object>());
            if (!objective.Success)
                return {"error in 'objective' property: " + objective.Log};
            result.Objective = objective.Result.value();

            // Start property - Optional
            if (!obj["start"].is<picojson::null>())
            {
                auto start = obj["start"];
                if (!start.is<picojson::object>())
                    return {"'start' property is not define as an object"};
                auto mission_start = MissionStart::FromJson(start.get<picojson::object>());
                if (!mission_start.Result)
                    return {"error in 'objective' property: " + mission_start.Log};

                result.Start = mission_start.Result.value();
            }

            // Transit property - Optional
            if (!obj["transit"].is<picojson::null>())
            {
                if (!obj["transit"].is<picojson::object>())
                    return {"'transit' property is not defined as an object"};
                auto transit = MissionTransit::FromJson(obj["transit"].get<picojson::object>());
                if (!transit.Success)
                    return {"Error in 'transit' property: " + transit.Log};
                result.Transit = transit.Result.value();
            }

            return {result};
        };

        picojson::object ToJson() const
        {
            picojson::object result;

            picojson::array vehiclesJson;
            for (auto &&vehicle : this->Vehicles)
            {
                vehiclesJson.push_back(picojson::value(vehicle));
            }
            result["vehicles"] = picojson::value(vehiclesJson);
            result["mission_id"] = picojson::value(this->MissionId);
            result["behavior"] = picojson::value(static_cast<double>(this->Behavior));
            result["objective"] = picojson::value(this->Objective.ToJson());
            if (this->Start.has_value())
                result["start"] = picojson::value(this->Start.value().ToJson());
            if (this->Transit.has_value())
                result["transit"] = picojson::value(this->Transit.value().ToJson());

            return result;
        };

        std::string ToJsonString() const
        {
            return picojson::value(this->ToJson()).serialize();
        };
    };
}