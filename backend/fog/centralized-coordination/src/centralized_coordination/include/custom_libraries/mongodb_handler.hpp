/****************************************************************/
// MongoDB handlers for Swarm Manager
// Enzo Ghizoni & Alexandre La Grappe & Emile Le Flecher  - RMA - alexandre.lagrappe@mil.be or emile.leflecher@mil.be 
// 03.12.2024 - V1.0
/****************************************************************/
#pragma once

#include <cstdint>
#include <string>
#include <iostream>
#include <iterator>

#include "bsoncxx/builder/stream/document.hpp"
#include <bsoncxx/builder/basic/kvp.hpp>
#include "bsoncxx/json.hpp"
#include "bsoncxx/oid.hpp"
#include "mongocxx/client.hpp"
#include "mongocxx/database.hpp"
#include "mongocxx/uri.hpp"
#include "mongocxx/instance.hpp"

#include <nlohmann/json.hpp>


#define OUT

#define OUT

using bsoncxx::builder::stream::close_array;
using bsoncxx::builder::stream::close_document;
using bsoncxx::builder::stream::document;
using bsoncxx::builder::stream::finalize;
using bsoncxx::builder::stream::open_array;
using bsoncxx::builder::stream::open_document;

namespace RuntimeDatabase {
const std::string kMongoDbUri = std::getenv("MONGODB_CONNSTRING"); //  "mongodb://mongodb:27017"; //"mongodb://localhost:27017"; // "mongodb://0.0.0.0:27017"; 
constexpr char kDatabaseName[] = "RuntimeDB";
constexpr char kCollectionMission[] = "MissionConfig";
constexpr char kCollectionPlanning[] = "Planning";
constexpr char kCollectionConnectedVehicles[] = "ConnectedVehicles";

class MongoDbHandler {
 public:
  MongoDbHandler()
      : uri(mongocxx::uri(kMongoDbUri)),
        client(mongocxx::client(uri)),
        db(client[kDatabaseName]) {}

  bool AddObjectInDb(const std::string &objectJson, const std::string &kCollectionName) {
    try {
      mongocxx::collection collection = db[kCollectionName];
      bsoncxx::stdx::optional<mongocxx::result::insert_one> maybe_result = collection.insert_one(bsoncxx::from_json(objectJson));
      if(maybe_result) {
        return maybe_result->inserted_id().get_oid().value.to_string().size() != 0;
      }
      return false;
    } 
    catch(const std::exception& e) {
        std::cerr << "MongoDB Handler ->  Error inserting object into database: " << e.what() << std::endl;
        return false;
    }
  }

  void databaseAddMission(const std::string &missionJson) {
    try {
        this->AddObjectInDb(missionJson, kCollectionMission);
    } catch(const std::exception& e) {
        std::cerr << "MongoDB Handler ->  Error adding mission to database: " << e.what() << std::endl;
    }
  }

  void databaseAddPlanning(const std::string &planningJson) {
    try {
        this->AddObjectInDb(planningJson, kCollectionPlanning);
    } catch(const std::exception& e) {
        std::cerr << "MongoDB Handler ->  Error adding planning to database: " << e.what() << std::endl;
    }
  }
  

  void databaseUpdatePlanning(const std::string &mission_id, const std::string &planningJson){
    try {
        // Create the collection instance
        mongocxx::collection collection = db[kCollectionPlanning];
        // Delete the element with the corresponding ID
        collection.delete_one(document{} << "mission_id" << mission_id << finalize);
        // Create a new element with the information of the new Json
        databaseAddPlanning(planningJson);
    } catch (const std::exception& e) {
        std::cerr << "MongoDB Handler ->  Error in databaseUpdatePlanning: " << e.what() << std::endl;
    }
  }

  void databaseDeleteMission(const std::string &mission_id) {
    try {
        std::cout << "MONGODB LIBRARY: Deleting mission from database" << std::endl;
        mongocxx::collection collection = db[kCollectionMission];
        collection.delete_one(document{} << "mission_id" << mission_id << finalize);
    } catch (const std::exception& e) {
        std::cerr << "MongoDB Handler ->  Error in databaseDeleteMission: " << e.what() << std::endl;
    }
  }

  void databaseUpdateMission(const std::string &mission_id, const std::string &missionJson){
    try {
        // Create the collection instance
        mongocxx::collection collection = db[kCollectionMission];
        // Delete the element with the corresponding ID
        collection.delete_one(document{} << "mission_id" << mission_id << finalize);

        // Create a new element with the information of the new Json
        databaseAddMission(missionJson);
    } catch (const std::exception& e) {
        std::cerr << "MongoDB Handler ->  Error in databaseUpdateMission: " << e.what() << std::endl;
    }
  }

