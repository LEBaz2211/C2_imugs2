# Swarm Edge Client

This project uses ROS2 C++ node(s) to act as the edge module of swarming within the iMUGS project.
The Swarm Edge Client module communicates with Autonomy (also on edge, so locally) and with the Swarm Manager (on the Fog, so remotely). There is one instance of this module for each UGV, running independently of each other. 

The whole communication network is using FASTRTPS dynamic, with eProsima integration service.

The only ROS2 node of this specific module is:
* **agent_ uuid**: swarm edge client node which manages tasks and sends individual waypoints to autonomy.



## Run with Docker-Compose

### Prerequisites

* Docker and docker-compose should be installed
* The docker image of the Swarm Edge Client should be either:
- pulled from the [gitlab container registry](https://gitlab.cylab.be/rma-ras/imugs/swarm_edge_client/container_registry) 
- built locally through the DockerFile with the whole workspace
- loaded from a [compressed .tar](https://docs.docker.com/engine/reference/commandline/save/) file of the image
* The [`docker-compose.yaml`](docker-compose-dir/single-agent-with-autonomy-sim/docker-compose.single-agent-with-autonomy-sim.yaml) and [`config.yaml`](docker-compose-dir/single-agent-with-autonomy-sim/config.yaml) and [`launch_agent_tasks_supervisor.sh`](docker-compose-dir/single-agent-with-autonomy-sim/launch_agent_tasks_supervisor.sh) files should be available in the same working directory


### Run docker-compose

1. Go to docker-compose-dir and navigate to desired configuration (multiple agents, single agent with or without autonomy, ...)
2. Comment/uncomment specific services in the `docker-compose.yaml` file based on desired running modules. The minimum service is the swarm_edge_client. Change the AGENT_ID environment variable here (it should be a uuid)
3. Adapt the `config.yaml` file based on desired parameters. For edge-only testing, set the corresponding parameter to True (the node will then use the given waypoints as a task)
2. With the Docker Plugin in VS Code, right-click on the desired `docker-compose.yaml` and select 'Compose Up' (or in terminal running `docker-compose up` )
3. To view the swarm edge client logs: using Docker Plugin, right-click on swarm_manager container which is running and select "View Logs". Or using terminal: find its contained ID with "docker ps" and run "docker logs --follow <container_id>"
**Comment:** The autonomy simulator node can't differentiate between multiple swarm_edge_clients messages (and vice-versa). 

| Folder                           | Comments                                                                        |
|----------------------------------|---------------------------------------------------------------------------------|
| multiple-agents-sim              | create three instance of swarm-edge-client                                      |
| multiple-agent-sim-with-autonomy | create three instance of swarm-edge-client + autonomy simulation for all agents |
| single-agent                     | create one instance of swarm-edge-client                                        |
| single-agent-with-autonomy-sim   | create one instance of swarm-edge-client + autonomy simulation                  |



## Run with Docker-Compose

### Prerequisites

* Docker and docker-compose should be installed
* The docker image of the edge module should be either:
- pulled from the [gitlab container registry](https://gitlab.cylab.be/rma-ras/imugs/swarm_edge_client/container_registry) 
- built locally through the DockerFile with the whole workspace
- loaded from a [compressed .tar](https://docs.docker.com/engine/reference/commandline/save/) file of the image
* The [`docker-compose.yaml`](docker-compose.yaml) and [`config.yaml`](config.yaml) files should be available in the current working directory


### Run docker-compose
To run docker images with the Docker Plugin in VS Code, right-click on any `docker-compose.yaml` and select 'Compose Up' (or in terminal running `docker-compose up` ).
To view the logs: using Docker Plugin, right-click on swarm_manager container which is running and select "View Logs". Or using terminal: find its contained ID with "docker ps" and run "docker logs --follow <container_id>"

1. Go to docker-compose-dir/multiple-agents-sim-with-autonomy (or another configuration folder)
2. change the `config.yaml` file to change the edge module parameters and the `autonomy_config.yaml` to change the autonomy simulator parameters (like initial position)
3. Run the `docker-compose.yaml` file to start the edge module

Keep in mind that this module is intended to be used with the [swarm manager](https://gitlab.cylab.be/rma-ras/imugs/swarm_manager/) module
## Run locally (not recommended)
### Prerequisites

* Dependencies installed:
```
cd .config/
. install-dependencies.sh
. install-custom-message-packages

```
###  How to run? :

1. Terminal 1 - run the whole Swarm Edge Client module
```
. ros2ws/launch_agent_tasks_supervisor.sh
```

2. (For Testing) Terminal 2 - simulating the autonomy
```
. ros2ws/launch_autonomy_sim.sh
```


## Continuous Integration

See [.gitlab-ci.yml](.gitlab-ci.yml), used for docker-build


## Autonomy Integration Testing Notes


Edge computer french themis :
dotocean@10.128.6.212
1234

amd architecture not working. Use docker-desktop with cross platform builder, follow this tutorial:
https://www.docker.com/blog/multi-arch-images/
then build using:
docker buildx build --platform linux/amd64,linux/arm64 -t gitlab.cylab.be:8081/rma-ras/imugs/swarm_edge_client:xplatform_0.0.6 .

# Custom interface bridging between ROS 1 & 2

Bridge of custom interfaces between ROS 1 & 2 using the ros1_bridge package (https://github.com/ros2/ros1_bridge).

## Video tutorial ROS1-ROS2 bridge:
Tutorial on how to transfer custom messages between ROS 1&2:  
https://www.youtube.com/watch?v=vBlUFIOHEIo

