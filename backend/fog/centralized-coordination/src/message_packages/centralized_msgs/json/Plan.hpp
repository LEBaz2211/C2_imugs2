#pragma once

#include <vector>
#include <string>

#include "include/picojson.h"
#include "include/JsonResult.h"
#include "include/Isotime.h"

#include "Task.hpp"
#include "Enums.hpp"

namespace centralized_msgs::json
{
        class Plan
        {
        public:
                enums::PlanStatus Status;
                time_t From; // calculation start time
                time_t To;   // calculated plan to time
                std::vector<Task> Tasks;

                Plan();
                Plan(enums::PlanStatus status, time_t from, time_t to, std::vector<Task> tasks) : Status(status), From(from), To(to), Tasks(tasks){};

                static JsonResult<Plan> FromJsonString(const std::string &str)
                {
                        picojson::value configJson;
                        std::string errConfigParsing = picojson::parse(configJson, str);
                        if (!errConfigParsing.empty())
                                return {"Parsing of json config failed: " + errConfigParsing};
                        return FromJson(configJson.get<picojson::object>());
                };

                static JsonResult<Plan> FromJson(picojson::object &obj)
                {
                        if (obj.empty())
                                return {"Plan is empty"};

                        std::vector<Task> tasks;
                        if (obj["tasks"].is<picojson::array>())
                        {
                                auto tasksJson = obj["tasks"].get<picojson::array>();
                                for (auto &&taskJson : tasksJson)
                                {
                                        if (taskJson.is<picojson::object>())
                                        {
                                                auto task = Task::FromJson(taskJson.get<picojson::object>());
                                                if (!task.Success)
                                                        return {"Unable to parse ask: " + task.Log};

                                                tasks.push_back(task.Result.value());
                                        }
                                }
                        }

                        if (!obj["status"].is<double>())
                                return {"Status is empty"};

                        if (!obj["from"].is<std::string>())
                                return {"From date is empty"};

                        if (!obj["to"].is<std::string>())
                                return {"To date is empty"};

                        auto from = Isotime::FromIso8601(obj["from"].get<std::string>());
                        auto to = Isotime::FromIso8601(obj["to"].get<std::string>());
                        auto status = static_cast<enums::PlanStatus>((int)obj["status"].get<double>());

                        return {Plan(status, from, to, tasks)};
                };

                std::string ToJsonString() const
                {
                        return picojson::value(this->ToJson()).serialize();
                };

                picojson::object ToJson() const
                {
                        picojson::object result;
                        picojson::array tasksJson;
                        for (auto &&task : this->Tasks)
                                tasksJson.push_back(picojson::value(task.ToJson()));

                        result["status"] = picojson::value((double)(int)this->Status);
                        result["tasks"] = picojson::value(tasksJson);
                        result["from"] = picojson::value(Isotime::ToIso8601(this->From));
                        result["to"] = picojson::value(Isotime::ToIso8601(this->To));
                        return result;
                };
        };
}