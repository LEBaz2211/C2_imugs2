#include <gtest/gtest.h>
#include <fstream>
#include <sstream>
#include "../json/MissionConfig.hpp"
#include "../json/MissionFeedback.hpp"
// #include "../json/GPSPose.hpp"
#include "../json/GPSCoordinate.hpp"
#include "../json/include/Isotime.h"
#include <ostream>

using namespace c2_msgs::json;

inline std::string ReadConfig(std::string file)
{
        std::ifstream t("/home/emile/Documents/dev_ws/imugs/test_ws/src/swarm_msg/test/Data/" + file);
        std::stringstream buffer;
        buffer << t.rdbuf();
        return buffer.str();
}

TEST(MissionConfig, Vehicle_Test)
{
        auto configParsed = MissionConfig::FromJsonString("{\"vehicles\":[\"vehicle_1\"]}");
        ASSERT_TRUE(!configParsed.Success) << "Must contain error, objective can't be empty";
}

TEST(MissionConfig, Reading_File)
{
        std::string json = ReadConfig("mission_config_example_1_waypoint_navigation.json");
        ASSERT_TRUE(!json.empty()) << "Error reading file, return empty string";
        // auto configParsed = MissionConfig::FromJsonString(json);
        // ASSERT_TRUE(configParsed.Success) << "Error in parsing: " + configParsed.Log;
}

TEST(MissionConfig, MissionConfig_Test1)
{
    std::string json = ReadConfig("mission_config_example_0_simple.json");
    auto configParsed = MissionConfig::FromJsonString(json);
    ASSERT_TRUE(configParsed.Success) << "Error in parsing: " + configParsed.Log;

    auto &config = configParsed.Result.value();

    // Check the number of vehicles
    ASSERT_EQ(config.Vehicles.size(), (size_t)3);
    ASSERT_EQ(config.Vehicles[0], "f17d27fc-50f6-11ec-bf63-0242ac130002");
    ASSERT_EQ(config.Vehicles[1], "fcee3176-50f6-11ec-bf63-0242ac130002");
    ASSERT_EQ(config.Vehicles[2], "t18d27fc-50f6-11ec-bf63-0242ac130055");

    // Ensure geometries exist
    ASSERT_FALSE(config.Objective.Geometries.empty()) << "Objective geometries list is empty!";

    bool hasCoordinates = false;
    bool hasFeatureId = false;

    // Loop through geometries and check for valid fields
    for (const auto &geometry : config.Objective.Geometries)
    {
        if (geometry.Coordinates.has_value())
        {
            hasCoordinates = true;
            ASSERT_FALSE(geometry.Coordinates->empty()) << "Coordinates list is empty!";
        }
        if (geometry.FeatureId.has_value())
        {
            hasFeatureId = true;
            ASSERT_FALSE(geometry.FeatureId->empty()) << "Feature ID is empty!";
        }
    }

    // Ensure at least one geometry has coordinates or a feature ID
    ASSERT_TRUE(hasCoordinates || hasFeatureId) << "No valid geometries found with coordinates or feature ID!";
}