  auto databaseFindObject(const std::string &mission_id, const std::string &kCollectionName) {
    try {
        mongocxx::collection collection = db[kCollectionName];
        bsoncxx::stdx::optional<bsoncxx::document::value> maybe_result =
        //collection.find_one(document{} << "mission_id" << mission_id << finalize);
        collection.find_one(document{} << "mission_id" << mission_id << finalize);
        if(maybe_result) {
            // std::cout << bsoncxx::to_json(*maybe_result) << "\n";
            return bsoncxx::to_json(*maybe_result);
        }
        else{
            const std::string outputJson = "";
            return outputJson;
        }
    } 
    catch (const std::exception& e) {
        std::cerr << "MongoDB Handler ->  Error in databaseFindObject: " << e.what() << std::endl;
    }
  }

  
  auto databaseFindLatestObject(const std::string &mission_id, const std::string &kCollectionName) {
    try {
      mongocxx::collection collection = db[kCollectionName];
      // Create the query filter
      auto filter = document{} << "mission_id"
                              << mission_id << finalize;
      auto order = bsoncxx::builder::stream::document{} << "$natural" << -1 << bsoncxx::builder::stream::finalize;
      auto opts = mongocxx::options::find{};
      opts.sort(order.view());
      opts.limit(1);
      // Execute find with options
      bsoncxx::stdx::optional<bsoncxx::document::value> maybe_result = collection.find_one(filter.view(),opts);

      if(maybe_result) {
        return bsoncxx::to_json(*maybe_result);
      }
      else{
        const std::string outputJson = "";
        return outputJson;
      }
    }
    catch(const std::exception& e) {
      std::cerr << "MongoDB Handler ->  Error occurred in databaseFindLatestObject: " << e.what() << std::endl;
      const std::string outputJson = "";
      return outputJson;
    }
  }


  auto databaseFindMission(const std::string &mission_id) {
    try {
      return this->databaseFindObject(mission_id, kCollectionMission);
    }
    catch(const std::exception& e) {
      std::cerr << "MongoDB Handler ->  Error occurred in databaseFindMission: " << e.what() << std::endl;
      const std::string outputJson = "";
      return outputJson;
    }
  }

  auto databaseFindPlanning(const std::string &mission_id) {
    try {
      return this->databaseFindObject(mission_id, kCollectionPlanning);
    }
    catch(const std::exception& e) {
      std::cerr << "MongoDB Handler ->  Error occurred in databaseFindPlanning: " << e.what() << std::endl;
      const std::string outputJson = "";
      return outputJson;
    }
  }


  auto databaseGetAllMissionIDs() {
    try {
      std::vector<std::string> mission_id_list;
      mongocxx::collection collection = db[kCollectionMission];
      // Execute a query with an empty filter (i.e. get all documents).
      mongocxx::cursor cursor = collection.find({});
      // Iterate the cursor into bsoncxx::document::view objects.
      for (const bsoncxx::document::view& doc : cursor) {
        bsoncxx::document::element mission_id_elem = doc["mission_id"];
        std::string mission_id = mission_id_elem.get_string().value.to_string(); // get_utf8 or get_string
        // std::string mission_id = doc["mission_id"].get_utf8().value; //mission_id_elem.get_value();
        std::cout << "mission_id: " << mission_id << std::endl;
        mission_id_list.push_back(mission_id);
      }
      return mission_id_list;
    }
    catch(const std::exception& e) {
      std::cerr << "MongoDB Handler ->  Error occurred in databaseGetAllMissionIDs: " << e.what() << std::endl;
      std::vector<std::string> empty_list;
      return empty_list;
    }
  }

  void addVehicles(const std::string &mission_id, const std::string &vehicle){
    try{
      mongocxx::collection collection = db[kCollectionMission];
      collection.update_one(
        document{}
            << "mission_id" << mission_id
            << finalize,

        document{}
            << "$push" << open_document
                << "vehicles" << vehicle
            << close_document
            << finalize
      );
    }
    catch(const std::exception& e) {
        std::cerr << "MongoDB Handler ->  Error adding vehicle into database: " << e.what() << std::endl;
    }
  }

