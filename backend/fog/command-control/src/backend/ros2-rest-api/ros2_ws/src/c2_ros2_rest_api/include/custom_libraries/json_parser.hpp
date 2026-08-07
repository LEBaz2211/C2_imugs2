/****************************************************************/
// JSON parsing library
// Emile Le Flecher & Alexandre La Grappe - RMA - alexandre.lagrappe@mil.be or emile.leflecher@mil.be
// 21.02.2022 - V1.0.0
/****************************************************************/
// #pragma once
#ifndef JSONLIB_HPP
#define JSONLIB_HPP

#include <fstream>
#include <iostream>
#include <nlohmann/json.hpp>

namespace swarm_manager::json_lib
{
  // using json = nlohmann::json;

  class JsonParser
  {
  public:
    /* Generic class (Could be in a utils package) */
    /* Open a stored json file + save in json variable + serialization in std::string */
    static nlohmann::json readJsonFile(std::string path_to_json, std::string file_name)
    {
      nlohmann::json json_output;
      std::ifstream file;

      file.open(path_to_json + file_name); // Open file

      if (file.is_open() && !file.fail()) // Check opening error
      {
        file >> json_output; // deserialize from file
        file.close();
        return json_output;
      }
      else
      {
        std::cout << "json file: " << file_name << " opening failed" << std::endl;
        return -1;
      }
    };

    /* Serialize json to string */
    static std::string serializeJsonToString(nlohmann::json json_input)
    {
      std::string str_output;
      try
      {
        str_output = json_input.dump();
      }
      catch (const std::exception &e)
      {
        std::cerr << e.what() << '\n';
      }

      return str_output;
    };

    static nlohmann::json deserialzeStringToJson(std::string str_input)
    {
      nlohmann::json json_output;
      try
      {
        json_output = nlohmann::json::parse(str_input);
      }
      catch (const std::exception &e)
      {
        std::cerr << e.what() << '\n';
      }
      return json_output;
    };
  };

}

#endif