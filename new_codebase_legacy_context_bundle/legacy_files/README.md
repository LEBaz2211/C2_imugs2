# Multi-Agent Framework

## Clone
```
git clone --recursive https://gitlab.cylab.be/rma-ras/multi-robot-framework/multi-agent-framework.git
```

If you've already cloned the repository without the --recursive option:
```
git submodule update --init --recursive
```

## Overview

The Multi-Agent Framework is a robust and modular system for coordinating multiple vehiclesin various mission scenarios. It was developed as part of the iMUGS (Integrated Modular Unmanned Ground System) project, funded by the European Defense Industrial Development Program (EDIDP), which aims to build a standardized and scalable ecosystem for unmanned systems. 


The framework is designed to enable robust coordination in centralized and decentralized multi-robot settings.
It is structured around a modular architecture. 

## High-level iMUGS Architecture

![High Level Architecture](images/iMUGS_Global_arch.png)
*High-level architecture of the iMUGS system.*

## Multi-Agent Framework Architecture

![Multi-Agent Framework Architecture](images/iMUGS-Multi-Robot-Arch.png)
*Architecture of the Multi-Agent Framework.*


### Fog Module Overview

#### Orchestrator Node
- Acts as the main interface between the **C2 module** and the rest of the Multi-Robot System (MRS).
- Creates a **mission manager** node for each new mission and routes feedback to the C2 module.
- Manages mission descriptions in a dedicated database.

#### Mission Manager Node
- Uses unique UUIDs as namespaces for communication.
- Handles mission state transitions (e.g., initialization, planning, execution).
- Manages mission failures and re-planning as needed.

#### Fleet Manager Node
- Supervises robot readiness, connectivity, and availability.
- Stores fleet data such as location, status, and resources.
- Allocates resources for multiple concurrent missions and resolves conflicts.

Using **ROS2 multi-threaded executors**, it handles parallel mission execution with better scalability, resilience, and throughput for simultaneous missions.


### Edge Module Overview

#### Agent Task Supervisor Node
- Acts as the main interface between the **AUTONOMY module** and the rest of the Multi-Robot System (MRS).
- Supervises agent task execution and routes feedback to the Fog module.


# Working Principle

### Launch

To launch all processes with docker (Recommended), go to the [Full Stack docker-compose.yaml](multi-agent-framework/docker-compose-dir/Simulation-Full-Stack/docker-compose.yaml)



The pipeline is roughly structured as follows:


### Map Features

The C2 operator defines features on the map, which are stored individually in a dedicated featurecollection database. Using standard geojson structures, the map can be augmented with geofences, risks, roads, ... using any type of geometry (Polygon, LineString, MultiPoint, Point, ...). 


![Webapp Map Features](images/map_features.png)
*Webapp Map Features, showing the drawing of a parade geofence polygon.*


### Mission Definition

The operator defines a mission configuration, using a json structure like the following:
```json
{
  "objective": {
    "geometries": [
      {
        "geometry": {
          "coordinates": [
            [
              4.391893297982506,
              50.844115083630555
            ],
            [
              4.391710170382453,
              50.84427476662046
            ],
            [
              4.392039364043669,
              50.844318817004506
            ]
          ],
          "geometry_type": "MultiPoint"
        },
        "_id": "679a44ae9a40cdbbf4cac989"
      }
    ],
    "maximize_coverage": true
  },
  "transit": {
    "desired_vehicle_constraints": {
      "max_speed": 2
    }
  },
  "mission_id": "ac19d601-9473-4bca-a029-e39861a21b1d",
  "behavior": 0,
  "name": "Delivery-MP",
  "vehicles": [
    "4dd12623-3fb6-4ae4-91c2-1f4b10d2327d",
    "2b4a887b-95af-451d-bd85-e0dcacb72524",
    "f9992bb3-9871-451f-90a0-9207eb9fe6c5",
    "8ef41dae-86d0-41f5-a65d-d8cc5bab1cf6"
  ]
}
```

A mission has a unique indentifier (UUID), and we allocate a set of vehicles (also with UUIDs) with a global **behavior** type (navigate-to, explore, map, ...). 

The **objective** property defines the constraints and geometries for the end state. For instance if we have a behavior=0 (navigate-to) and a MultiPoint objective geometry, it means that we want to send our vehicles to these points. If maximize_coverage=True and the objective geometry is a Polygon, we want our robots to go to a state that maximally cover the polygons' area.

The **transit** property defines the constraints and geometries during the motion. For instance if we have a behavior=1 (explore) and a Polygon for the transit geometry with maximize_coverage=true, it means we somehow want to explore this polygon maximally (mine detection survey for instance).

Instead of using **geojson** geometries, the user can also use the **feature_id** of a feature that is registered in the map. In this case the objective geometry could be written as:

```json
"objective": {
    "geometries": [
      {
        "feature_id": "b3b6ead4-14d6-4777-baa1-52bae998744c",
      }
    ]
}
```
which could be any type of feature.