  void deleteVehicles(const std::string &mission_id, const std::string &vehicle){
    try{
      mongocxx::collection collection = db[kCollectionMission];
      collection.update_one(
        document{}
            << "mission_id" << mission_id
            << finalize,

        document{}
            << "$pull" << open_document
                << "vehicles" << vehicle
            << close_document
            << finalize
      );
    }
    catch(const std::exception& e) {
        std::cerr << "MongoDB Handler ->  Error deleting vehicle from database: " << e.what() << std::endl;
    }
  }


  void databaseAddConnectedVehicle(const std::string &vehicle_id) {
    try{
      mongocxx::collection collection = db[kCollectionConnectedVehicles];
      collection.delete_one(document{} << "agent_id" << vehicle_id << finalize); // to update it

      using bsoncxx::builder::basic::kvp;
      using bsoncxx::builder::basic::make_document;
      db[kCollectionConnectedVehicles].insert_one(make_document(kvp("agent_id", vehicle_id)));
    }
    catch(const std::exception& e) {
        std::cerr << "MongoDB Handler ->  Error inserting connected vehicle into database: " << e.what() << std::endl;
    }
  }

  void databaseRemoveDisconnectedVehicle(const std::string &vehicle_id) {
    try{
      mongocxx::collection collection = db[kCollectionConnectedVehicles];
      collection.delete_one(document{} << "agent_id" << vehicle_id << finalize);
    }
    catch(const std::exception& e) {
        std::cerr << "MongoDB Handler ->  Error removing disconnected vehicle from database: " << e.what() << std::endl;
    }
  }

  std::vector<std::string> databaseGetConnectedVehicles() {
    std::vector<std::string> agent_id_list;
    try{
      mongocxx::collection collection = db[kCollectionConnectedVehicles];
      mongocxx::cursor cursor = collection.find({});
      for(auto doc : cursor) {
        bsoncxx::document::element agent_id_elem = doc["agent_id"];
        std::string agent_id = agent_id_elem.get_string().value.to_string();
        agent_id_list.push_back(agent_id);
      }
      return agent_id_list;
    }
    catch(const std::exception& e) {
        std::cerr << "MongoDB Handler ->  Error getting connected vehicles from database: " << e.what() << std::endl;
        return agent_id_list;
    }
  }

  // Drop whole collection of connected vehicles
  void databaseDropConnectedVehicles() {
    try{
      db[kCollectionConnectedVehicles].drop();
    }
    catch(const std::exception& e) {
        std::cerr << "MongoDB Handler ->  Error removing all connected vehicles from database: " << e.what() << std::endl;
    }
  }

  private:
    mongocxx::uri uri;
    mongocxx::client client;
    mongocxx::database db;
};
}

namespace VehicleDatabase {
const std::string kMongoDbUri = std::getenv("MONGODB_CONNSTRING"); //  "mongodb://mongodb:27017"; //"mongodb://localhost:27017"; // "mongodb://0.0.0.0:27017"; //"mongodb://mongodb:27017"; 
constexpr char kDatabaseName[] = "VehicleDB";
constexpr char kCollectionVehicles[] = "Vehicles";


class MongoDbHandler {
 public:
  MongoDbHandler()
      : uri(mongocxx::uri(kMongoDbUri)),
        client(mongocxx::client(uri)),
        db(client[kDatabaseName]) {}

  //TODO improve robustness of the functions with try catch statement

  bool AddObjectInDb(const std::string &objectJson, const std::string &kCollectionName) {
    try{
      mongocxx::collection collection = db[kCollectionName];
      bsoncxx::stdx::optional<mongocxx::result::insert_one> maybe_result =
          collection.insert_one(bsoncxx::from_json(objectJson));
      // optional, can just return true by default
      if(maybe_result) {
        return maybe_result->inserted_id().get_oid().value.to_string().size() != 0;
      }
      return false;
    }
    catch(const std::exception& e) {
        std::cerr << "MongoDB Handler ->  Error inserting object into database: " << e.what() << std::endl;
        return false;
    }
  }

  void databaseAddVehicle(const std::string &vehicleJson) {
    this->AddObjectInDb(vehicleJson, kCollectionVehicles);
  }

  

   
  void databaseUpdateVehicle(const std::string &vehicle_id, const std::string &vehicleJson){
    try{
      // Create the collection instance
      mongocxx::collection collection = db[kCollectionVehicles];
      // Delete the element with the corresponding ID
      collection.delete_one(document{} << "agent_id" << vehicle_id << finalize);

      // Create a new element with the information of the new Json
      databaseAddVehicle(vehicleJson);
    }
    catch(const std::exception& e) {
        std::cerr << "MongoDB Handler ->  Error updating vehicle in database: " << e.what() << std::endl;
    }
  }

