#include <cpprest/http_listener.h>
#include <cpprest/json.h>
#include "c2_ros2_rest_api/c2_rest.hpp"
#include <nlohmann/json.hpp>  // Make sure this is included for JSON parsing
#include <iostream>
#include <exception>

using namespace web;
using namespace http;
using namespace http::experimental::listener;

class MissionHandler {
public:
    MissionHandler(utility::string_t url, C2* c2_instance) : listener(url), c2_instance(c2_instance) {

        listener.support(methods::OPTIONS, [](http_request request) {
            // Reply to the preflight request for CORS with appropriate headers
            http_response response(status_codes::OK);
            response.headers().add(U("Access-Control-Allow-Origin"), U("*"));
            response.headers().add(U("Access-Control-Allow-Methods"), U("GET, POST, OPTIONS"));
            response.headers().add(U("Access-Control-Allow-Headers"), U("Content-Type"));
            request.reply(response);
        });

        listener.support(methods::POST, std::bind(&MissionHandler::handle_post_request, this, std::placeholders::_1));
        listener.open().wait();
        // std::wcout << "Listening for requests at: " << url << std::endl;
    }

    // Handle POST requests
    void handle_post_request(http_request request) {
        std::cout << "Received request: " << std::endl;

        // Try extracting the JSON body
        request.extract_json().then([=](json::value json_request) {
            try {
                std::string action = json_request[U("action")].as_string();
                if (action == "change_status") {
                    int requested_state = json_request[U("requested_state")].as_integer();
                    std::cout << "Change status " << std::endl;
                    c2_instance->sendChangeStatus(requested_state);
                    request.reply(status_codes::OK, U("Mission status change requested"));
                } 
                else if (action == "initialize") {
                    // std::cout << "Extracted JSON body: " << json_request.serialize() << std::endl;
                    // Check if both mission_id and mission_config fields exist
                    if (json_request.has_field(U("mission_id")) && json_request.has_field(U("mission_config"))) {
                        std::string mission_id = json_request[U("mission_id")].as_string();
                        std::cout << "Mission_id: " << mission_id << std::endl;

                        // Get the raw mission_config string and print it
                        std::string mission_config_str = json_request[U("mission_config")].as_string();
                        std::cout << "Raw Mission Config String: " << mission_config_str << std::endl;

                        // Parse the JSON string
                        nlohmann::json mission_config_json = nlohmann::json::parse(mission_config_str);
                        std::cout << "Parsed Mission Config JSON: " << mission_config_json.dump(4) << std::endl;

                        c2_instance->setMissionConfig(mission_config_json);
                        c2_instance->sendInitMission();

                        request.reply(status_codes::OK, U("Mission initialized successfully!"));
                    } 
                    else {
                        // DEBUG: Print message if the fields are not found
                        std::cout << "Either 'mission_id' or 'mission_config' not found in JSON body." << std::endl;
                        request.reply(status_codes::BadRequest, U("Invalid request: missing mission_id or mission_config."));
                    }
                } 
                else {
                    request.reply(status_codes::BadRequest, U("Unknown action"));
                }
            } 
            catch (const std::exception& e) {
                request.reply(status_codes::InternalError, U("Error handling request"));
            }
        }).wait();
    }

private:
    http_listener listener;
    C2* c2_instance;

};
