#include <gtest/gtest.h>
#include <fstream>
#include <sstream>
#include "../json/tasks/DriveConfig.hpp"
#include "../json/Enums.hpp"
#include "../json/Pose.hpp"

using namespace autonomy_msgs::json;

inline std::string ReadConfig(std::string file)
{
        std::ifstream t(("../test/Data/" + file).c_str());
        std::stringstream buffer;
        buffer << t.rdbuf();
        return buffer.str();
}

TEST(Config, task_drive_config_simple_0)
{
        //std::string json = ReadConfig("task_drive_config_simple_0.json");
        // auto configParsed = Config::FromJsonString(json);
        //ASSERT_TRUE(configParsed.Success) << "Error in parsing: " + configParsed.Log;

        // auto &config = configParsed.Result.value();

        // TODO: ASSERT_EQ on vars
}

int main(int argc, char **argv)
{
        testing::InitGoogleTest(&argc, argv);
        return RUN_ALL_TESTS();
}