  void databaseDeleteVehicle(const std::string &vehicle_id) {
    try{
      mongocxx::collection collection = db[kCollectionVehicles];
      collection.delete_one(document{} << "agent_id" << vehicle_id << finalize);
    }
    catch(const std::exception& e) {
        std::cerr << "MongoDB Handler ->  Error removing vehicle from database: " << e.what() << std::endl;
    }
  }
 
  auto databaseFindObject(const std::string &vehicle_id, const std::string &kCollectionName) {
    const std::string emptyJson = "";
    try{
      mongocxx::collection collection = db[kCollectionName];
      bsoncxx::stdx::optional<bsoncxx::document::value> maybe_result =
      collection.find_one(document{} << "agent_id" << vehicle_id << finalize);
      if(maybe_result) {
        // std::cout << bsoncxx::to_json(*maybe_result) << "\n";
        return bsoncxx::to_json(*maybe_result);
      }
      else{
        return emptyJson;
      }
    }
    catch(const std::exception& e) {
        std::cerr << "MongoDB Handler ->  Error finding object in database: " << e.what() << std::endl;
        return emptyJson;
    }
  }

  auto databaseFindVehicle(const std::string &vehicle_id) {
    return this->databaseFindObject(vehicle_id, kCollectionVehicles);
  }

  private:
    mongocxx::uri uri;
    mongocxx::client client;
    mongocxx::database db;
};
}

namespace FeedbackDatabase {
const std::string kMongoDbUri = std::getenv("MONGODB_CONNSTRING"); //  "mongodb://mongodb:27017"; //"mongodb://localhost:27017"; // "mongodb://0.0.0.0:27017"; //"mongodb://mongodb:27017"; 
constexpr char kDatabaseName[] = "RuntimeDB";
constexpr char kCollectionMissionFeedback[] = "MissionFeedback";

class MongoDbHandler {
 public:
  MongoDbHandler()
      : uri(mongocxx::uri(kMongoDbUri)),
        client(mongocxx::client(uri)),
        db(client[kDatabaseName]) {}

  /** Generic Functions **/
  bool AddObjectInDb(const std::string &objectJson, const std::string &kCollectionName) {
    try{
      mongocxx::collection collection = db[kCollectionName];
      bsoncxx::stdx::optional<mongocxx::result::insert_one> maybe_result =
          collection.insert_one(bsoncxx::from_json(objectJson));
      // optional, can just return true by default
      if(maybe_result) {
        return maybe_result->inserted_id().get_oid().value.to_string().size() != 0;
      }
      return false;
    }
    catch(const std::exception& e) {
        std::cerr << "MongoDB Handler ->  Error adding object in feedback database: " << e.what() << std::endl;
        return false;
    }
  }

  auto databaseFindObject(const std::string &mission_id, const std::string &kCollectionName) {
    const std::string emptyJson = "";
    try{
      mongocxx::collection collection = db[kCollectionName];
      bsoncxx::stdx::optional<bsoncxx::document::value> maybe_result =
      //collection.find_one(document{} << "mission_id" << mission_id << finalize);
      collection.find_one(document{} << "mission_id" << mission_id << finalize);
      if(maybe_result) {
        // std::cout << bsoncxx::to_json(*maybe_result) << "\n";
        return bsoncxx::to_json(*maybe_result);
      }
      else{
        return emptyJson;
      }
    }
    catch(const std::exception& e) {
        std::cerr << "MongoDB Handler ->  Error finding object in feedback database: " << e.what() << std::endl;
        return emptyJson;
    }
  }

  auto databaseFindLatestObject(const std::string &mission_id, const std::string &kCollectionName) {
    const std::string emptyJson = "";
    try{
      mongocxx::collection collection = db[kCollectionName];
      // Create the query filter
      auto filter = document{} << "mission_id"
                              << mission_id << finalize;
      auto order = bsoncxx::builder::stream::document{} << "$natural" << -1 << bsoncxx::builder::stream::finalize;
      auto opts = mongocxx::options::find{};
      opts.sort(order.view());
      opts.limit(1);
      // Execute find with options
      bsoncxx::stdx::optional<bsoncxx::document::value> maybe_result = collection.find_one(filter.view(),opts);
      
      if(maybe_result) {
        return bsoncxx::to_json(*maybe_result);
      }
      else{
        return emptyJson;
      }
    }
    catch(const std::exception& e) {
        std::cerr << "MongoDB Handler ->  Error finding latest object in feedback database: " << e.what() << std::endl;
        return emptyJson;
    }
  }