TEST(MissionConfig, MissionConfig_WpNav)
{
        std::string json = ReadConfig("mission_config_example_1_waypoint_navigation.json");
        
        auto configParsed = MissionConfig::FromJsonString(json);
        ASSERT_TRUE(configParsed.Success) << "Error in parsing: " + configParsed.Log;

        auto &config = configParsed.Result.value();

        /****************************************************************/
        /*                      Vehicle                                 */
        /****************************************************************/
        ASSERT_EQ(config.Vehicles.size(), (size_t)3);
        ASSERT_EQ(config.Vehicles[0], "f17d27fc-50f6-11ec-bf63-0242ac130000");
        ASSERT_EQ(config.Vehicles[1], "fcee3176-50f6-11ec-bf63-0242ac130001");
        ASSERT_EQ(config.Vehicles[2], "t18d27fc-50f6-11ec-bf63-0242ac130052");

        /****************************************************************/
        /*                      Objective                               */
        /****************************************************************/
        // ArrivalTime
        ASSERT_EQ(config.Objective.ArrivalTime.Earliest, Isotime::FromIso8601("1991-03-26T07:28:00Z"));
        ASSERT_EQ(config.Objective.ArrivalTime.Target, Isotime::FromIso8601("1991-03-26T07:28:00Z"));
        ASSERT_EQ(config.Objective.ArrivalTime.Latest, Isotime::FromIso8601("1991-03-26T07:28:00Z"));

        // Ensure geometries exist
        ASSERT_FALSE(config.Objective.Geometries.empty()) << "Objective geometries list is empty!";

        bool hasFeatureId = false;

        // Check if at least one geometry contains the expected FeatureId
        for (const auto &geometry : config.Objective.Geometries)
        {
                if (geometry.FeatureId.has_value() && geometry.FeatureId.value() == "6c411df5-e75f-4d4f-a647-ae2877f208da")
                {
                hasFeatureId = true;
                break;
                }
        }

        ASSERT_TRUE(hasFeatureId) << "Expected FeatureId not found in any geometry!";

        
        // VehicleOrientation - Optional
        ASSERT_TRUE(config.Objective.VehicleOrientationOri.value().FeatureId.has_value());
        ASSERT_EQ(config.Objective.VehicleOrientationOri.value().FeatureId, "6c411df5-e75f-4d4f-a647-ae2877f208db");

        // Order - Optional
        ASSERT_TRUE(config.Objective.VehicleOrder.has_value());
        ASSERT_TRUE(config.Objective.VehicleOrder.value());

        // LineOfSight - Optional
        ASSERT_TRUE(config.Objective.LineOfSight->GeometryType.has_value());
        ASSERT_TRUE(config.Objective.LineOfSight->Coordinates.has_value());
        ASSERT_EQ(config.Objective.LineOfSight->GeometryType.value(), "Polygon");
        // ASSERT_EQ(config.Objective.LineOfSight->Coordinates->size(), (size_t)3);
        ASSERT_EQ(config.Objective.LineOfSight->Coordinates->at(0).Lat, -67.13734);
        ASSERT_EQ(config.Objective.LineOfSight->Coordinates->at(0).Lng, 45.13745);

        // LineOfSightPropagation - Optional
        ASSERT_TRUE(config.Objective.LineOfSightPropagation.has_value());
        ASSERT_TRUE(config.Objective.LineOfSightPropagation.value());

        // MaxmizeCoverage - Optional
        ASSERT_TRUE(config.Objective.MaximizeCoverage.has_value());
        ASSERT_TRUE(config.Objective.MaximizeCoverage.value());

        // MaximizeCoverageDistances - Optional
        ASSERT_TRUE(config.Objective.MaximizeCoverageDistances.has_value());
        ASSERT_EQ(config.Objective.MaximizeCoverageDistances.value().size(), (size_t)5);
        ASSERT_EQ(config.Objective.MaximizeCoverageDistances.value().at(0), 1.0);

        /****************************************************************/
        /*                       Transit                                */
        /****************************************************************/
        // Geofence - Optional
        ASSERT_TRUE(config.Transit.has_value());
        ASSERT_TRUE(config.Transit.value().Geofence.has_value());
        ASSERT_EQ(config.Transit.value().Geofence.value().FeatureId, "d17d27fc-50d6-11ec-bf63-0242ac130203");

        // GeofenceMaximumCoverage - Optional
        ASSERT_TRUE(config.Transit.value().GeofenceMaximizeCoverage.value());

        // VehicleFormation - Optional
        ASSERT_EQ(config.Transit.value().VehicleFormation.value(), 1);

        // VehicleFormationDistance - Optional
        ASSERT_EQ(config.Transit.value().VehicleFormationDistance.value(), 10);

        // Optimalization - Optional
        ASSERT_TRUE(config.Transit.value().Optimalization.has_value());
        ASSERT_TRUE(config.Transit.value().Optimalization.value().Visibility.has_value());
        ASSERT_TRUE(config.Transit.value().Optimalization.value().Energy.has_value());
        ASSERT_TRUE(config.Transit.value().Optimalization.value().RoadUsage.has_value());

        ASSERT_EQ(config.Transit.value().Optimalization.value().Visibility.value(), 70);
        ASSERT_EQ(config.Transit.value().Optimalization.value().Energy.value(), 1);
        ASSERT_EQ(config.Transit.value().Optimalization.value().RoadUsage.value(), 1);

}


TEST(MissionConfig, MissionConfig_CoverageMission)
{
        std::string json = ReadConfig("CoverageMissionInit_2.json");
        auto configParsed = MissionConfig::FromJsonString(json);
        ASSERT_TRUE(configParsed.Success) << "Error in parsing: " + configParsed.Log;

        auto &config = configParsed.Result.value();

        ASSERT_TRUE(config.Transit.has_value());
}

TEST(MissionFeedback, mission_feedback_Objective)
{
        std::string json = ReadConfig("mission_feedback_example1.json");

        ASSERT_TRUE(!json.empty()) << "Error reading file, return empty string";
        auto feedbackParsed = MissionFeedback::FromJsonString(json);
        ASSERT_TRUE(feedbackParsed.Success) << "Error in parsing: " + feedbackParsed.Log;

        auto &feedback = feedbackParsed.Result.value();

        ASSERT_EQ(feedback.Objective.has_value(), true);
        ASSERT_EQ(feedback.Objective.value()[0].FeatureId, "fcee3176-50f6-11ec-bf63-0242ac130002");
        ASSERT_EQ(feedback.Objective.value()[0].Type, enums::ObjectiveType::TRACKING_TARGET_INFORMATION);
        ASSERT_EQ(feedback.Objective.value()[0].ObjectLocations.has_value(), true);
        ASSERT_EQ(feedback.Objective.value()[0].ObjectLocations.value()[0].Velocity[0], 10);
        ASSERT_EQ(feedback.Objective.value()[0].ObjectLocations.value()[0].TimeStamp, Isotime::FromIso8601("1991-03-26 07:10:00Z"));
        ASSERT_EQ(feedback.Objective.value()[0].ObjectLocations.value().size(), (size_t)3);
        ASSERT_EQ(feedback.Objective.value()[0].ObjectLocations.value().at(0).Coordinates.size(), (size_t)3);
        ASSERT_EQ(feedback.Objective.value()[0].ObjectLocations.value().at(0).Coordinates.at(0).Lat, -67.13734);
        ASSERT_EQ(feedback.Objective.value()[0].ObjectLocations.value().at(0).Coordinates.at(0).Lng, 45.13745);
}

