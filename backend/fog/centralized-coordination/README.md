# Centralized Coordination
cloning: don't forget to pull all submodules after cloning `git submodule update --init --recursive`


This project uses ROS2 C++ nodes to manage multiple ground vehicles within the iMUGS project.
The Swarm Manager module communicates with C2 (command & Control), with the Swarm Planner (developed by dotOcean), which are all collocated on the Fog. The Centralized Coordination Module also communicates with the individual agents (Edge devices) remotely.

The whole communication network is using FASTRTPS dynamic, with eProsima integration service.

The ROS2 nodes spinned by the **executor.cpp** are:
* **C2_interface_node**: ROS2 interfaces with C2 are instantiated here
* **orchestrator_node**: The main processes of the Centralized Coordination are executed here (initializing a mission, adding it to the database, ...)
* **fleet_manager_node**: The interface with the edge devices and the main processes related to sending individual agent tasks and changing task states
* **mission_manager** (multiple instances): One node for each mission is created. Here, the state machine is running for a specific mission and all mission-related processes are manger here (planning a mission, start, pause, stop, delete, ...)
* **planner** ( **! not spinned by executor**): This was dotOcean's task, so only the docker image is available. However, our own version is under development in another git repo. 

MongoDB is used for storing multiple json objects. The different databases are:
1. **RuntimeDB**:
* MissionConfig (=json files gathering all operator-defined mission parameters)
* Planning
2. **RuntimeDB**:
* MissionFeedback (= json files sent to C2 giving feedback about a specific mission)
3. **VehicleDB**:
* Vehicles (= all kind of vehicle information like fuel level, size, constraints, connexion status, ...)


## Run with Docker-Compose

### Prerequisites

* Docker and docker-compose should be installed
* The latest docker image of MongoDB from DockerHub should be pulled
* (optional) [MongoDB Compass](https://www.mongodb.com/docs/compass/master/install/) installed for visualization of the databases
* The docker image of the Swarm Manager should be either:
- pulled from the [gitlab container registry](https://gitlab.cylab.be/rma-ras/imugs/centralized_coordination/container_registry) 
- built locally through the DockerFile with the whole workspace
- loaded from a [compressed .tar](https://docs.docker.com/engine/reference/commandline/save/) file of the image
* The [`docker-compose.yaml`](docker-compose.yaml) and [`config.yaml`](config.yaml) files should be available in the current working directory


### Run docker-compose
To run docker images with the Docker Plugin in VS Code, right-click on any `docker-compose.yaml` and select 'Compose Up' (or in terminal running `docker-compose up` ).
To view the logs: using Docker Plugin, right-click on centralized_coordination container which is running and select "View Logs". Or using terminal: find its contained ID with "docker ps" and run "docker logs --follow <container_id>"

1. Go to docker-compose-dir/centralized_coordination
2. Run the `mongodb-docker-compose.yaml` to run de database independently
3. Run the `docker-compose.yaml` file to start the Centralized Coordination (**! depends on mongodb !**)
4. To have the C2 control, in another terminal, run "docker-compose run --rm c2_sim ". This allows to run the terminal C2 simulator interactively. 
5. To run RMA's planner, go to the planner git repo.

Keep in mind that the centralized_coordination is a submodule, there are other necessary dockers to run to have the full framework.
The [agent tasks supervisor](https://gitlab.cylab.be/rma-ras/multi-robot-framework/submodules/edge-module/agent-tasks-supervisor) git repo includes the edge module to run for each robot, which is needed to initiate a mission involving robots.


## Run locally (not recommended)
### Prerequisites

* Dependencies installed:
```
cd .config/
. install-dependencies.sh
. install-custom-message-packages

```
* (optional) [MongoDB Compass](https://www.mongodb.com/try/download/compass) installed for visualization of the databases


1. Source ROS & install in all Terminals:
```
. /opt/ros/galactic/setup.bash && . install/local_setup.bash
```



2. (optional) Setup FastRTPS:

in all terminals: 
```
export RMW_IMPLEMENTATION="rmw_fastrtps_dynamic_cpp"
```


3. Setup mongoDB:
Choose MongoDB hostname and port:
```
export MONGODB_CONNSTRING=mongodb://localhost:27017
```

Start MongoDB ('start' can be replaced by 'stop' or 'restart'):
```
sudo systemctl start mongod
```

Verify that MongoDB has started successfully:
```
sudo systemctl status mongod
```



4. Terminal 1 - run the whole Centralized Coordination module
```
ros2 run centralized_coordination centralized_coordination_executable
```

#  Testing :

6. Terminal 3 - simulating the planner
```
ros2 run centralized_coordination test_planner_sim
```

7. Terminal 4 - simulating C2
```
ros2 run centralized_coordination test_c2_sim
```

## Continuous Integration

See [.gitlab-ci.yml](.gitlab-ci.yml), used for docker-build