  /** Specific Function for feedbacks **/
  void databaseAddMissionFeedback(const std::string &missionJson) {
    this->AddObjectInDb(missionJson, kCollectionMissionFeedback);
  }

  void databaseUpdateMissionFeedback(const std::string &mission_id, const std::string &missionJson){
    try{
      // Create the collection instance
      mongocxx::collection collection = db[kCollectionMissionFeedback];
      // Delete the element with the corresponding ID
      collection.delete_one(document{} << "mission_id" << mission_id << finalize);

      // Create a new element with the information of the new Json
      databaseAddMissionFeedback(missionJson);
    }
    catch(const std::exception& e) {
        std::cerr << "MongoDB Handler ->  Error updating object in feedback database: " << e.what() << std::endl;
    }
  }

  auto databaseFindMissionFeedback(const std::string &mission_id) {
    return this->databaseFindObject(mission_id, kCollectionMissionFeedback);
  }

  auto databaseFindLatestFeedback(const std::string &mission_id) {
    return this->databaseFindLatestObject(mission_id, kCollectionMissionFeedback);
  }

  private:
    mongocxx::uri uri;
    mongocxx::client client;
    mongocxx::database db;
};
}

namespace LogDatabase {
const std::string kMongoDbUri = std::getenv("MONGODB_CONNSTRING"); //  "mongodb://mongodb:27017"; //"mongodb://localhost:27017"; // "mongodb://0.0.0.0:27017"; //"mongodb://mongodb:27017"; 
constexpr char kDatabaseName[] = "RuntimeDB";
constexpr char kCollectionSwarmLog[] = "Logs";

class MongoDbHandler {
 public:
  MongoDbHandler()
      : uri(mongocxx::uri(kMongoDbUri)),
        client(mongocxx::client(uri)),
        db(client[kDatabaseName]) {}

  /** Generic Functions **/
  bool AddObjectInDb(const std::string &objectJson, const std::string &kCollectionName) {
    try{
      mongocxx::collection collection = db[kCollectionName];
      bsoncxx::stdx::optional<mongocxx::result::insert_one> maybe_result =
          collection.insert_one(bsoncxx::from_json(objectJson));
      // optional, can just return true by default
      if(maybe_result) {
        return maybe_result->inserted_id().get_oid().value.to_string().size() != 0;
      }
      return false;
    }
    catch(const std::exception& e) {
        std::cerr << "MongoDB Handler ->  Error adding object in Log database: " << e.what() << std::endl;
        return false;
    }
  }

  auto databaseFindObject(const std::string &mission_id, const std::string &kCollectionName) {
    const std::string emptyJson = "";
    try{
      mongocxx::collection collection = db[kCollectionName];
      bsoncxx::stdx::optional<bsoncxx::document::value> maybe_result =
      //collection.find_one(document{} << "mission_id" << mission_id << finalize);
      collection.find_one(document{} << "mission_id" << mission_id << finalize);
      if(maybe_result) {
        // std::cout << bsoncxx::to_json(*maybe_result) << "\n";
        return bsoncxx::to_json(*maybe_result);
      }
      else{
        return emptyJson;
      }
    }
    catch(const std::exception& e) {
        std::cerr << "MongoDB Handler ->  Error finding object in Log database: " << e.what() << std::endl;
        return emptyJson;
    }
  }

  auto databaseFindLatestObject(const std::string &mission_id, const std::string &kCollectionName) {
    const std::string emptyJson = "";
    try{
      mongocxx::collection collection = db[kCollectionName];
      // Create the query filter
      auto filter = document{} << "mission_id"
                              << mission_id << finalize;
      auto order = bsoncxx::builder::stream::document{} << "$natural" << -1 << bsoncxx::builder::stream::finalize;
      auto opts = mongocxx::options::find{};
      opts.sort(order.view());
      opts.limit(1);
      // Execute find with options
      bsoncxx::stdx::optional<bsoncxx::document::value> maybe_result = collection.find_one(filter.view(),opts);
      
      if(maybe_result) {
        return bsoncxx::to_json(*maybe_result);
      }
      else{
        return emptyJson;
      }
    }
    catch(const std::exception& e) {
        std::cerr << "MongoDB Handler ->  Error finding latest object in Log database: " << e.what() << std::endl;
        return emptyJson;
    }
  }

  /** Specific Functions for Logs**/
  void databaseAddSwarmLog(const std::string &logJson) {
    this->AddObjectInDb(logJson, kCollectionSwarmLog);
  }

  private:
    mongocxx::uri uri;
    mongocxx::client client;
    mongocxx::database db;
};
}