TEST(MissionFeedback, mission_feedback_alternative_plan)
{
        std::string json = ReadConfig("mission_feedback_alternative_plan.json");

        ASSERT_TRUE(!json.empty()) << "Error reading file, return empty string";
        auto feedbackParsed = MissionFeedback::FromJsonString(json);
        ASSERT_TRUE(feedbackParsed.Success) << "Error in parsing: " + feedbackParsed.Log;

        auto &feedback = feedbackParsed.Result.value();

        ASSERT_EQ(feedback.Behavior, enums::Behavior::NAVIGATE);
        ASSERT_EQ(feedback.Status, enums::MissionStatus::PLANNED_ALTERNATIVE);
        ASSERT_EQ(feedback.RequestedStatus, enums::MissionStatusRequest::START);
        ASSERT_EQ(feedback.Date, Isotime::FromIso8601("1991-03-26 07:00:00Z"));

        ASSERT_TRUE(feedback.Tasks.has_value());
        ASSERT_EQ(feedback.Tasks.value().size(), (size_t)2);
        ASSERT_EQ(feedback.Tasks.value()[0].VehicleId, "f17d27fc-50f6-11ec-bf63-0242ac130002");
        ASSERT_EQ(feedback.Tasks.value()[0].Est, Isotime::FromIso8601("1991-03-26 07:10:00Z"));
        ASSERT_TRUE(feedback.Tasks.value()[0].Waypoints.has_value());
        ASSERT_EQ(feedback.Tasks.value()[0].Waypoints.value().size(), (size_t)3);
        ASSERT_EQ(feedback.Tasks.value()[0].Waypoints.value()[0].Coordinates.Lat, -67.13734);
        ASSERT_EQ(feedback.Tasks.value()[0].Waypoints.value()[0].Coordinates.Lng, 45.13745);
        ASSERT_EQ(feedback.Tasks.value()[0].Waypoints.value()[2].Coordinates.Lat, -67.79141);
        ASSERT_EQ(feedback.Tasks.value()[0].Waypoints.value()[2].Coordinates.Lng, 45.70258);
        ASSERT_EQ(feedback.Tasks.value()[0].Waypoints.value()[2].AverageSpeed, 15);
        ASSERT_EQ(feedback.Tasks.value()[0].Waypoints.value()[2].Orientation.has_value(), true);
        ASSERT_EQ(feedback.Tasks.value()[0].Waypoints.value()[2].Orientation, 101);
        ASSERT_EQ(feedback.Tasks.value()[0].Waypoints.value()[2].Eta, Isotime::FromIso8601("1991-03-26 07:00:00Z"));

        ASSERT_EQ(feedback.Objective.has_value(), true);
        ASSERT_EQ(feedback.Objective.value()[0].FeatureId, "fcee3176-50f6-11ec-bf63-0242ac130002");
        ASSERT_EQ(feedback.Objective.value()[0].Type, enums::ObjectiveType::TRACKING_TARGET_INFORMATION);
        ASSERT_EQ(feedback.Objective.value()[0].ObjectLocations.has_value(), true);
        ASSERT_EQ(feedback.Objective.value()[0].ObjectLocations.value()[0].Velocity[0], 10);
        ASSERT_EQ(feedback.Objective.value()[0].ObjectLocations.value()[0].TimeStamp, Isotime::FromIso8601("1991-03-26 07:10:00Z"));
        ASSERT_EQ(feedback.Objective.value()[0].ObjectLocations.value().size(), (size_t)3);
        ASSERT_EQ(feedback.Objective.value()[0].ObjectLocations.value().at(0).Coordinates.size(), (size_t)3);
        ASSERT_EQ(feedback.Objective.value()[0].ObjectLocations.value().at(0).Coordinates.at(0).Lat, -67.13734);
        ASSERT_EQ(feedback.Objective.value()[0].ObjectLocations.value().at(0).Coordinates.at(0).Lng, 45.13745);
}
int main(int argc, char **argv)
{
        testing::InitGoogleTest(&argc, argv);
        return RUN_ALL_TESTS();
}