The C2 Webapp stores mission definitions in a dedicated database.
### Mission Management
Once the mission configuration is defined, it can be **submitted** to the Multi-Agent Fog Module. It will automatically create a **mission manager** node for each new mission and request the planner to calculate the individual agent tasks to solve the mission. Once the trajectories (received through the MissionFeedback) are received, the operator can **Approve** the proposed tasks, which will send the tasks to the individual edge modules (the Agent Supervisor Nodes). **Starting** the mission executes the list of objectives for every agent, **Pausing** it only temporarilly stops the agents (by setting a null_objective), **Stopping** the mission stops the agents and deletes the runtime data for that mission (it is not deleted from the C2 mission database).


The **logs** from the Fog Module are sent through and are saved in a dedicated database.
The mission **state machines** can also be visualized on the Webapp.

![Webapp Mission definition and control](images/webapp_mission_def.png)
*Webapp Mission definition and control.*



The ROS nodes and topics can be visualized in the following RQT graph, showing the use of dedicated namespaces for each vehicle and each mission manager node.
![RQT Graph representation](images/rqt_graph_2.png)
*RQT Graph representation of the Multi-Agent Framework ROS2 nodes with two missions.*



### Agent Tasks

The idea behind the execution workflow if the following:

When a mission is planned and accepted (sent to each agent), every agent supervisor node ends up with a **task**. A task is a **sequence** of **objectives**, which are ticked sequentially (behavior tree-like execution).

An objective is composed of **primitives**, based on the agent's skillset. For instance, one primitive type is **"waypoint"**, which is the skill that allows to navigate to a point. Another primitive type would be "search mine" or "follow-me".

- **Tasks**: Contains agent-specific tasks.
- **Primitives**: Atomic actions for each agent.
- **Objectives**: Group primitives with execution parameters.


## Structure Overview

The plan json, given by the planner, contains a `mission_id` and a `tasks` dictionary, where each key corresponds to an agent ID:

```json
{
    "mission_id": "ac19d601-9473-4bca-a029-e39861a21b1d",
    "tasks": {
        "agent_id_1": { ... },
        "agent_id_2": { ... }
    }
}
```
Each agent has a unique `task_id` and a list of `primitives` and `objectives`.

```json
"agent_id_1": {
    "task_id": "2b4ad006-3d8b-4290-9f62-a9fb07987e04",
    "primitives": [ ... ],
    "objectives": [ ... ]
}
```

The primitives list define a lookup table of atomic actions that an agent will execute in some of its objectives. Each primitive includes an ID, type, and execution parameters. This way, the primitive can be reused in the objective descriptions by its primitive_id:

Example of a waypoint primitive:
```json
{
    "primitive_id": "5s4ad006-3d8b-4290-9f62-a9fb07987e44",
    "primitive_type": "waypoint",
    "continuous": false,
    "completion": {
        "ends_objective": true,
        "ends_task": false,
        "followed_by_primitives": [],
        "inherit_other_primitives": false,
        "resume_after": true
    }
}
```

Example of a mine search primitive with parameters:
```json
{
    "primitive_id": "4a4ad006-3d8b-4290-9f62-a9fb07987e07",
    "primitive_type": "search_mine",
    "continuous": true,
    "parameters": {
        "pattern": "zigzag",
        "swath": 5,
        "sensors": ["emi", "gpr", "stereo_cam"]
    },
    "completion": {
        "ends_objective": false,
        "ends_task": false,
        "followed_by_primitives": ["3h4ad006-3d8b-4290-9f62-a9fb07987e59"],
        "inherit_other_primitives": false,
        "resume_after": true
    }
}
```
the **completion** parameters allow to define the graph-based execution scheme based on individual primitive completions. For instance, if a "search_mine" primitive is completed, it will activate a child node executing the primitives in "followed_by_primitives". In this case, it could be "dispose mine", and then rsume the parent node.
Objectives group related primitives together, often executed in sequence or parallel.

```json
{
    "objective_id": "8r4ad006-3d8b-4290-9f62-a9fb07987e02",
    "objective_type": "combined_primitives",
    "parallel_execution": true,
    "primitives": [ ... ]
}
```

Each objective may override parameters for included primitives, such as coordinates and speed:
```json
{
    "primitive_id": "5s4ad006-3d8b-4290-9f62-a9fb07987e44",
    "parameters": {
        "coordinates": [50.844400, 4.392069, 0],
        "speed": 3,
        "max_speed": 5,
        "wait_time": 5
    }
}
```

This way, the execution scheme can be handled like this:

We start with the first objective. If one of its primitives is completed and has "followed_by_primitives", a child node is created that sends new goals to the autonomy module. Based on the "resume_after", the graph traversal will get up the tree untill it finds a resumabe parent. Once the start node (most parent one) is completed, the next objective is started.

Every objective forms a **dynamic execution graph** during runtime depending on the primitive's outcomes, and once a child node is completed, a backtracking traversal is ensuring all ongoing primitives are completed. For continuous primitives like "search mine", which can run indefinitely, the objective needs a complementary primitive like "waypoint" to ensure it doesn't get in an execution deadlock. 