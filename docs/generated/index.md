# Contract browser

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

Everything is available on this page. Select a tab, then expand only the contracts you need. Browser find (`Ctrl+F` / `Cmd+F`) searches the generated page text.

[Download interface inventory (CSV)](interface-inventory.csv){ .md-button } [Download complete contract model (JSON)](contract-model.json){ .md-button }

!!! info "What is generated"
    Contract definitions, fields, usages, enums, and transitions are statically extracted from the editable source tree and schemas. The navigation payloads are separately labelled evidence from a frozen-reference run; they demonstrate contract compatibility, not current-backend runtime verification.

| HTTP | ROS topics | ROS services | ROS types | States | Enums | Schemas |
|---:|---:|---:|---:|---:|---:|---:|
| 30 | 29 | 18 | 49 | 2 | 20 (1 conflict) | 4 |

Source digest: `27eb96b0901cc31c`

=== "Verified run (24)"

    ## One robot navigating to one Point

    !!! success "Runtime verified"
        The checked-in run reached planner state 2, mission PLANNED(1), and delivered a 10-waypoint route to Themis Fr.
        Source tree: `legacy_ros` · Stack: `docker-compose.legacy-ros.yml` · Evidence: [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:11`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L11)
        This run verifies the frozen compatibility reference, not the current editable backend.

    | Value | Runtime data |
    |---|---|
    | Mission | `44444444-5555-4666-8777-888888888888` |
    | Robot | `Themis Fr` · `f9992bb3-9871-451f-90a0-9207eb9fe6c5` |
    | Start | `[4.392588, 50.844317]` [longitude, latitude] |
    | Destination | `[4.39167, 50.84417]` [longitude, latitude] |
    | Behavior | `0` (NAVIGATE) |
    | Requested speed | `1.3 m/s` |
    | Observed route | `10` waypoints |

    ### Recorded route coordinates

    The verification retained the first two and final coordinates. The seven unrecorded intermediate points are not invented.

    | Recorded position | Longitude | Latitude |
    |---|---:|---:|
    | first | `4.3925979` | `50.8443434` |
    | second | `4.3923021488298595` | `50.8442681286928` |
    | final | `4.391670213379427` | `50.84417059346137` |

    ### Payloads

    ??? abstract "robot discovery · Themis agent returned to the UI adapter"
        **Phase:** robot discovery

        **Evidence class:** `runtime_observed`

        **Applicable contracts:** `GET /api/agents`

        ```json
        {
          "agents": [
            {
              "agent_id": "f9992bb3-9871-451f-90a0-9207eb9fe6c5",
              "name": "Themis Fr",
              "vehicle_type": "UGV",
              "current_location": [
                4.392588,
                50.844317
              ],
              "constraints": {
                "max_speed": 4.5,
                "max_acceleration": 8.0,
                "max_weight": 16.0,
                "max_tilt_angle": 1.8
              },
              "status": "1"
            }
          ]
        }
        ```

        - Coordinates are [longitude, latitude].

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`legacy_ros/config/config_autonomy.yaml:6`](https://github.com/LEBaz2211/C2_imugs2/blob/main/legacy_ros/config/config_autonomy.yaml#L6)

    ??? abstract "robot discovery · Canonical profile for the participating robot"
        **Phase:** robot discovery

        **Evidence class:** `runtime_observed`

        **Applicable contracts:** `AgentProfile`

        ```json
        {
          "agent_id": "f9992bb3-9871-451f-90a0-9207eb9fe6c5",
          "name": "Themis Fr",
          "vehicle_type": "UGV",
          "status": "1",
          "current_location": [
            4.392588,
            50.844317
          ],
          "constraints": {
            "max_speed": 4.5,
            "max_acceleration": 8.0,
            "max_weight": 16.0,
            "max_tilt_angle": 1.8
          }
        }
        ```

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`legacy_ros/config/config_autonomy.yaml:6`](https://github.com/LEBaz2211/C2_imugs2/blob/main/legacy_ros/config/config_autonomy.yaml#L6)

    ??? abstract "robot discovery · Edge publishes the participating robot profile"
        **Phase:** robot discovery

        **Evidence class:** `observed_excerpt`

        **Applicable contracts:** `/multi_robot/edge/agent_profile`

        ```json
        {
          "data": "{\"agent_id\":\"f9992bb3-9871-451f-90a0-9207eb9fe6c5\",\"vehicle_constraints\":{\"max_speed\":{\"linear\":{\"x\":4.5}},\"max_acceleration\":{\"linear\":{\"x\":8.0}}},\"vehicle_info\":{\"fuel_status_pct\":85.0,\"battery_status_pct\":90.0}}"
        }
        ```

        - The JSON string is abridged; the runtime profile also contains angular constraints, dimensions, endurance, and sensors.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`legacy_ros/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:250`](https://github.com/LEBaz2211/C2_imugs2/blob/main/legacy_ros/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L250), [`legacy_ros/config/config_autonomy.yaml:6`](https://github.com/LEBaz2211/C2_imugs2/blob/main/legacy_ros/config/config_autonomy.yaml#L6)

    ??? abstract "robot discovery · Autonomy publishes the Themis vehicle profile"
        **Phase:** robot discovery

        **Evidence class:** `runtime_observed`

        **Applicable contracts:** `autonomy_msgs/msg/VehicleProfile`, `autonomy_msgs/msg/VehicleConstraints`, `autonomy_msgs/msg/VehicleInfo`, `autonomy_msgs/msg/SensorProperties`

        ```json
        {
          "active_autonomy_mode": 1,
          "vehicle_constraints": {
            "max_speed": {
              "linear": {
                "x": 4.5,
                "y": 0.0,
                "z": 0.0
              },
              "angular": {
                "x": 0.0,
                "y": 0.0,
                "z": 0.0
              }
            },
            "max_acceleration": {
              "linear": {
                "x": 8.0,
                "y": 0.0,
                "z": 0.0
              },
              "angular": {
                "x": 0.0,
                "y": 0.0,
                "z": 0.0
              }
            },
            "max_weight": 16.0,
            "max_tilt_angle": 1.8
          },
          "vehicle_info": {
            "vehicle_type": "ugv",
            "fuel_status_pct": 85,
            "fuel_hours": 1.5,
            "battery_status_pct": 90,
            "battery_hours": 3.0,
            "sensor_list": [
              {
                "type": 1,
                "status": 1,
                "field_of_view": [
                  360.0,
                  3.14
                ]
              },
              {
                "type": 2,
                "status": 1,
                "field_of_view": [
                  120.0,
                  2.0
                ]
              },
              {
                "type": 3,
                "status": 1,
                "field_of_view": [
                  180.0,
                  3.14
                ]
              }
            ],
            "vehicle_dimensions": [
              0.9,
              0.6,
              0.55
            ]
          }
        }
        ```

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`legacy_ros/config/config_autonomy.yaml:6`](https://github.com/LEBaz2211/C2_imugs2/blob/main/legacy_ros/config/config_autonomy.yaml#L6)

    ??? abstract "robot discovery · Fleet forwards Themis and its live pose to Planner"
        **Phase:** robot discovery

        **Evidence class:** `observed_excerpt`

        **Applicable contracts:** `/multi_robot/planner/agent`, `centralized_msgs/msg/Agent`

        ```json
        {
          "agent_id": "f9992bb3-9871-451f-90a0-9207eb9fe6c5",
          "agent_profile": "<JSON profile published by Edge>",
          "odometry": {
            "pose": {
              "pose": {
                "position": {
                  "x": 4.392588,
                  "y": 50.844317,
                  "z": 0.0
                }
              }
            }
          }
        }
        ```

        - In this global-coordinate simulation, odometry x is longitude and y is latitude.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:304`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L304)

    ??? abstract "planning · Mission manager requests the configured Themis agent"
        **Phase:** planning

        **Evidence class:** `verified_flow`

        **Applicable contracts:** `multi_robot/fleet_manager/get_agents`, `centralized_msgs/srv/GetAgents`

        ```json
        {
          "request": {
            "agent_id_list": [
              {
                "uuid": [
                  249,
                  153,
                  43,
                  179,
                  152,
                  113,
                  69,
                  31,
                  144,
                  160,
                  146,
                  7,
                  235,
                  159,
                  230,
                  197
                ]
              }
            ]
          },
          "response": {
            "agents": [
              {
                "agent_id": "f9992bb3-9871-451f-90a0-9207eb9fe6c5",
                "agent_profile": "<JSON profile published by Edge>",
                "odometry": {
                  "pose": {
                    "pose": {
                      "position": {
                        "x": 4.392588,
                        "y": 50.844317,
                        "z": 0.0
                      }
                    }
                  }
                }
              }
            ],
            "error_message": "ok"
          }
        }
        ```

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:452`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L452)

    ??? abstract "INIT · Canonical mission submitted to the adapter"
        **Phase:** INIT

        **Evidence class:** `verified_flow`

        **Applicable contracts:** `POST /api/missions/init`, `MissionConfig`

        ```json
        {
          "mission_id": "44444444-5555-4666-8777-888888888888",
          "behavior": 0,
          "vehicles": [
            "f9992bb3-9871-451f-90a0-9207eb9fe6c5"
          ],
          "objective": {
            "geometries": [
              {
                "geometry": {
                  "geometry_type": "Point",
                  "coordinates": [
                    4.39167,
                    50.84417
                  ]
                }
              }
            ]
          },
          "transit": {
            "optimization": {
              "road_usage": 1.0
            },
            "desired_vehicle_constraints": {
              "max_speed": 1.3
            }
          }
        }
        ```

        - The adapter uses canonical optimization; the legacy REST payload below translates it to optimalization.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:108`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L108), [`src/c2_imugs2/infrastructure/legacy/rest.py:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/infrastructure/legacy/rest.py#L1)

    ??? abstract "APPROVE · Approve the planned mission"
        **Phase:** APPROVE

        **Evidence class:** `verified_flow`

        **Applicable contracts:** `POST /api/missions/{mission_id}/approve`

        ```json
        {
          "path": "/api/missions/44444444-5555-4666-8777-888888888888/approve",
          "body": {}
        }
        ```

        - Send only after mission feedback contains a non-empty path and status PLANNED(1).

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:154`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L154)

    ??? abstract "START · Start the accepted mission"
        **Phase:** START

        **Evidence class:** `verified_flow`

        **Applicable contracts:** `POST /api/missions/{mission_id}/start`

        ```json
        {
          "path": "/api/missions/44444444-5555-4666-8777-888888888888/start",
          "body": {}
        }
        ```

        - Send after status ACCEPTED(4) and Edge confirms that the stopped task is installed.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:164`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L164)

    ??? abstract "INIT · Mission initialization on ROS"
        **Phase:** INIT

        **Evidence class:** `verified_flow`

        **Applicable contracts:** `/multi_robot/mission_init_request`, `c2_msgs/msg/InitMissionRequest`, `c2_msgs/srv/InitMission`

        ```json
        {
          "mission_id": {
            "uuid": [
              68,
              68,
              68,
              68,
              85,
              85,
              70,
              102,
              135,
              119,
              136,
              136,
              136,
              136,
              136,
              136
            ]
          },
          "mission_config": "{\"mission_id\":\"44444444-5555-4666-8777-888888888888\",\"behavior\":0,\"vehicles\":[\"f9992bb3-9871-451f-90a0-9207eb9fe6c5\"],\"objective\":{\"geometries\":[{\"geometry\":{\"geometry_type\":\"Point\",\"coordinates\":[4.39167,50.84417]}}]},\"transit\":{\"optimalization\":{\"road_usage\":1.0},\"desired_vehicle_constraints\":{\"max_speed\":1.3}}}"
        }
        ```

        - mission_config is a JSON-encoded string and uses the legacy key optimalization.
        - The UUID byte array decodes to 44444444-5555-4666-8777-888888888888.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:108`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L108)

    ??? abstract "APPROVE · APPROVE status request"
        **Phase:** APPROVE

        **Evidence class:** `verified_flow`

        **Applicable contracts:** `/multi_robot/change_mission_status_request`, `c2_msgs/msg/ChangeMissionStatusRequest`, `c2_msgs/srv/ChangeMissionStatus`, `multi_robot/fleet_manager/change_mission_status`

        ```json
        {
          "mission_id": {
            "uuid": [
              68,
              68,
              68,
              68,
              85,
              85,
              70,
              102,
              135,
              119,
              136,
              136,
              136,
              136,
              136,
              136
            ]
          },
          "mission_request_status": 1
        }
        ```

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:718`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L718)

    ??? abstract "START · START status request"
        **Phase:** START

        **Evidence class:** `verified_flow`

        **Applicable contracts:** `/multi_robot/change_mission_status_request`, `c2_msgs/msg/ChangeMissionStatusRequest`, `c2_msgs/srv/ChangeMissionStatus`, `multi_robot/fleet_manager/change_mission_status`

        ```json
        {
          "mission_id": {
            "uuid": [
              68,
              68,
              68,
              68,
              85,
              85,
              70,
              102,
              135,
              119,
              136,
              136,
              136,
              136,
              136,
              136
            ]
          },
          "mission_request_status": 2
        }
        ```

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:796`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L796)

    ??? abstract "APPROVE · Mission manager accepts the APPROVE transition"
        **Phase:** APPROVE

        **Evidence class:** `verified_flow`

        **Applicable contracts:** `/multi_robot/change_mission_status_response`, `c2_msgs/msg/ChangeMissionStatusResponse`, `c2_msgs/srv/ChangeMissionStatus`

        ```json
        {
          "mission_id": {
            "uuid": [
              68,
              68,
              68,
              68,
              85,
              85,
              70,
              102,
              135,
              119,
              136,
              136,
              136,
              136,
              136,
              136
            ]
          },
          "mission_status": 4,
          "error_message": ""
        }
        ```

        - Mission status 4 is ACCEPTED.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:876`](https://github.com/LEBaz2211/C2_imugs2/blob/main/legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L876)

    ??? abstract "START · Mission manager accepts the START transition"
        **Phase:** START

        **Evidence class:** `verified_flow`

        **Applicable contracts:** `/multi_robot/change_mission_status_response`, `c2_msgs/msg/ChangeMissionStatusResponse`, `c2_msgs/srv/ChangeMissionStatus`

        ```json
        {
          "mission_id": {
            "uuid": [
              68,
              68,
              68,
              68,
              85,
              85,
              70,
              102,
              135,
              119,
              136,
              136,
              136,
              136,
              136,
              136
            ]
          },
          "mission_status": 5,
          "error_message": ""
        }
        ```

        - Mission status 5 is STARTED.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:876`](https://github.com/LEBaz2211/C2_imugs2/blob/main/legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L876)

    ??? abstract "planning · Create the planner for the mission"
        **Phase:** planning

        **Evidence class:** `verified_flow`

        **Applicable contracts:** `/multi_robot/planner/create`, `centralized_msgs/srv/CreatePlanner`

        ```json
        {
          "request": {
            "id": "44444444-5555-4666-8777-888888888888",
            "priority": 0,
            "agents": [
              {
                "agent_id": "f9992bb3-9871-451f-90a0-9207eb9fe6c5",
                "agent_profile": "<JSON vehicle profile>",
                "odometry": {
                  "pose": {
                    "pose": {
                      "position": {
                        "x": 4.392588,
                        "y": 50.844317,
                        "z": 0.0
                      }
                    }
                  }
                }
              }
            ],
            "config": "<legacy mission_config JSON string>"
          },
          "response": {
            "id": "44444444-5555-4666-8777-888888888888",
            "state": 0
          }
        }
        ```

        - The verified run then published planner states 0, 1, and 2 asynchronously.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:475`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L475)

    ??? abstract "planning · Planner reports that the plan cache is ready"
        **Phase:** planning

        **Evidence class:** `runtime_observed`

        **Applicable contracts:** `/multi_robot/planner/state`

        ```json
        {
          "data": "{\"planners\":[{\"mission_id\":\"44444444-5555-4666-8777-888888888888\",\"state\":2}]}"
        }
        ```

        - State 2 was observed, but usable route evidence still comes from non-empty mission feedback waypoints.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:11`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L11)

    ??? abstract "plan retrieval · Observed 10-waypoint plan (recorded coordinate excerpt)"
        **Phase:** plan retrieval

        **Evidence class:** `observed_excerpt`

        **Applicable contracts:** `TaskPlan`

        ```json
        {
          "mission_id": "44444444-5555-4666-8777-888888888888",
          "tasks": {
            "f9992bb3-9871-451f-90a0-9207eb9fe6c5": {
              "task_id": "<generated-task-uuid>",
              "primitives": [
                {
                  "primitive_id": "<generated-primitive-uuid>",
                  "primitive_type": "waypoint",
                  "completion": {
                    "ends_objective": true,
                    "ends_task": false
                  }
                }
              ],
              "objectives": [
                {
                  "objective_id": "<first-generated-objective-uuid>",
                  "parallel_execution": true,
                  "primitives": [
                    {
                      "primitive_id": "<generated-primitive-uuid>",
                      "parameters": {
                        "coordinates": [
                          4.3925979,
                          50.8443434
                        ],
                        "speed": 1.3,
                        "max_speed": 1.3
                      }
                    }
                  ]
                },
                {
                  "objective_id": "<second-generated-objective-uuid>",
                  "parallel_execution": true,
                  "primitives": [
                    {
                      "primitive_id": "<generated-primitive-uuid>",
                      "parameters": {
                        "coordinates": [
                          4.3923021488298595,
                          50.8442681286928
                        ],
                        "speed": 1.3,
                        "max_speed": 1.3
                      }
                    }
                  ]
                },
                {
                  "objective_id": "<final-generated-objective-uuid>",
                  "parallel_execution": true,
                  "primitives": [
                    {
                      "primitive_id": "<generated-primitive-uuid>",
                      "parameters": {
                        "coordinates": [
                          4.391670213379427,
                          50.84417059346137
                        ],
                        "speed": 1.3,
                        "max_speed": 1.3
                      }
                    }
                  ]
                }
              ]
            }
          }
        }
        ```

        - This is deliberately an excerpt: the verified route contained 10 objectives, while the runtime record preserved in the walkthrough names the first two and final coordinates.
        - Generated task, primitive, and objective UUIDs change on every GetPlan serialization.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:599`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L599)

    ??? abstract "plan retrieval · Retrieve the generated robot task"
        **Phase:** plan retrieval

        **Evidence class:** `observed_excerpt`

        **Applicable contracts:** `/multi_robot/planner/get_plan`, `centralized_msgs/srv/GetPlan`

        ```json
        {
          "request": {
            "id": "44444444-5555-4666-8777-888888888888"
          },
          "response": {
            "id": "44444444-5555-4666-8777-888888888888",
            "plan": "<JSON-encoded TaskPlan containing one Themis task and 10 waypoint objectives>"
          }
        }
        ```

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:641`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L641)

    ??? abstract "PLANNED · Mission feedback proving that a route was received"
        **Phase:** PLANNED

        **Evidence class:** `observed_excerpt`

        **Applicable contracts:** `/multi_robot/mission_feedback`, `c2_msgs/msg/MissionFeedback`

        ```json
        {
          "mission_id": {
            "uuid": [
              68,
              68,
              68,
              68,
              85,
              85,
              70,
              102,
              135,
              119,
              136,
              136,
              136,
              136,
              136,
              136
            ]
          },
          "mission_feedback": "{\"mission_id\":\"44444444-5555-4666-8777-888888888888\",\"behavior\":0,\"status\":1,\"requested_status\":0,\"tasks\":[{\"vehicle_id\":\"f9992bb3-9871-451f-90a0-9207eb9fe6c5\",\"task_id\":\"<generated-task-uuid>\",\"waypoints\":[{\"coordinates\":[50.8443434,4.3925979]},{\"coordinates\":[50.84417059346137,4.391670213379427]}]}]}"
        }
        ```

        - The JSON string is abridged from 10 waypoints.
        - Legacy MissionFeedback serializes waypoint coordinates as [latitude, longitude]; the adapter swaps them back to [longitude, latitude].

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:678`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L678)

    ??? abstract "APPROVE · Fleet installs the stopped waypoint task on Themis"
        **Phase:** APPROVE

        **Evidence class:** `observed_excerpt`

        **Applicable contracts:** `multi_robot/edge/agent_{agent_id}/add_task`, `task_msgs/srv/AddTask`

        ```json
        {
          "request": {
            "task_id": "<generated-task-uuid>",
            "task_type": 0,
            "override": true,
            "task_config": "{\"primitives\":[{\"primitive_id\":\"<generated-primitive-uuid>\",\"primitive_type\":\"waypoint\"}],\"objectives\":[{\"objective_id\":\"<first-generated-objective-uuid>\",\"primitives\":[{\"primitive_id\":\"<generated-primitive-uuid>\",\"parameters\":{\"coordinates\":[4.3925979,50.8443434],\"speed\":1.3,\"max_speed\":1.3}}]}]}",
            "std": ""
          },
          "response": {
            "task_id": "<generated-task-uuid>",
            "task_state": 0
          }
        }
        ```

        - task_config is an abridged JSON string; the real task contained 10 waypoint objectives.
        - Task state 0 is STOPPED: APPROVE installs the task but does not move the robot.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:750`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L750)

    ??? abstract "APPROVE · Mission manager asks Fleet to dispatch the stored plan"
        **Phase:** APPROVE

        **Evidence class:** `verified_flow`

        **Applicable contracts:** `multi_robot/fleet_manager/send_tasks`, `c2_msgs/srv/InitMission`

        ```json
        {
          "request": {
            "mission_id": {
              "uuid": [
                68,
                68,
                68,
                68,
                85,
                85,
                70,
                102,
                135,
                119,
                136,
                136,
                136,
                136,
                136,
                136
              ]
            },
            "mission_config": ""
          },
          "response": {
            "mission_id": {
              "uuid": [
                68,
                68,
                68,
                68,
                85,
                85,
                70,
                102,
                135,
                119,
                136,
                136,
                136,
                136,
                136,
                136
              ]
            },
            "mission_feedback": ""
          }
        }
        ```

        - This service reuses InitMission.srv, but both string fields are intentionally empty; Fleet reloads the plan from RuntimeDB.Planning by mission ID.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:1056`](https://github.com/LEBaz2211/C2_imugs2/blob/main/legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L1056), [`legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:469`](https://github.com/LEBaz2211/C2_imugs2/blob/main/legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L469)

    ??? abstract "START · Fleet starts the installed Themis task"
        **Phase:** START

        **Evidence class:** `verified_flow`

        **Applicable contracts:** `task_msgs/srv/ChangeTaskState`

        ```json
        {
          "request": {
            "task_id": "<generated-task-uuid>",
            "task_requested_state": 1
          },
          "response": {
            "task_id": "<generated-task-uuid>",
            "task_state": 1,
            "feedback": ""
          }
        }
        ```

        - task_requested_state 1 is EXECUTE; task_state 1 is STARTED.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:818`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L818)

    ??? abstract "execution · Edge sends the current waypoint to autonomy"
        **Phase:** execution

        **Evidence class:** `observed_excerpt`

        **Applicable contracts:** `autonomy_msgs/msg/AutonomySetObjective`, `autonomy_msgs/msg/AutonomyObjective`

        ```json
        {
          "null_objective": false,
          "objective": {
            "id": "<first-generated-objective-uuid>",
            "objective_type": "combined_primitives",
            "parallel_execution": true,
            "primitives": [
              "{\"id\":\"<generated-primitive-uuid>\",\"type\":\"waypoint\",\"parameters\":{\"coordinates\":[4.3925979,50.8443434],\"speed\":1.3,\"max_speed\":1.3,\"mobility_profile\":0,\"wait_time\":0}}"
            ],
            "max_speed": 1.3,
            "mobility_profile": 0
          }
        }
        ```

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:850`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L850)

    ??? abstract "COMPLETED · Themis reports completion after the final waypoint"
        **Phase:** COMPLETED

        **Evidence class:** `verified_flow`

        **Applicable contracts:** `/multi_robot/edge/feedback`, `task_msgs/msg/Feedback`, `task_msgs/msg/TaskFeedback`

        ```json
        {
          "agent_id": "f9992bb3-9871-451f-90a0-9207eb9fe6c5",
          "state": 1,
          "tasks": [
            {
              "task_id": "<generated-task-uuid>",
              "task_state": 3,
              "current_objective_id": "<final-generated-objective-uuid>"
            }
          ],
          "odometry": {
            "pose": {
              "pose": {
                "position": {
                  "x": 4.391670213379427,
                  "y": 50.84417059346137,
                  "z": 0.0
                }
              }
            }
          }
        }
        ```

        - Task state 3 is COMPLETED. The mission manager then transitions the one-robot mission to COMPLETED(10).

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:918`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L918)


=== "Data flow (50)"

    ## Module data flow extracted from code

    Arrows are generated by pairing callers with handlers, publishers with subscribers, and service callers with providers using the exact interface names found in source. They are regenerated whenever MkDocs builds.

    !!! note "Static boundary"
        A dashed endpoint means only one side of that exact interface name was statically extracted. This commonly occurs where ROS names are assembled dynamically; the generator does not invent the missing link.

    ### Module overview

    ```mermaid
    flowchart LR
      N_component_api["FastAPI Adapter"]
      N_component_c2_rest["Old REST Bridge"]
      N_component_centralized["Centralized Coordination"]
      N_component_edge["Edge Supervisor"]
      N_component_fleet["Fleet Manager"]
      N_component_planner["Legacy Planner"]
      N_component_ui["Browser UI"]
      N_component_c2_rest -->|topics 2| N_component_centralized
      N_component_centralized -->|topics 2| N_component_c2_rest
      N_component_centralized -->|services 3| N_component_fleet
      N_component_centralized -->|services 2| N_component_planner
      N_component_edge -->|topics 1| N_component_centralized
      N_component_edge -->|topics 2| N_component_fleet
      N_component_fleet -->|topics 1| N_component_centralized
      N_component_fleet -->|services 3 · topics 1| N_component_edge
      N_component_fleet -->|topics 1| N_component_planner
      N_component_planner -->|topics 1| N_component_centralized
      N_component_ui -->|HTTP 24| N_component_api
    ```

    The counts represent distinct exact interface contracts, not message volume.

    ### Verified Themis navigation path

    This view filters the extracted flows to interfaces carrying data recorded in the checked-in single-robot test.

    ```mermaid
    flowchart LR
      classDef unresolved stroke-dasharray: 5 5,fill:transparent
      N_component_api["FastAPI Adapter"]
      N_component_c2_rest["Old REST Bridge"]
      N_component_centralized["Centralized Coordination"]
      N_component_edge["Edge Supervisor"]
      N_component_fleet["Fleet Manager"]
      N_component_planner["Legacy Planner"]
      N_component_ui["Browser UI"]
      FLOW_0(["GET /api/agents"])
      UNRESOLVED_IN_0["producer not statically paired"] -.-> FLOW_0
      class UNRESOLVED_IN_0 unresolved
      FLOW_0 --> N_component_api
      FLOW_1(["POST /api/missions/init"])
      N_component_ui --> FLOW_1
      FLOW_1 --> N_component_api
      FLOW_2(["POST /api/missions/{mission_id}/approve"])
      N_component_ui --> FLOW_2
      FLOW_2 --> N_component_api
      FLOW_3(["POST /api/missions/{mission_id}/start"])
      N_component_ui --> FLOW_3
      FLOW_3 --> N_component_api
      FLOW_4(["/multi_robot/planner/create<br/>centralized_msgs/srv/CreatePlanner"])
      N_component_centralized --> FLOW_4
      FLOW_4 --> N_component_planner
      FLOW_5(["/multi_robot/planner/get_plan<br/>centralized_msgs/srv/GetPlan"])
      N_component_centralized --> FLOW_5
      FLOW_5 --> N_component_planner
      FLOW_6(["multi_robot/edge/agent_{agent_id}/add_task<br/>task_msgs/srv/AddTask"])
      N_component_fleet --> FLOW_6
      FLOW_6 --> N_component_edge
      FLOW_7(["multi_robot/fleet_manager/change_mission_status<br/>c2_msgs/srv/ChangeMissionStatus"])
      N_component_centralized --> FLOW_7
      FLOW_7 --> N_component_fleet
      FLOW_8(["multi_robot/fleet_manager/get_agents<br/>centralized_msgs/srv/GetAgents"])
      N_component_centralized --> FLOW_8
      FLOW_8 --> N_component_fleet
      FLOW_9(["multi_robot/fleet_manager/send_tasks<br/>c2_msgs/srv/InitMission"])
      N_component_centralized --> FLOW_9
      FLOW_9 --> N_component_fleet
      FLOW_10(["/multi_robot/change_mission_status_request<br/>c2_msgs/msg/ChangeMissionStatusRequest"])
      N_component_c2_rest --> FLOW_10
      FLOW_10 --> N_component_centralized
      FLOW_11(["/multi_robot/change_mission_status_response<br/>c2_msgs/msg/ChangeMissionStatusResponse"])
      N_component_centralized --> FLOW_11
      FLOW_11 --> N_component_c2_rest
      FLOW_12(["/multi_robot/edge/agent_profile<br/>std_msgs/msg/String"])
      N_component_edge --> FLOW_12
      FLOW_12 --> N_component_fleet
      FLOW_13(["/multi_robot/edge/feedback<br/>task_msgs/msg/Feedback"])
      N_component_edge --> FLOW_13
      FLOW_13 --> N_component_centralized
      FLOW_13 --> N_component_fleet
      FLOW_14(["/multi_robot/mission_feedback<br/>c2_msgs/msg/MissionFeedback"])
      N_component_centralized --> FLOW_14
      FLOW_14 -.-> UNRESOLVED_OUT_14["consumer not statically paired"]
      class UNRESOLVED_OUT_14 unresolved
      FLOW_15(["/multi_robot/mission_init_request<br/>c2_msgs/msg/InitMissionRequest"])
      N_component_c2_rest --> FLOW_15
      FLOW_15 --> N_component_centralized
      FLOW_16(["/multi_robot/planner/agent<br/>centralized_msgs/msg/Agent"])
      N_component_fleet --> FLOW_16
      FLOW_16 --> N_component_planner
      FLOW_17(["/multi_robot/planner/state<br/>std_msgs/msg/String"])
      N_component_planner --> FLOW_17
      FLOW_17 --> N_component_centralized
    ```

    ### Data structures and real examples

    ??? abstract "GET /api/agents · http_endpoint"
        **Flow:** _not statically paired_ → `FastAPI Adapter`

        **Contract kind:** `http_endpoint`

        **Data type:** `not declared on this interface`

        #### Verified navigation data

        ##### Themis agent returned to the UI adapter

        Phase: **robot discovery** · Evidence class: `runtime_observed`

        ```json
        {
          "agents": [
            {
              "agent_id": "f9992bb3-9871-451f-90a0-9207eb9fe6c5",
              "name": "Themis Fr",
              "vehicle_type": "UGV",
              "current_location": [
                4.392588,
                50.844317
              ],
              "constraints": {
                "max_speed": 4.5,
                "max_acceleration": 8.0,
                "max_weight": 16.0,
                "max_tilt_angle": 1.8
              },
              "status": "1"
            }
          ]
        }
        ```

        - Coordinates are [longitude, latitude].

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`legacy_ros/config/config_autonomy.yaml:6`](https://github.com/LEBaz2211/C2_imugs2/blob/main/legacy_ros/config/config_autonomy.yaml#L6)

        #### Source evidence

        - [`src/c2_imugs2/api/app.py:346`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/app.py#L346)

    ??? abstract "POST /api/missions/init · http_endpoint"
        **Flow:** `Browser UI` → `FastAPI Adapter`

        **Contract kind:** `http_endpoint`

        **Data type:** `not declared on this interface`

        #### Verified navigation data

        ##### Canonical mission submitted to the adapter

        Phase: **INIT** · Evidence class: `verified_flow`

        ```json
        {
          "mission_id": "44444444-5555-4666-8777-888888888888",
          "behavior": 0,
          "vehicles": [
            "f9992bb3-9871-451f-90a0-9207eb9fe6c5"
          ],
          "objective": {
            "geometries": [
              {
                "geometry": {
                  "geometry_type": "Point",
                  "coordinates": [
                    4.39167,
                    50.84417
                  ]
                }
              }
            ]
          },
          "transit": {
            "optimization": {
              "road_usage": 1.0
            },
            "desired_vehicle_constraints": {
              "max_speed": 1.3
            }
          }
        }
        ```

        - The adapter uses canonical optimization; the legacy REST payload below translates it to optimalization.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:108`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L108), [`src/c2_imugs2/infrastructure/legacy/rest.py:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/infrastructure/legacy/rest.py#L1)

        #### Source evidence

        - [`src/c2_imugs2/api/routers.py:193`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L193)
        - [`frontend/src/api.ts:621`](https://github.com/LEBaz2211/C2_imugs2/blob/main/frontend/src/api.ts#L621)

    ??? abstract "POST /api/missions/{mission_id}/approve · http_endpoint"
        **Flow:** `Browser UI` → `FastAPI Adapter`

        **Contract kind:** `http_endpoint`

        **Data type:** `not declared on this interface`

        #### Verified navigation data

        ##### Approve the planned mission

        Phase: **APPROVE** · Evidence class: `verified_flow`

        ```json
        {
          "path": "/api/missions/44444444-5555-4666-8777-888888888888/approve",
          "body": {}
        }
        ```

        - Send only after mission feedback contains a non-empty path and status PLANNED(1).

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:154`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L154)

        #### Source evidence

        - [`src/c2_imugs2/api/routers.py:208`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L208)
        - [`frontend/src/api.ts:629`](https://github.com/LEBaz2211/C2_imugs2/blob/main/frontend/src/api.ts#L629)

    ??? abstract "POST /api/missions/{mission_id}/start · http_endpoint"
        **Flow:** `Browser UI` → `FastAPI Adapter`

        **Contract kind:** `http_endpoint`

        **Data type:** `not declared on this interface`

        #### Verified navigation data

        ##### Start the accepted mission

        Phase: **START** · Evidence class: `verified_flow`

        ```json
        {
          "path": "/api/missions/44444444-5555-4666-8777-888888888888/start",
          "body": {}
        }
        ```

        - Send after status ACCEPTED(4) and Edge confirms that the stopped task is installed.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:164`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L164)

        #### Source evidence

        - [`src/c2_imugs2/api/routers.py:215`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L215)
        - [`frontend/src/api.ts:633`](https://github.com/LEBaz2211/C2_imugs2/blob/main/frontend/src/api.ts#L633)

    ??? abstract "/multi_robot/planner/create · centralized_msgs/srv/CreatePlanner"
        **Flow:** `Centralized Coordination` → `Legacy Planner`

        **Contract kind:** `ros_service`

        **Data type:** `centralized_msgs/srv/CreatePlanner`

        #### Extracted fields

        | Section | Type | Name |
        |---|---|---|
        | request | `string` | `id` |
        | request | `uint8` | `priority` |
        | request | `Agent[]` | `agents` |
        | request | `string` | `config` |
        | response | `string` | `id` |
        | response | `uint8` | `state` |

        #### Verified navigation data

        ##### Create the planner for the mission

        Phase: **planning** · Evidence class: `verified_flow`

        ```json
        {
          "request": {
            "id": "44444444-5555-4666-8777-888888888888",
            "priority": 0,
            "agents": [
              {
                "agent_id": "f9992bb3-9871-451f-90a0-9207eb9fe6c5",
                "agent_profile": "<JSON vehicle profile>",
                "odometry": {
                  "pose": {
                    "pose": {
                      "position": {
                        "x": 4.392588,
                        "y": 50.844317,
                        "z": 0.0
                      }
                    }
                  }
                }
              }
            ],
            "config": "<legacy mission_config JSON string>"
          },
          "response": {
            "id": "44444444-5555-4666-8777-888888888888",
            "state": 0
          }
        }
        ```

        - The verified run then published planner states 0, 1, and 2 asynchronously.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:475`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L475)

        #### Source evidence

        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:56`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L56)
        - [`backend/fog/planner/ros2ws/src/planner/planner/planner_node.py:141`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/planner/planner/planner_node.py#L141)

    ??? abstract "/multi_robot/planner/get_plan · centralized_msgs/srv/GetPlan"
        **Flow:** `Centralized Coordination` → `Legacy Planner`

        **Contract kind:** `ros_service`

        **Data type:** `centralized_msgs/srv/GetPlan`

        #### Extracted fields

        | Section | Type | Name |
        |---|---|---|
        | request | `string` | `id` |
        | response | `string` | `id` |
        | response | `string` | `plan` |

        #### Verified navigation data

        ##### Retrieve the generated robot task

        Phase: **plan retrieval** · Evidence class: `observed_excerpt`

        ```json
        {
          "request": {
            "id": "44444444-5555-4666-8777-888888888888"
          },
          "response": {
            "id": "44444444-5555-4666-8777-888888888888",
            "plan": "<JSON-encoded TaskPlan containing one Themis task and 10 waypoint objectives>"
          }
        }
        ```

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:641`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L641)

        #### Source evidence

        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:53`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L53)
        - [`backend/fog/planner/ros2ws/src/planner/planner/planner_node.py:144`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/planner/planner/planner_node.py#L144)

    ??? abstract "multi_robot/edge/agent_{agent_id}/add_task · task_msgs/srv/AddTask"
        **Flow:** `Fleet Manager` → `Edge Supervisor`

        **Contract kind:** `ros_service`

        **Data type:** `task_msgs/srv/AddTask`

        #### Extracted fields

        | Section | Type | Name |
        |---|---|---|
        | request | `string` | `task_id` |
        | request | `uint8` | `task_type` |
        | request | `bool` | `override` |
        | request | `string<=1048576` | `task_config` |
        | request | `string` | `std` |
        | response | `string` | `task_id` |
        | response | `uint8` | `task_state` |

        #### Verified navigation data

        ##### Fleet installs the stopped waypoint task on Themis

        Phase: **APPROVE** · Evidence class: `observed_excerpt`

        ```json
        {
          "request": {
            "task_id": "<generated-task-uuid>",
            "task_type": 0,
            "override": true,
            "task_config": "{\"primitives\":[{\"primitive_id\":\"<generated-primitive-uuid>\",\"primitive_type\":\"waypoint\"}],\"objectives\":[{\"objective_id\":\"<first-generated-objective-uuid>\",\"primitives\":[{\"primitive_id\":\"<generated-primitive-uuid>\",\"parameters\":{\"coordinates\":[4.3925979,50.8443434],\"speed\":1.3,\"max_speed\":1.3}}]}]}",
            "std": ""
          },
          "response": {
            "task_id": "<generated-task-uuid>",
            "task_state": 0
          }
        }
        ```

        - task_config is an abridged JSON string; the real task contained 10 waypoint objectives.
        - Task state 0 is STOPPED: APPROVE installs the task but does not move the robot.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:750`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L750)

        #### Source evidence

        - [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:89`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L89)
        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:339`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L339)

    ??? abstract "multi_robot/fleet_manager/change_mission_status · c2_msgs/srv/ChangeMissionStatus"
        **Flow:** `Centralized Coordination` → `Fleet Manager`

        **Contract kind:** `ros_service`

        **Data type:** `c2_msgs/srv/ChangeMissionStatus`

        #### Extracted fields

        | Section | Type | Name |
        |---|---|---|
        | request | `unique_identifier_msgs/UUID` | `mission_id` |
        | request | `uint8` | `mission_request_status` |
        | response | `unique_identifier_msgs/UUID` | `mission_id` |
        | response | `uint8` | `mission_status` |
        | response | `string<=2000` | `error_message` |

        #### Verified navigation data

        ##### APPROVE status request

        Phase: **APPROVE** · Evidence class: `verified_flow`

        ```json
        {
          "mission_id": {
            "uuid": [
              68,
              68,
              68,
              68,
              85,
              85,
              70,
              102,
              135,
              119,
              136,
              136,
              136,
              136,
              136,
              136
            ]
          },
          "mission_request_status": 1
        }
        ```

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:718`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L718)

        ##### START status request

        Phase: **START** · Evidence class: `verified_flow`

        ```json
        {
          "mission_id": {
            "uuid": [
              68,
              68,
              68,
              68,
              85,
              85,
              70,
              102,
              135,
              119,
              136,
              136,
              136,
              136,
              136,
              136
            ]
          },
          "mission_request_status": 2
        }
        ```

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:796`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L796)

        #### Source evidence

        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:93`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L93)
        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:64`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L64)

    ??? abstract "multi_robot/fleet_manager/get_agents · centralized_msgs/srv/GetAgents"
        **Flow:** `Centralized Coordination` → `Fleet Manager`

        **Contract kind:** `ros_service`

        **Data type:** `centralized_msgs/srv/GetAgents`

        #### Extracted fields

        | Section | Type | Name |
        |---|---|---|
        | request | `unique_identifier_msgs/UUID[]` | `agent_id_list` |
        | response | `centralized_msgs/Agent[]` | `agents` |
        | response | `string<=2000` | `error_message` |

        #### Verified navigation data

        ##### Mission manager requests the configured Themis agent

        Phase: **planning** · Evidence class: `verified_flow`

        ```json
        {
          "request": {
            "agent_id_list": [
              {
                "uuid": [
                  249,
                  153,
                  43,
                  179,
                  152,
                  113,
                  69,
                  31,
                  144,
                  160,
                  146,
                  7,
                  235,
                  159,
                  230,
                  197
                ]
              }
            ]
          },
          "response": {
            "agents": [
              {
                "agent_id": "f9992bb3-9871-451f-90a0-9207eb9fe6c5",
                "agent_profile": "<JSON profile published by Edge>",
                "odometry": {
                  "pose": {
                    "pose": {
                      "position": {
                        "x": 4.392588,
                        "y": 50.844317,
                        "z": 0.0
                      }
                    }
                  }
                }
              }
            ],
            "error_message": "ok"
          }
        }
        ```

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:452`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L452)

        #### Source evidence

        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:87`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L87)
        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:60`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L60)

    ??? abstract "multi_robot/fleet_manager/send_tasks · c2_msgs/srv/InitMission"
        **Flow:** `Centralized Coordination` → `Fleet Manager`

        **Contract kind:** `ros_service`

        **Data type:** `c2_msgs/srv/InitMission`

        #### Extracted fields

        | Section | Type | Name |
        |---|---|---|
        | request | `unique_identifier_msgs/UUID` | `mission_id` |
        | request | `string<=10000` | `mission_config` |
        | response | `unique_identifier_msgs/UUID` | `mission_id` |
        | response | `string<=10000` | `mission_feedback` |

        #### Verified navigation data

        ##### Mission manager asks Fleet to dispatch the stored plan

        Phase: **APPROVE** · Evidence class: `verified_flow`

        ```json
        {
          "request": {
            "mission_id": {
              "uuid": [
                68,
                68,
                68,
                68,
                85,
                85,
                70,
                102,
                135,
                119,
                136,
                136,
                136,
                136,
                136,
                136
              ]
            },
            "mission_config": ""
          },
          "response": {
            "mission_id": {
              "uuid": [
                68,
                68,
                68,
                68,
                85,
                85,
                70,
                102,
                135,
                119,
                136,
                136,
                136,
                136,
                136,
                136
              ]
            },
            "mission_feedback": ""
          }
        }
        ```

        - This service reuses InitMission.srv, but both string fields are intentionally empty; Fleet reloads the plan from RuntimeDB.Planning by mission ID.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:1056`](https://github.com/LEBaz2211/C2_imugs2/blob/main/legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L1056), [`legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:469`](https://github.com/LEBaz2211/C2_imugs2/blob/main/legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L469)

        #### Source evidence

        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:90`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L90)
        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:62`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L62)

    ??? abstract "/multi_robot/change_mission_status_request · c2_msgs/msg/ChangeMissionStatusRequest"
        **Flow:** `Old REST Bridge` → `Centralized Coordination`

        **Contract kind:** `ros_topic`

        **Data type:** `c2_msgs/msg/ChangeMissionStatusRequest`

        #### Extracted fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `mission_id` |
        | message | `uint8` | `mission_request_status` |

        #### Verified navigation data

        ##### APPROVE status request

        Phase: **APPROVE** · Evidence class: `verified_flow`

        ```json
        {
          "mission_id": {
            "uuid": [
              68,
              68,
              68,
              68,
              85,
              85,
              70,
              102,
              135,
              119,
              136,
              136,
              136,
              136,
              136,
              136
            ]
          },
          "mission_request_status": 1
        }
        ```

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:718`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L718)

        ##### START status request

        Phase: **START** · Evidence class: `verified_flow`

        ```json
        {
          "mission_id": {
            "uuid": [
              68,
              68,
              68,
              68,
              85,
              85,
              70,
              102,
              135,
              119,
              136,
              136,
              136,
              136,
              136,
              136
            ]
          },
          "mission_request_status": 2
        }
        ```

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:796`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L796)

        #### Source evidence

        - [`backend/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/c2_rest.cpp:58`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/c2_rest.cpp#L58)
        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:57`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L57)

    ??? abstract "/multi_robot/change_mission_status_response · c2_msgs/msg/ChangeMissionStatusResponse"
        **Flow:** `Centralized Coordination` → `Old REST Bridge`

        **Contract kind:** `ros_topic`

        **Data type:** `c2_msgs/msg/ChangeMissionStatusResponse`

        #### Extracted fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `mission_id` |
        | message | `uint8` | `mission_status` |
        | message | `string<=2000` | `error_message` |

        #### Verified navigation data

        ##### Mission manager accepts the APPROVE transition

        Phase: **APPROVE** · Evidence class: `verified_flow`

        ```json
        {
          "mission_id": {
            "uuid": [
              68,
              68,
              68,
              68,
              85,
              85,
              70,
              102,
              135,
              119,
              136,
              136,
              136,
              136,
              136,
              136
            ]
          },
          "mission_status": 4,
          "error_message": ""
        }
        ```

        - Mission status 4 is ACCEPTED.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:876`](https://github.com/LEBaz2211/C2_imugs2/blob/main/legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L876)

        ##### Mission manager accepts the START transition

        Phase: **START** · Evidence class: `verified_flow`

        ```json
        {
          "mission_id": {
            "uuid": [
              68,
              68,
              68,
              68,
              85,
              85,
              70,
              102,
              135,
              119,
              136,
              136,
              136,
              136,
              136,
              136
            ]
          },
          "mission_status": 5,
          "error_message": ""
        }
        ```

        - Mission status 5 is STARTED.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:876`](https://github.com/LEBaz2211/C2_imugs2/blob/main/legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L876)

        #### Source evidence

        - [`backend/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/c2_rest.cpp:57`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/c2_rest.cpp#L57)
        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:137`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L137)
        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:58`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L58)

    ??? abstract "/multi_robot/edge/agent_profile · std_msgs/msg/String"
        **Flow:** `Edge Supervisor` → `Fleet Manager`

        **Contract kind:** `ros_topic`

        **Data type:** `std_msgs/msg/String`

        #### Extracted fields

        | Section | Type | Name |
        |---|---|---|
        | message | `string` | `data` |

        #### Verified navigation data

        ##### Edge publishes the participating robot profile

        Phase: **robot discovery** · Evidence class: `observed_excerpt`

        ```json
        {
          "data": "{\"agent_id\":\"f9992bb3-9871-451f-90a0-9207eb9fe6c5\",\"vehicle_constraints\":{\"max_speed\":{\"linear\":{\"x\":4.5}},\"max_acceleration\":{\"linear\":{\"x\":8.0}}},\"vehicle_info\":{\"fuel_status_pct\":85.0,\"battery_status_pct\":90.0}}"
        }
        ```

        - The JSON string is abridged; the runtime profile also contains angular constraints, dimensions, endurance, and sensors.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`legacy_ros/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:250`](https://github.com/LEBaz2211/C2_imugs2/blob/main/legacy_ros/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L250), [`legacy_ros/config/config_autonomy.yaml:6`](https://github.com/LEBaz2211/C2_imugs2/blob/main/legacy_ros/config/config_autonomy.yaml#L6)

        #### Source evidence

        - [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:82`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L82)
        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:77`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L77)

    ??? abstract "/multi_robot/edge/feedback · task_msgs/msg/Feedback"
        **Flow:** `Edge Supervisor` → `Centralized Coordination`, `Fleet Manager`

        **Contract kind:** `ros_topic`

        **Data type:** `task_msgs/msg/Feedback`

        #### Extracted fields

        | Section | Type | Name |
        |---|---|---|
        | message | `string` | `agent_id` |
        | message | `uint8` | `state` |
        | message | `TaskFeedback[]` | `tasks` |
        | message | `nav_msgs/Odometry` | `odometry` |

        #### Verified navigation data

        ##### Themis reports completion after the final waypoint

        Phase: **COMPLETED** · Evidence class: `verified_flow`

        ```json
        {
          "agent_id": "f9992bb3-9871-451f-90a0-9207eb9fe6c5",
          "state": 1,
          "tasks": [
            {
              "task_id": "<generated-task-uuid>",
              "task_state": 3,
              "current_objective_id": "<final-generated-objective-uuid>"
            }
          ],
          "odometry": {
            "pose": {
              "pose": {
                "position": {
                  "x": 4.391670213379427,
                  "y": 50.84417059346137,
                  "z": 0.0
                }
              }
            }
          }
        }
        ```

        - Task state 3 is COMPLETED. The mission manager then transitions the one-robot mission to COMPLETED(10).

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:918`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L918)

        #### Source evidence

        - [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:78`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L78)
        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:96`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L96)
        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:74`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L74)

    ??? abstract "/multi_robot/mission_feedback · c2_msgs/msg/MissionFeedback"
        **Flow:** `Centralized Coordination` → _not statically paired_

        **Contract kind:** `ros_topic`

        **Data type:** `c2_msgs/msg/MissionFeedback`

        #### Extracted fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `mission_id` |
        | message | `string` | `mission_feedback` |

        #### Verified navigation data

        ##### Mission feedback proving that a route was received

        Phase: **PLANNED** · Evidence class: `observed_excerpt`

        ```json
        {
          "mission_id": {
            "uuid": [
              68,
              68,
              68,
              68,
              85,
              85,
              70,
              102,
              135,
              119,
              136,
              136,
              136,
              136,
              136,
              136
            ]
          },
          "mission_feedback": "{\"mission_id\":\"44444444-5555-4666-8777-888888888888\",\"behavior\":0,\"status\":1,\"requested_status\":0,\"tasks\":[{\"vehicle_id\":\"f9992bb3-9871-451f-90a0-9207eb9fe6c5\",\"task_id\":\"<generated-task-uuid>\",\"waypoints\":[{\"coordinates\":[50.8443434,4.3925979]},{\"coordinates\":[50.84417059346137,4.391670213379427]}]}]}"
        }
        ```

        - The JSON string is abridged from 10 waypoints.
        - Legacy MissionFeedback serializes waypoint coordinates as [latitude, longitude]; the adapter swaps them back to [longitude, latitude].

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:678`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L678)

        #### Source evidence

        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:133`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L133)
        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:71`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L71)

    ??? abstract "/multi_robot/mission_init_request · c2_msgs/msg/InitMissionRequest"
        **Flow:** `Old REST Bridge` → `Centralized Coordination`

        **Contract kind:** `ros_topic`

        **Data type:** `c2_msgs/msg/InitMissionRequest`

        #### Extracted fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `mission_id` |
        | message | `string<=10000` | `mission_config` |

        #### Verified navigation data

        ##### Mission initialization on ROS

        Phase: **INIT** · Evidence class: `verified_flow`

        ```json
        {
          "mission_id": {
            "uuid": [
              68,
              68,
              68,
              68,
              85,
              85,
              70,
              102,
              135,
              119,
              136,
              136,
              136,
              136,
              136,
              136
            ]
          },
          "mission_config": "{\"mission_id\":\"44444444-5555-4666-8777-888888888888\",\"behavior\":0,\"vehicles\":[\"f9992bb3-9871-451f-90a0-9207eb9fe6c5\"],\"objective\":{\"geometries\":[{\"geometry\":{\"geometry_type\":\"Point\",\"coordinates\":[4.39167,50.84417]}}]},\"transit\":{\"optimalization\":{\"road_usage\":1.0},\"desired_vehicle_constraints\":{\"max_speed\":1.3}}}"
        }
        ```

        - mission_config is a JSON-encoded string and uses the legacy key optimalization.
        - The UUID byte array decodes to 44444444-5555-4666-8777-888888888888.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:108`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L108)

        #### Source evidence

        - [`backend/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/c2_rest.cpp:55`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/c2_rest.cpp#L55)
        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:54`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L54)

    ??? abstract "/multi_robot/planner/agent · centralized_msgs/msg/Agent"
        **Flow:** `Fleet Manager` → `Legacy Planner`

        **Contract kind:** `ros_topic`

        **Data type:** `centralized_msgs/msg/Agent`

        #### Extracted fields

        | Section | Type | Name |
        |---|---|---|
        | message | `string` | `agent_id` |
        | message | `string` | `agent_profile` |
        | message | `nav_msgs/Odometry` | `odometry` |

        #### Verified navigation data

        ##### Fleet forwards Themis and its live pose to Planner

        Phase: **robot discovery** · Evidence class: `observed_excerpt`

        ```json
        {
          "agent_id": "f9992bb3-9871-451f-90a0-9207eb9fe6c5",
          "agent_profile": "<JSON profile published by Edge>",
          "odometry": {
            "pose": {
              "pose": {
                "position": {
                  "x": 4.392588,
                  "y": 50.844317,
                  "z": 0.0
                }
              }
            }
          }
        }
        ```

        - In this global-coordinate simulation, odometry x is longitude and y is latitude.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:304`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L304)

        #### Source evidence

        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:67`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L67)
        - [`backend/fog/planner/ros2ws/src/planner/planner/planner_node.py:134`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/planner/planner/planner_node.py#L134)

    ??? abstract "/multi_robot/planner/state · std_msgs/msg/String"
        **Flow:** `Legacy Planner` → `Centralized Coordination`

        **Contract kind:** `ros_topic`

        **Data type:** `std_msgs/msg/String`

        #### Extracted fields

        | Section | Type | Name |
        |---|---|---|
        | message | `string` | `data` |

        #### Verified navigation data

        ##### Planner reports that the plan cache is ready

        Phase: **planning** · Evidence class: `runtime_observed`

        ```json
        {
          "data": "{\"planners\":[{\"mission_id\":\"44444444-5555-4666-8777-888888888888\",\"state\":2}]}"
        }
        ```

        - State 2 was observed, but usable route evidence still comes from non-empty mission feedback waypoints.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:11`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L11)

        #### Source evidence

        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:65`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L65)
        - [`backend/fog/planner/ros2ws/src/planner/planner/planner_node.py:132`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/planner/planner/planner_node.py#L132)


=== "HTTP (30)"

    ## DELETE

    3 extracted contracts.

    ??? abstract "DELETE /api/assistant/conversations/{conversation_id} · reset_conversation"
        FastAPI handler `reset_conversation`

        [Open standalone page](http/delete-api-assistant-conversations-conversation-id.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `http_endpoint` |
        | Method | `DELETE` |
        | Path | `/api/assistant/conversations/{conversation_id}` |
        | Handler | `reset_conversation` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | handled by reset_conversation | `—` | [`src/c2_imugs2/api/routers.py:353`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L353) |
        | resetAssistantConversation | `—` | [`frontend/src/api.ts:655`](https://github.com/LEBaz2211/C2_imugs2/blob/main/frontend/src/api.ts#L655) |

        #### Definition evidence

        - [`src/c2_imugs2/api/routers.py:353`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L353)

    ??? abstract "DELETE /api/map/features/{feature_id} · delete_map_feature"
        FastAPI handler `delete_map_feature`

        [Open standalone page](http/delete-api-map-features-feature-id.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `http_endpoint` |
        | Method | `DELETE` |
        | Path | `/api/map/features/{feature_id}` |
        | Handler | `delete_map_feature` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | deleteMapFeature | `—` | [`frontend/src/api.ts:588`](https://github.com/LEBaz2211/C2_imugs2/blob/main/frontend/src/api.ts#L588) |
        | handled by delete_map_feature | `—` | [`src/c2_imugs2/api/app.py:288`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/app.py#L288) |

        #### Definition evidence

        - [`src/c2_imugs2/api/app.py:288`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/app.py#L288)

    ??? abstract "DELETE /api/missions/{mission_id} · forget"
        FastAPI handler `forget`

        [Open standalone page](http/delete-api-missions-mission-id.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `http_endpoint` |
        | Method | `DELETE` |
        | Path | `/api/missions/{mission_id}` |
        | Handler | `forget` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | forgetMission | `—` | [`frontend/src/api.ts:637`](https://github.com/LEBaz2211/C2_imugs2/blob/main/frontend/src/api.ts#L637) |
        | handled by forget | `—` | [`src/c2_imugs2/api/routers.py:222`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L222) |

        #### Definition evidence

        - [`src/c2_imugs2/api/routers.py:222`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L222)

    ## GET

    16 extracted contracts.

    ??? abstract "GET /api/agents · agents"
        FastAPI handler `agents`

        [Open standalone page](http/get-api-agents.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `http_endpoint` |
        | Method | `GET` |
        | Path | `/api/agents` |
        | Handler | `agents` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | handled by agents | `—` | [`src/c2_imugs2/api/app.py:346`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/app.py#L346) |

        #### Verified navigation data

        ##### Themis agent returned to the UI adapter

        Phase: **robot discovery** · Evidence class: `runtime_observed`

        ```json
        {
          "agents": [
            {
              "agent_id": "f9992bb3-9871-451f-90a0-9207eb9fe6c5",
              "name": "Themis Fr",
              "vehicle_type": "UGV",
              "current_location": [
                4.392588,
                50.844317
              ],
              "constraints": {
                "max_speed": 4.5,
                "max_acceleration": 8.0,
                "max_weight": 16.0,
                "max_tilt_angle": 1.8
              },
              "status": "1"
            }
          ]
        }
        ```

        - Coordinates are [longitude, latitude].

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`legacy_ros/config/config_autonomy.yaml:6`](https://github.com/LEBaz2211/C2_imugs2/blob/main/legacy_ros/config/config_autonomy.yaml#L6)

        #### Definition evidence

        - [`src/c2_imugs2/api/app.py:346`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/app.py#L346)

    ??? abstract "GET /api/assistant/operational-picture · operational_picture"
        FastAPI handler `operational_picture`

        [Open standalone page](http/get-api-assistant-operational-picture.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `http_endpoint` |
        | Method | `GET` |
        | Path | `/api/assistant/operational-picture` |
        | Handler | `operational_picture` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | handled by operational_picture | `—` | [`src/c2_imugs2/api/routers.py:273`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L273) |

        #### Definition evidence

        - [`src/c2_imugs2/api/routers.py:273`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L273)

    ??? abstract "GET /api/assistant/status · assistant_status"
        FastAPI handler `assistant_status`

        [Open standalone page](http/get-api-assistant-status.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `http_endpoint` |
        | Method | `GET` |
        | Path | `/api/assistant/status` |
        | Handler | `assistant_status` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | getAssistantStatus | `—` | [`frontend/src/api.ts:641`](https://github.com/LEBaz2211/C2_imugs2/blob/main/frontend/src/api.ts#L641) |
        | handled by assistant_status | `—` | [`src/c2_imugs2/api/routers.py:269`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L269) |

        #### Definition evidence

        - [`src/c2_imugs2/api/routers.py:269`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L269)

    ??? abstract "GET /api/contracts · contracts"
        FastAPI handler `contracts`

        [Open standalone page](http/get-api-contracts.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `http_endpoint` |
        | Method | `GET` |
        | Path | `/api/contracts` |
        | Handler | `contracts` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | getContracts | `—` | [`frontend/src/api.ts:605`](https://github.com/LEBaz2211/C2_imugs2/blob/main/frontend/src/api.ts#L605) |
        | handled by contracts | `—` | [`src/c2_imugs2/api/app.py:212`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/app.py#L212) |

        #### Definition evidence

        - [`src/c2_imugs2/api/app.py:212`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/app.py#L212)

    ??? abstract "GET /api/diagnostics · diagnostics"
        FastAPI handler `diagnostics`

        [Open standalone page](http/get-api-diagnostics.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `http_endpoint` |
        | Method | `GET` |
        | Path | `/api/diagnostics` |
        | Handler | `diagnostics` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | getDiagnostics | `—` | [`frontend/src/api.ts:596`](https://github.com/LEBaz2211/C2_imugs2/blob/main/frontend/src/api.ts#L596) |
        | handled by diagnostics | `—` | [`src/c2_imugs2/api/app.py:186`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/app.py#L186) |

        #### Definition evidence

        - [`src/c2_imugs2/api/app.py:186`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/app.py#L186)

    ??? abstract "GET /api/events · events"
        FastAPI handler `events`

        [Open standalone page](http/get-api-events.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `http_endpoint` |
        | Method | `GET` |
        | Path | `/api/events` |
        | Handler | `events` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | handled by events | `—` | [`src/c2_imugs2/api/app.py:399`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/app.py#L399) |

        #### Definition evidence

        - [`src/c2_imugs2/api/app.py:399`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/app.py#L399)

    ??? abstract "GET /api/health · health"
        FastAPI handler `health`

        [Open standalone page](http/get-api-health.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `http_endpoint` |
        | Method | `GET` |
        | Path | `/api/health` |
        | Handler | `health` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | handled by health | `—` | [`src/c2_imugs2/api/app.py:170`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/app.py#L170) |

        #### Definition evidence

        - [`src/c2_imugs2/api/app.py:170`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/app.py#L170)

    ??? abstract "GET /api/legacy/trace · legacy_trace"
        FastAPI handler `legacy_trace`

        [Open standalone page](http/get-api-legacy-trace.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `http_endpoint` |
        | Method | `GET` |
        | Path | `/api/legacy/trace` |
        | Handler | `legacy_trace` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | getLegacyTrace | `—` | [`frontend/src/api.ts:613`](https://github.com/LEBaz2211/C2_imugs2/blob/main/frontend/src/api.ts#L613) |
        | handled by legacy_trace | `—` | [`src/c2_imugs2/api/app.py:225`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/app.py#L225) |

        #### Definition evidence

        - [`src/c2_imugs2/api/app.py:225`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/app.py#L225)

    ??? abstract "GET /api/map/features · map_features"
        FastAPI handler `map_features`

        [Open standalone page](http/get-api-map-features.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `http_endpoint` |
        | Method | `GET` |
        | Path | `/api/map/features` |
        | Handler | `map_features` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | handled by map_features | `—` | [`src/c2_imugs2/api/app.py:267`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/app.py#L267) |

        #### Definition evidence

        - [`src/c2_imugs2/api/app.py:267`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/app.py#L267)

    ??? abstract "GET /api/map/osm-roads · osm_roads"
        FastAPI handler `osm_roads`

        [Open standalone page](http/get-api-map-osm-roads.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `http_endpoint` |
        | Method | `GET` |
        | Path | `/api/map/osm-roads` |
        | Handler | `osm_roads` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | getOsmRoads | `—` | [`frontend/src/api.ts:564`](https://github.com/LEBaz2211/C2_imugs2/blob/main/frontend/src/api.ts#L564) |
        | handled by osm_roads | `—` | [`src/c2_imugs2/api/app.py:316`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/app.py#L316) |

        #### Definition evidence

        - [`src/c2_imugs2/api/app.py:316`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/app.py#L316)

    ??? abstract "GET /api/mission-examples · mission_examples"
        FastAPI handler `mission_examples`

        [Open standalone page](http/get-api-mission-examples.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `http_endpoint` |
        | Method | `GET` |
        | Path | `/api/mission-examples` |
        | Handler | `mission_examples` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | getMissionExamples | `—` | [`frontend/src/api.ts:609`](https://github.com/LEBaz2211/C2_imugs2/blob/main/frontend/src/api.ts#L609) |
        | handled by mission_examples | `—` | [`src/c2_imugs2/api/app.py:382`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/app.py#L382) |

        #### Definition evidence

        - [`src/c2_imugs2/api/app.py:382`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/app.py#L382)

    ??? abstract "GET /api/missions/{mission_id} · get_mission"
        FastAPI handler `get_mission`

        [Open standalone page](http/get-api-missions-mission-id.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `http_endpoint` |
        | Method | `GET` |
        | Path | `/api/missions/{mission_id}` |
        | Handler | `get_mission` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | getMissionState | `—` | [`frontend/src/api.ts:625`](https://github.com/LEBaz2211/C2_imugs2/blob/main/frontend/src/api.ts#L625) |
        | handled by get_mission | `—` | [`src/c2_imugs2/api/routers.py:200`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L200) |

        #### Definition evidence

        - [`src/c2_imugs2/api/routers.py:200`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L200)

    ??? abstract "GET /api/planning/diagnostics · planning_diagnostics"
        FastAPI handler `planning_diagnostics`

        [Open standalone page](http/get-api-planning-diagnostics.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `http_endpoint` |
        | Method | `GET` |
        | Path | `/api/planning/diagnostics` |
        | Handler | `planning_diagnostics` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | getPlanningDiagnostics | `—` | [`frontend/src/api.ts:600`](https://github.com/LEBaz2211/C2_imugs2/blob/main/frontend/src/api.ts#L600) |
        | handled by planning_diagnostics | `—` | [`src/c2_imugs2/api/app.py:205`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/app.py#L205) |

        #### Definition evidence

        - [`src/c2_imugs2/api/app.py:205`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/app.py#L205)

    ??? abstract "GET /api/runtime/bootstrap · runtime_bootstrap"
        FastAPI handler `runtime_bootstrap`

        [Open standalone page](http/get-api-runtime-bootstrap.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `http_endpoint` |
        | Method | `GET` |
        | Path | `/api/runtime/bootstrap` |
        | Handler | `runtime_bootstrap` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | getRuntimeBootstrap | `—` | [`frontend/src/api.ts:560`](https://github.com/LEBaz2211/C2_imugs2/blob/main/frontend/src/api.ts#L560) |
        | handled by runtime_bootstrap | `—` | [`src/c2_imugs2/api/app.py:466`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/app.py#L466) |

        #### Definition evidence

        - [`src/c2_imugs2/api/app.py:466`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/app.py#L466)

    ??? abstract "GET /api/scenarios · catalog"
        FastAPI handler `catalog`

        [Open standalone page](http/get-api-scenarios.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `http_endpoint` |
        | Method | `GET` |
        | Path | `/api/scenarios` |
        | Handler | `catalog` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | getScenarios | `—` | [`frontend/src/api.ts:580`](https://github.com/LEBaz2211/C2_imugs2/blob/main/frontend/src/api.ts#L580) |
        | handled by catalog | `—` | [`src/c2_imugs2/api/routers.py:232`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L232) |

        #### Definition evidence

        - [`src/c2_imugs2/api/routers.py:232`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L232)

    ??? abstract "GET /api/scenarios/active · active"
        FastAPI handler `active`

        [Open standalone page](http/get-api-scenarios-active.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `http_endpoint` |
        | Method | `GET` |
        | Path | `/api/scenarios/active` |
        | Handler | `active` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | getActiveScenario | `—` | [`frontend/src/api.ts:576`](https://github.com/LEBaz2211/C2_imugs2/blob/main/frontend/src/api.ts#L576) |
        | handled by active | `—` | [`src/c2_imugs2/api/routers.py:239`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L239) |

        #### Definition evidence

        - [`src/c2_imugs2/api/routers.py:239`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L239)

    ## POST

    10 extracted contracts.

    ??? abstract "POST /api/assistant/messages · send_message"
        FastAPI handler `send_message`

        [Open standalone page](http/post-api-assistant-messages.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `http_endpoint` |
        | Method | `POST` |
        | Path | `/api/assistant/messages` |
        | Handler | `send_message` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | handled by send_message | `—` | [`src/c2_imugs2/api/routers.py:314`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L314) |
        | sendAssistantMessage | `—` | [`frontend/src/api.ts:645`](https://github.com/LEBaz2211/C2_imugs2/blob/main/frontend/src/api.ts#L645) |

        #### Definition evidence

        - [`src/c2_imugs2/api/routers.py:314`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L314)

    ??? abstract "POST /api/assistant/operational-picture/preview · operational_picture_preview"
        FastAPI handler `operational_picture_preview`

        [Open standalone page](http/post-api-assistant-operational-picture-preview.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `http_endpoint` |
        | Method | `POST` |
        | Path | `/api/assistant/operational-picture/preview` |
        | Handler | `operational_picture_preview` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | handled by operational_picture_preview | `—` | [`src/c2_imugs2/api/routers.py:291`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L291) |
        | previewAssistantOperationalPicture | `—` | [`frontend/src/api.ts:649`](https://github.com/LEBaz2211/C2_imugs2/blob/main/frontend/src/api.ts#L649) |

        #### Definition evidence

        - [`src/c2_imugs2/api/routers.py:291`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L291)

    ??? abstract "POST /api/map/features · create_map_feature"
        FastAPI handler `create_map_feature`

        [Open standalone page](http/post-api-map-features.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `http_endpoint` |
        | Method | `POST` |
        | Path | `/api/map/features` |
        | Handler | `create_map_feature` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | createMapFeature | `—` | [`frontend/src/api.ts:584`](https://github.com/LEBaz2211/C2_imugs2/blob/main/frontend/src/api.ts#L584) |
        | handled by create_map_feature | `—` | [`src/c2_imugs2/api/app.py:274`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/app.py#L274) |

        #### Definition evidence

        - [`src/c2_imugs2/api/app.py:274`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/app.py#L274)

    ??? abstract "POST /api/map/osm-roads/query · query_osm_roads"
        FastAPI handler `query_osm_roads`

        [Open standalone page](http/post-api-map-osm-roads-query.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `http_endpoint` |
        | Method | `POST` |
        | Path | `/api/map/osm-roads/query` |
        | Handler | `query_osm_roads` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | handled by query_osm_roads | `—` | [`src/c2_imugs2/api/app.py:320`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/app.py#L320) |
        | queryOsmRoads | `—` | [`frontend/src/api.ts:568`](https://github.com/LEBaz2211/C2_imugs2/blob/main/frontend/src/api.ts#L568) |

        #### Definition evidence

        - [`src/c2_imugs2/api/app.py:320`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/app.py#L320)

    ??? abstract "POST /api/missions/init · init_mission"
        FastAPI handler `init_mission`

        [Open standalone page](http/post-api-missions-init.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `http_endpoint` |
        | Method | `POST` |
        | Path | `/api/missions/init` |
        | Handler | `init_mission` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | handled by init_mission | `—` | [`src/c2_imugs2/api/routers.py:193`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L193) |
        | initMission | `—` | [`frontend/src/api.ts:621`](https://github.com/LEBaz2211/C2_imugs2/blob/main/frontend/src/api.ts#L621) |

        #### Verified navigation data

        ##### Canonical mission submitted to the adapter

        Phase: **INIT** · Evidence class: `verified_flow`

        ```json
        {
          "mission_id": "44444444-5555-4666-8777-888888888888",
          "behavior": 0,
          "vehicles": [
            "f9992bb3-9871-451f-90a0-9207eb9fe6c5"
          ],
          "objective": {
            "geometries": [
              {
                "geometry": {
                  "geometry_type": "Point",
                  "coordinates": [
                    4.39167,
                    50.84417
                  ]
                }
              }
            ]
          },
          "transit": {
            "optimization": {
              "road_usage": 1.0
            },
            "desired_vehicle_constraints": {
              "max_speed": 1.3
            }
          }
        }
        ```

        - The adapter uses canonical optimization; the legacy REST payload below translates it to optimalization.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:108`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L108), [`src/c2_imugs2/infrastructure/legacy/rest.py:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/infrastructure/legacy/rest.py#L1)

        #### Definition evidence

        - [`src/c2_imugs2/api/routers.py:193`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L193)

    ??? abstract "POST /api/missions/{mission_id}/approve · approve"
        FastAPI handler `approve`

        [Open standalone page](http/post-api-missions-mission-id-approve.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `http_endpoint` |
        | Method | `POST` |
        | Path | `/api/missions/{mission_id}/approve` |
        | Handler | `approve` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | approveMission | `—` | [`frontend/src/api.ts:629`](https://github.com/LEBaz2211/C2_imugs2/blob/main/frontend/src/api.ts#L629) |
        | handled by approve | `—` | [`src/c2_imugs2/api/routers.py:208`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L208) |

        #### Verified navigation data

        ##### Approve the planned mission

        Phase: **APPROVE** · Evidence class: `verified_flow`

        ```json
        {
          "path": "/api/missions/44444444-5555-4666-8777-888888888888/approve",
          "body": {}
        }
        ```

        - Send only after mission feedback contains a non-empty path and status PLANNED(1).

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:154`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L154)

        #### Definition evidence

        - [`src/c2_imugs2/api/routers.py:208`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L208)

    ??? abstract "POST /api/missions/{mission_id}/start · start"
        FastAPI handler `start`

        [Open standalone page](http/post-api-missions-mission-id-start.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `http_endpoint` |
        | Method | `POST` |
        | Path | `/api/missions/{mission_id}/start` |
        | Handler | `start` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | handled by start | `—` | [`src/c2_imugs2/api/routers.py:215`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L215) |
        | startMission | `—` | [`frontend/src/api.ts:633`](https://github.com/LEBaz2211/C2_imugs2/blob/main/frontend/src/api.ts#L633) |

        #### Verified navigation data

        ##### Start the accepted mission

        Phase: **START** · Evidence class: `verified_flow`

        ```json
        {
          "path": "/api/missions/44444444-5555-4666-8777-888888888888/start",
          "body": {}
        }
        ```

        - Send after status ACCEPTED(4) and Edge confirms that the stopped task is installed.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:164`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L164)

        #### Definition evidence

        - [`src/c2_imugs2/api/routers.py:215`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L215)

    ??? abstract "POST /api/scenarios/activate · activate"
        FastAPI handler `activate`

        [Open standalone page](http/post-api-scenarios-activate.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `http_endpoint` |
        | Method | `POST` |
        | Path | `/api/scenarios/activate` |
        | Handler | `activate` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | handled by activate | `—` | [`src/c2_imugs2/api/routers.py:244`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L244) |
        | launchScenario | `—` | [`frontend/src/api.ts:572`](https://github.com/LEBaz2211/C2_imugs2/blob/main/frontend/src/api.ts#L572) |

        #### Definition evidence

        - [`src/c2_imugs2/api/routers.py:244`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L244)

    ??? abstract "POST /api/scenarios/launch · activate"
        FastAPI handler `activate`

        [Open standalone page](http/post-api-scenarios-launch.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `http_endpoint` |
        | Method | `POST` |
        | Path | `/api/scenarios/launch` |
        | Handler | `activate` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | handled by activate | `—` | [`src/c2_imugs2/api/routers.py:244`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L244) |

        #### Definition evidence

        - [`src/c2_imugs2/api/routers.py:244`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L244)

    ??? abstract "POST /api/testing/reset-legacy-runtime · reset_legacy_runtime"
        FastAPI handler `reset_legacy_runtime`

        [Open standalone page](http/post-api-testing-reset-legacy-runtime.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `http_endpoint` |
        | Method | `POST` |
        | Path | `/api/testing/reset-legacy-runtime` |
        | Handler | `reset_legacy_runtime` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | handled by reset_legacy_runtime | `—` | [`src/c2_imugs2/api/app.py:256`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/app.py#L256) |
        | resetLegacyRuntime | `—` | [`frontend/src/api.ts:617`](https://github.com/LEBaz2211/C2_imugs2/blob/main/frontend/src/api.ts#L617) |

        #### Definition evidence

        - [`src/c2_imugs2/api/app.py:256`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/app.py#L256)

    ## PUT

    1 extracted contract.

    ??? abstract "PUT /api/map/features/{feature_id} · update_map_feature"
        FastAPI handler `update_map_feature`

        [Open standalone page](http/put-api-map-features-feature-id.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `http_endpoint` |
        | Method | `PUT` |
        | Path | `/api/map/features/{feature_id}` |
        | Handler | `update_map_feature` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | handled by update_map_feature | `—` | [`src/c2_imugs2/api/app.py:300`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/app.py#L300) |
        | updateMapFeature | `—` | [`frontend/src/api.ts:592`](https://github.com/LEBaz2211/C2_imugs2/blob/main/frontend/src/api.ts#L592) |

        #### Definition evidence

        - [`src/c2_imugs2/api/app.py:300`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/app.py#L300)


=== "ROS topics (29)"

    ## /multi_robot/change

    4 extracted contracts.

    ??? abstract "/multi_robot/change_mission_status_request · c2_msgs/msg/ChangeMissionStatusRequest"
        ROS topic `/multi_robot/change_mission_status_request`

        [Open standalone page](ros-topics/multi-robot-change-mission-status-request.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_topic` |
        | Interface | `/multi_robot/change_mission_status_request` |
        | Type | `c2_msgs/msg/ChangeMissionStatusRequest` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `mission_id` |
        | message | `uint8` | `mission_request_status` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | publishes | `c2_msgs/msg/ChangeMissionStatusRequest` | [`backend/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/c2_rest.cpp:58`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/c2_rest.cpp#L58) |
        | subscribes | `c2_msgs/msg/ChangeMissionStatusRequest` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:57`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L57) |

        #### Verified navigation data

        ##### APPROVE status request

        Phase: **APPROVE** · Evidence class: `verified_flow`

        ```json
        {
          "mission_id": {
            "uuid": [
              68,
              68,
              68,
              68,
              85,
              85,
              70,
              102,
              135,
              119,
              136,
              136,
              136,
              136,
              136,
              136
            ]
          },
          "mission_request_status": 1
        }
        ```

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:718`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L718)

        ##### START status request

        Phase: **START** · Evidence class: `verified_flow`

        ```json
        {
          "mission_id": {
            "uuid": [
              68,
              68,
              68,
              68,
              85,
              85,
              70,
              102,
              135,
              119,
              136,
              136,
              136,
              136,
              136,
              136
            ]
          },
          "mission_request_status": 2
        }
        ```

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:796`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L796)

        #### Definition evidence

        - [`backend/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/c2_rest.cpp:58`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/c2_rest.cpp#L58)
        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:57`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L57)

    ??? abstract "/multi_robot/change_mission_status_response · c2_msgs/msg/ChangeMissionStatusResponse"
        ROS topic `/multi_robot/change_mission_status_response`

        [Open standalone page](ros-topics/multi-robot-change-mission-status-response.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_topic` |
        | Interface | `/multi_robot/change_mission_status_response` |
        | Type | `c2_msgs/msg/ChangeMissionStatusResponse` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `mission_id` |
        | message | `uint8` | `mission_status` |
        | message | `string<=2000` | `error_message` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | publishes | `c2_msgs/msg/ChangeMissionStatusResponse` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:58`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L58) |
        | publishes | `c2_msgs/msg/ChangeMissionStatusResponse` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:137`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L137) |
        | subscribes | `c2_msgs/msg/ChangeMissionStatusResponse` | [`backend/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/c2_rest.cpp:57`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/c2_rest.cpp#L57) |

        #### Verified navigation data

        ##### Mission manager accepts the APPROVE transition

        Phase: **APPROVE** · Evidence class: `verified_flow`

        ```json
        {
          "mission_id": {
            "uuid": [
              68,
              68,
              68,
              68,
              85,
              85,
              70,
              102,
              135,
              119,
              136,
              136,
              136,
              136,
              136,
              136
            ]
          },
          "mission_status": 4,
          "error_message": ""
        }
        ```

        - Mission status 4 is ACCEPTED.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:876`](https://github.com/LEBaz2211/C2_imugs2/blob/main/legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L876)

        ##### Mission manager accepts the START transition

        Phase: **START** · Evidence class: `verified_flow`

        ```json
        {
          "mission_id": {
            "uuid": [
              68,
              68,
              68,
              68,
              85,
              85,
              70,
              102,
              135,
              119,
              136,
              136,
              136,
              136,
              136,
              136
            ]
          },
          "mission_status": 5,
          "error_message": ""
        }
        ```

        - Mission status 5 is STARTED.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:876`](https://github.com/LEBaz2211/C2_imugs2/blob/main/legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L876)

        #### Definition evidence

        - [`backend/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/c2_rest.cpp:57`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/c2_rest.cpp#L57)
        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:137`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L137)
        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:58`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L58)

    ??? abstract "/multi_robot/change_mission_vehicle_request · c2_msgs/msg/ChangeMissionVehicleRequest"
        ROS topic `/multi_robot/change_mission_vehicle_request`

        [Open standalone page](ros-topics/multi-robot-change-mission-vehicle-request.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_topic` |
        | Interface | `/multi_robot/change_mission_vehicle_request` |
        | Type | `c2_msgs/msg/ChangeMissionVehicleRequest` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `mission_id` |
        | message | `string[]` | `vehicule_id_list` |
        | message | `uint8` | `vehicle_changes` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | subscribes | `c2_msgs/msg/ChangeMissionVehicleRequest` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:60`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L60) |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:60`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L60)

    ??? abstract "/multi_robot/change_mission_vehicle_response · c2_msgs/msg/ChangeMissionVehicleResponse"
        ROS topic `/multi_robot/change_mission_vehicle_response`

        [Open standalone page](ros-topics/multi-robot-change-mission-vehicle-response.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_topic` |
        | Interface | `/multi_robot/change_mission_vehicle_response` |
        | Type | `c2_msgs/msg/ChangeMissionVehicleResponse` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `mission_id` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | publishes | `c2_msgs/msg/ChangeMissionVehicleResponse` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:61`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L61) |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:61`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L61)

    ## /multi_robot/edge

    4 extracted contracts.

    ??? abstract "/multi_robot/edge/agent_profile · std_msgs/msg/String"
        ROS topic `/multi_robot/edge/agent_profile`

        [Open standalone page](ros-topics/multi-robot-edge-agent-profile.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_topic` |
        | Interface | `/multi_robot/edge/agent_profile` |
        | Type | `std_msgs/msg/String` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `string` | `data` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | publishes | `std_msgs/msg/String` | [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:82`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L82) |
        | subscribes | `std_msgs/msg/String` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:77`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L77) |

        #### Verified navigation data

        ##### Edge publishes the participating robot profile

        Phase: **robot discovery** · Evidence class: `observed_excerpt`

        ```json
        {
          "data": "{\"agent_id\":\"f9992bb3-9871-451f-90a0-9207eb9fe6c5\",\"vehicle_constraints\":{\"max_speed\":{\"linear\":{\"x\":4.5}},\"max_acceleration\":{\"linear\":{\"x\":8.0}}},\"vehicle_info\":{\"fuel_status_pct\":85.0,\"battery_status_pct\":90.0}}"
        }
        ```

        - The JSON string is abridged; the runtime profile also contains angular constraints, dimensions, endurance, and sensors.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`legacy_ros/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:250`](https://github.com/LEBaz2211/C2_imugs2/blob/main/legacy_ros/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L250), [`legacy_ros/config/config_autonomy.yaml:6`](https://github.com/LEBaz2211/C2_imugs2/blob/main/legacy_ros/config/config_autonomy.yaml#L6)

        #### Definition evidence

        - [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:82`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L82)
        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:77`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L77)

    ??? abstract "/multi_robot/edge/feedback · task_msgs/msg/Feedback"
        ROS topic `/multi_robot/edge/feedback`

        [Open standalone page](ros-topics/multi-robot-edge-feedback.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_topic` |
        | Interface | `/multi_robot/edge/feedback` |
        | Type | `task_msgs/msg/Feedback` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `string` | `agent_id` |
        | message | `uint8` | `state` |
        | message | `TaskFeedback[]` | `tasks` |
        | message | `nav_msgs/Odometry` | `odometry` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | publishes | `task_msgs/msg/Feedback` | [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:78`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L78) |
        | subscribes | `task_msgs/msg/Feedback` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:74`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L74) |
        | subscribes | `task_msgs/msg/Feedback` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:96`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L96) |

        #### Verified navigation data

        ##### Themis reports completion after the final waypoint

        Phase: **COMPLETED** · Evidence class: `verified_flow`

        ```json
        {
          "agent_id": "f9992bb3-9871-451f-90a0-9207eb9fe6c5",
          "state": 1,
          "tasks": [
            {
              "task_id": "<generated-task-uuid>",
              "task_state": 3,
              "current_objective_id": "<final-generated-objective-uuid>"
            }
          ],
          "odometry": {
            "pose": {
              "pose": {
                "position": {
                  "x": 4.391670213379427,
                  "y": 50.84417059346137,
                  "z": 0.0
                }
              }
            }
          }
        }
        ```

        - Task state 3 is COMPLETED. The mission manager then transitions the one-robot mission to COMPLETED(10).

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:918`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L918)

        #### Definition evidence

        - [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:78`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L78)
        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:96`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L96)
        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:74`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L74)

    ??? abstract "multi_robot/edge/connection_check · std_msgs/msg/String"
        ROS topic `multi_robot/edge/connection_check`

        [Open standalone page](ros-topics/multi-robot-edge-connection-check.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_topic` |
        | Interface | `multi_robot/edge/connection_check` |
        | Type | `std_msgs/msg/String` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `string` | `data` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | publishes | `std_msgs/msg/String` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:80`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L80) |
        | subscribes | `std_msgs/msg/String` | [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:86`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L86) |

        #### Definition evidence

        - [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:86`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L86)
        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:80`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L80)

    ??? abstract "multi_robot/edge/node_init · std_msgs/msg/String"
        ROS topic `multi_robot/edge/node_init`

        [Open standalone page](ros-topics/multi-robot-edge-node-init.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_topic` |
        | Interface | `multi_robot/edge/node_init` |
        | Type | `std_msgs/msg/String` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `string` | `data` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | publishes | `std_msgs/msg/String` | [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:75`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L75) |

        #### Definition evidence

        - [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:75`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L75)

    ## /multi_robot/environment

    6 extracted contracts.

    ??? abstract "/multi_robot/environment_data_get_version_request · environment_msgs/msg/EnvironmentDataGetVersionRequest"
        ROS topic `/multi_robot/environment_data_get_version_request`

        [Open standalone page](ros-topics/multi-robot-environment-data-get-version-request.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_topic` |
        | Interface | `/multi_robot/environment_data_get_version_request` |
        | Type | `environment_msgs/msg/EnvironmentDataGetVersionRequest` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `request_id` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | subscribes | `environment_msgs/msg/EnvironmentDataGetVersionRequest` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:67`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L67) |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:67`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L67)

    ??? abstract "/multi_robot/environment_data_get_version_response · environment_msgs/msg/EnvironmentDataGetVersionResponse"
        ROS topic `/multi_robot/environment_data_get_version_response`

        [Open standalone page](ros-topics/multi-robot-environment-data-get-version-response.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_topic` |
        | Interface | `/multi_robot/environment_data_get_version_response` |
        | Type | `environment_msgs/msg/EnvironmentDataGetVersionResponse` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `request_id` |
        | message | `uint32` | `version_nr` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | publishes | `environment_msgs/msg/EnvironmentDataGetVersionResponse` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:68`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L68) |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:68`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L68)

    ??? abstract "/multi_robot/environment_data_reset_request · environment_msgs/msg/EnvironmentDataResetRequest"
        ROS topic `/multi_robot/environment_data_reset_request`

        [Open standalone page](ros-topics/multi-robot-environment-data-reset-request.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_topic` |
        | Interface | `/multi_robot/environment_data_reset_request` |
        | Type | `environment_msgs/msg/EnvironmentDataResetRequest` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `request_id` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | subscribes | `environment_msgs/msg/EnvironmentDataResetRequest` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:63`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L63) |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:63`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L63)

    ??? abstract "/multi_robot/environment_data_reset_response · environment_msgs/msg/EnvironmentDataResetResponse"
        ROS topic `/multi_robot/environment_data_reset_response`

        [Open standalone page](ros-topics/multi-robot-environment-data-reset-response.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_topic` |
        | Interface | `/multi_robot/environment_data_reset_response` |
        | Type | `environment_msgs/msg/EnvironmentDataResetResponse` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `request_id` |
        | message | `uint8` | `result_status` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | publishes | `environment_msgs/msg/EnvironmentDataResetResponse` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:64`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L64) |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:64`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L64)

    ??? abstract "/multi_robot/environment_data_upload_request · environment_msgs/msg/EnvironmentDataUploadRequest"
        ROS topic `/multi_robot/environment_data_upload_request`

        [Open standalone page](ros-topics/multi-robot-environment-data-upload-request.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_topic` |
        | Interface | `/multi_robot/environment_data_upload_request` |
        | Type | `environment_msgs/msg/EnvironmentDataUploadRequest` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `request_id` |
        | message | `uint32` | `version_nr` |
        | message | `string<=10000` | `insert_geojson` |
        | message | `string<=10000` | `update_geojson` |
        | message | `string<=5000` | `delete_json` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | subscribes | `environment_msgs/msg/EnvironmentDataUploadRequest` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:65`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L65) |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:65`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L65)

    ??? abstract "/multi_robot/environment_data_upload_response · environment_msgs/msg/EnvironmentDataUploadResponse"
        ROS topic `/multi_robot/environment_data_upload_response`

        [Open standalone page](ros-topics/multi-robot-environment-data-upload-response.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_topic` |
        | Interface | `/multi_robot/environment_data_upload_response` |
        | Type | `environment_msgs/msg/EnvironmentDataUploadResponse` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `request_id` |
        | message | `uint8` | `result_status` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | publishes | `environment_msgs/msg/EnvironmentDataUploadResponse` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:66`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L66) |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:66`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L66)

    ## /multi_robot/log

    1 extracted contract.

    ??? abstract "/multi_robot/log · c2_msgs/msg/SwarmLog"
        ROS topic `/multi_robot/log`

        [Open standalone page](ros-topics/multi-robot-log.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_topic` |
        | Interface | `/multi_robot/log` |
        | Type | `c2_msgs/msg/SwarmLog` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `mission_id` |
        | message | `string` | `log` |
        | message | `string` | `date` |
        | message | `uint8` | `log_type` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | publishes | `c2_msgs/msg/SwarmLog` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:54`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L54) |
        | publishes | `c2_msgs/msg/SwarmLog` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:143`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L143) |
        | publishes | `c2_msgs/msg/SwarmLog` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp:64`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp#L64) |
        | subscribes | `c2_msgs/msg/SwarmLog` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp:51`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp#L51) |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:143`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L143)
        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:54`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L54)
        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp:51`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp#L51)
        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp:64`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp#L64)

    ## /multi_robot/mission

    3 extracted contracts.

    ??? abstract "/multi_robot/mission_feedback · c2_msgs/msg/MissionFeedback"
        ROS topic `/multi_robot/mission_feedback`

        [Open standalone page](ros-topics/multi-robot-mission-feedback.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_topic` |
        | Interface | `/multi_robot/mission_feedback` |
        | Type | `c2_msgs/msg/MissionFeedback` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `mission_id` |
        | message | `string` | `mission_feedback` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | publishes | `c2_msgs/msg/MissionFeedback` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:71`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L71) |
        | publishes | `c2_msgs/msg/MissionFeedback` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:133`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L133) |

        #### Verified navigation data

        ##### Mission feedback proving that a route was received

        Phase: **PLANNED** · Evidence class: `observed_excerpt`

        ```json
        {
          "mission_id": {
            "uuid": [
              68,
              68,
              68,
              68,
              85,
              85,
              70,
              102,
              135,
              119,
              136,
              136,
              136,
              136,
              136,
              136
            ]
          },
          "mission_feedback": "{\"mission_id\":\"44444444-5555-4666-8777-888888888888\",\"behavior\":0,\"status\":1,\"requested_status\":0,\"tasks\":[{\"vehicle_id\":\"f9992bb3-9871-451f-90a0-9207eb9fe6c5\",\"task_id\":\"<generated-task-uuid>\",\"waypoints\":[{\"coordinates\":[50.8443434,4.3925979]},{\"coordinates\":[50.84417059346137,4.391670213379427]}]}]}"
        }
        ```

        - The JSON string is abridged from 10 waypoints.
        - Legacy MissionFeedback serializes waypoint coordinates as [latitude, longitude]; the adapter swaps them back to [longitude, latitude].

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:678`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L678)

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:133`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L133)
        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:71`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L71)

    ??? abstract "/multi_robot/mission_init_request · c2_msgs/msg/InitMissionRequest"
        ROS topic `/multi_robot/mission_init_request`

        [Open standalone page](ros-topics/multi-robot-mission-init-request.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_topic` |
        | Interface | `/multi_robot/mission_init_request` |
        | Type | `c2_msgs/msg/InitMissionRequest` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `mission_id` |
        | message | `string<=10000` | `mission_config` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | publishes | `c2_msgs/msg/InitMissionRequest` | [`backend/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/c2_rest.cpp:55`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/c2_rest.cpp#L55) |
        | subscribes | `c2_msgs/msg/InitMissionRequest` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:54`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L54) |

        #### Verified navigation data

        ##### Mission initialization on ROS

        Phase: **INIT** · Evidence class: `verified_flow`

        ```json
        {
          "mission_id": {
            "uuid": [
              68,
              68,
              68,
              68,
              85,
              85,
              70,
              102,
              135,
              119,
              136,
              136,
              136,
              136,
              136,
              136
            ]
          },
          "mission_config": "{\"mission_id\":\"44444444-5555-4666-8777-888888888888\",\"behavior\":0,\"vehicles\":[\"f9992bb3-9871-451f-90a0-9207eb9fe6c5\"],\"objective\":{\"geometries\":[{\"geometry\":{\"geometry_type\":\"Point\",\"coordinates\":[4.39167,50.84417]}}]},\"transit\":{\"optimalization\":{\"road_usage\":1.0},\"desired_vehicle_constraints\":{\"max_speed\":1.3}}}"
        }
        ```

        - mission_config is a JSON-encoded string and uses the legacy key optimalization.
        - The UUID byte array decodes to 44444444-5555-4666-8777-888888888888.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:108`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L108)

        #### Definition evidence

        - [`backend/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/c2_rest.cpp:55`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/c2_rest.cpp#L55)
        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:54`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L54)

    ??? abstract "/multi_robot/mission_init_response · c2_msgs/msg/InitMissionResponse"
        ROS topic `/multi_robot/mission_init_response`

        [Open standalone page](ros-topics/multi-robot-mission-init-response.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_topic` |
        | Interface | `/multi_robot/mission_init_response` |
        | Type | `c2_msgs/msg/InitMissionResponse` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `mission_id` |
        | message | `string<=10000` | `mission_feedback` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | publishes | `c2_msgs/msg/InitMissionResponse` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:55`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L55) |
        | subscribes | `c2_msgs/msg/InitMissionResponse` | [`backend/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/c2_rest.cpp:54`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/c2_rest.cpp#L54) |

        #### Definition evidence

        - [`backend/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/c2_rest.cpp:54`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/c2_rest.cpp#L54)
        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:55`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L55)

    ## /multi_robot/planner

    4 extracted contracts.

    ??? abstract "/multi_robot/planner/agent · centralized_msgs/msg/Agent"
        ROS topic `/multi_robot/planner/agent`

        [Open standalone page](ros-topics/multi-robot-planner-agent.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_topic` |
        | Interface | `/multi_robot/planner/agent` |
        | Type | `centralized_msgs/msg/Agent` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `string` | `agent_id` |
        | message | `string` | `agent_profile` |
        | message | `nav_msgs/Odometry` | `odometry` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | publishes | `centralized_msgs/msg/Agent` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:67`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L67) |
        | subscribes | `centralized_msgs/msg/Agent` | [`backend/fog/planner/ros2ws/src/planner/planner/planner_node.py:134`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/planner/planner/planner_node.py#L134) |

        #### Verified navigation data

        ##### Fleet forwards Themis and its live pose to Planner

        Phase: **robot discovery** · Evidence class: `observed_excerpt`

        ```json
        {
          "agent_id": "f9992bb3-9871-451f-90a0-9207eb9fe6c5",
          "agent_profile": "<JSON profile published by Edge>",
          "odometry": {
            "pose": {
              "pose": {
                "position": {
                  "x": 4.392588,
                  "y": 50.844317,
                  "z": 0.0
                }
              }
            }
          }
        }
        ```

        - In this global-coordinate simulation, odometry x is longitude and y is latitude.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:304`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L304)

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:67`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L67)
        - [`backend/fog/planner/ros2ws/src/planner/planner/planner_node.py:134`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/planner/planner/planner_node.py#L134)

    ??? abstract "/multi_robot/planner/graph_image · CompressedImage"
        ROS topic `/multi_robot/planner/graph_image`

        [Open standalone page](ros-topics/multi-robot-planner-graph-image.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_topic` |
        | Interface | `/multi_robot/planner/graph_image` |
        | Type | `CompressedImage` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | publishes | `CompressedImage` | [`backend/fog/planner/ros2ws/src/planner/planner/planner_node.py:151`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/planner/planner/planner_node.py#L151) |

        #### Definition evidence

        - [`backend/fog/planner/ros2ws/src/planner/planner/planner_node.py:151`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/planner/planner/planner_node.py#L151)

    ??? abstract "/multi_robot/planner/planner_calculated · centralized_msgs/msg/PlanCalculated"
        ROS topic `/multi_robot/planner/planner_calculated`

        [Open standalone page](ros-topics/multi-robot-planner-planner-calculated.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_topic` |
        | Interface | `/multi_robot/planner/planner_calculated` |
        | Type | `centralized_msgs/msg/PlanCalculated` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `string` | `id` |
        | message | `string` | `plan` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | subscribes | `centralized_msgs/msg/PlanCalculated` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:62`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L62) |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:62`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L62)

    ??? abstract "/multi_robot/planner/state · std_msgs/msg/String"
        ROS topic `/multi_robot/planner/state`

        [Open standalone page](ros-topics/multi-robot-planner-state.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_topic` |
        | Interface | `/multi_robot/planner/state` |
        | Type | `std_msgs/msg/String` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `string` | `data` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | publishes | `std_msgs/msg/String` | [`backend/fog/planner/ros2ws/src/planner/planner/planner_node.py:132`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/planner/planner/planner_node.py#L132) |
        | subscribes | `std_msgs/msg/String` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:65`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L65) |

        #### Verified navigation data

        ##### Planner reports that the plan cache is ready

        Phase: **planning** · Evidence class: `runtime_observed`

        ```json
        {
          "data": "{\"planners\":[{\"mission_id\":\"44444444-5555-4666-8777-888888888888\",\"state\":2}]}"
        }
        ```

        - State 2 was observed, but usable route evidence still comes from non-empty mission feedback waypoints.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:11`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L11)

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:65`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L65)
        - [`backend/fog/planner/ros2ws/src/planner/planner/planner_node.py:132`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/planner/planner/planner_node.py#L132)

    ## /multi_robot/swarm

    1 extracted contract.

    ??? abstract "/multi_robot/swarm_log · c2_msgs/msg/SwarmLog"
        ROS topic `/multi_robot/swarm_log`

        [Open standalone page](ros-topics/multi-robot-swarm-log.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_topic` |
        | Interface | `/multi_robot/swarm_log` |
        | Type | `c2_msgs/msg/SwarmLog` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `mission_id` |
        | message | `string` | `log` |
        | message | `string` | `date` |
        | message | `uint8` | `log_type` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | publishes | `c2_msgs/msg/SwarmLog` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:70`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L70) |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:70`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L70)

    ## /{autonomy_prefix}

    6 extracted contracts.

    ??? abstract "{autonomy_prefix}/edge/multi_robot/autonomy_set_objective · autonomy_msgs/msg/AutonomySetObjective"
        ROS topic `{autonomy_prefix}/edge/multi_robot/autonomy_set_objective`

        [Open standalone page](ros-topics/autonomy-prefix-edge-multi-robot-autonomy-set-objective.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_topic` |
        | Interface | `{autonomy_prefix}/edge/multi_robot/autonomy_set_objective` |
        | Type | `autonomy_msgs/msg/AutonomySetObjective` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `bool` | `null_objective` |
        | message | `AutonomyObjective` | `objective` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | publishes | `autonomy_msgs/msg/AutonomySetObjective` | [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:51`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L51) |
        | subscribes | `autonomy_msgs/msg/AutonomySetObjective` | [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/test/test_autonomy.cpp:40`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/test/test_autonomy.cpp#L40) |

        #### Definition evidence

        - [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:51`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L51)
        - [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/test/test_autonomy.cpp:40`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/test/test_autonomy.cpp#L40)

    ??? abstract "{autonomy_prefix}/edge/multi_robot/autonomy_status · autonomy_msgs/msg/AutonomyStatus"
        ROS topic `{autonomy_prefix}/edge/multi_robot/autonomy_status`

        [Open standalone page](ros-topics/autonomy-prefix-edge-multi-robot-autonomy-status.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_topic` |
        | Interface | `{autonomy_prefix}/edge/multi_robot/autonomy_status` |
        | Type | `autonomy_msgs/msg/AutonomyStatus` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `autonomy_objective_id` |
        | message | `uint8` | `status` |
        | message | `AutonomyPrimitiveStatus[]` | `primitive_statuses` |
        | message | `uint8` | `PENDING` |
        | message | `uint8` | `ACTIVE` |
        | message | `uint8` | `COMPLETED` |
        | message | `uint8` | `FAILED` |
        | message | `uint8` | `ABORTED` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | publishes | `autonomy_msgs/msg/AutonomyStatus` | [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/test/test_autonomy.cpp:47`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/test/test_autonomy.cpp#L47) |
        | subscribes | `autonomy_msgs/msg/AutonomyStatus` | [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:64`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L64) |

        #### Definition evidence

        - [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:64`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L64)
        - [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/test/test_autonomy.cpp:47`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/test/test_autonomy.cpp#L47)

    ??? abstract "{autonomy_prefix}/edge/multi_robot/autonomy_trajectory · autonomy_msgs/msg/AutonomyTrajectory"
        ROS topic `{autonomy_prefix}/edge/multi_robot/autonomy_trajectory`

        [Open standalone page](ros-topics/autonomy-prefix-edge-multi-robot-autonomy-trajectory.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_topic` |
        | Interface | `{autonomy_prefix}/edge/multi_robot/autonomy_trajectory` |
        | Type | `autonomy_msgs/msg/AutonomyTrajectory` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `autonomy_objective_id` |
        | message | `string<=150000` | `trajectory` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | subscribes | `autonomy_msgs/msg/AutonomyTrajectory` | [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:67`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L67) |

        #### Definition evidence

        - [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:67`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L67)

    ??? abstract "{autonomy_prefix}/edge/multi_robot/detected_obstacle · autonomy_msgs/msg/DetectedObstacle"
        ROS topic `{autonomy_prefix}/edge/multi_robot/detected_obstacle`

        [Open standalone page](ros-topics/autonomy-prefix-edge-multi-robot-detected-obstacle.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_topic` |
        | Interface | `{autonomy_prefix}/edge/multi_robot/detected_obstacle` |
        | Type | `autonomy_msgs/msg/DetectedObstacle` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `obstacle_id` |
        | message | `string` | `obstacle_geofence` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | subscribes | `autonomy_msgs/msg/DetectedObstacle` | [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:61`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L61) |

        #### Definition evidence

        - [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:61`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L61)

    ??? abstract "{autonomy_prefix}/edge/multi_robot/localization · nav_msgs::msg::Odometry"
        ROS topic `{autonomy_prefix}/edge/multi_robot/localization`

        [Open standalone page](ros-topics/autonomy-prefix-edge-multi-robot-localization.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_topic` |
        | Interface | `{autonomy_prefix}/edge/multi_robot/localization` |
        | Type | `nav_msgs::msg::Odometry` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | publishes | `nav_msgs::msg::Odometry` | [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/test/test_autonomy.cpp:43`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/test/test_autonomy.cpp#L43) |
        | subscribes | `nav_msgs::msg::Odometry` | [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:55`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L55) |

        #### Definition evidence

        - [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:55`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L55)
        - [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/test/test_autonomy.cpp:43`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/test/test_autonomy.cpp#L43)

    ??? abstract "{autonomy_prefix}/edge/multi_robot/vehicle_profile · autonomy_msgs/msg/VehicleProfile"
        ROS topic `{autonomy_prefix}/edge/multi_robot/vehicle_profile`

        [Open standalone page](ros-topics/autonomy-prefix-edge-multi-robot-vehicle-profile.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_topic` |
        | Interface | `{autonomy_prefix}/edge/multi_robot/vehicle_profile` |
        | Type | `autonomy_msgs/msg/VehicleProfile` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `uint8` | `active_autonomy_mode` |
        | message | `VehicleConstraints` | `vehicle_constraints` |
        | message | `VehicleInfo` | `vehicle_info` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | publishes | `autonomy_msgs/msg/VehicleProfile` | [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/test/test_autonomy.cpp:50`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/test/test_autonomy.cpp#L50) |
        | subscribes | `autonomy_msgs/msg/VehicleProfile` | [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:58`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L58) |

        #### Definition evidence

        - [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:58`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L58)
        - [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/test/test_autonomy.cpp:50`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/test/test_autonomy.cpp#L50)


=== "ROS services (18)"

    ## /multi_robot/cmd

    1 extracted contract.

    ??? abstract "multi_robot/cmd · std_srvs::srv::Trigger"
        ROS service `multi_robot/cmd`

        [Open standalone page](ros-services/multi-robot-cmd.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_service` |
        | Interface | `multi_robot/cmd` |
        | Type | `std_srvs::srv::Trigger` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | provides | `std_srvs::srv::Trigger` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp:70`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp#L70) |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp:70`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp#L70)

    ## /multi_robot/delete

    1 extracted contract.

    ??? abstract "multi_robot/delete_mission · c2_msgs/srv/ChangeMissionStatus"
        ROS service `multi_robot/delete_mission`

        [Open standalone page](ros-services/multi-robot-delete-mission.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_service` |
        | Interface | `multi_robot/delete_mission` |
        | Type | `c2_msgs/srv/ChangeMissionStatus` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | request | `unique_identifier_msgs/UUID` | `mission_id` |
        | request | `uint8` | `mission_request_status` |
        | response | `unique_identifier_msgs/UUID` | `mission_id` |
        | response | `uint8` | `mission_status` |
        | response | `string<=2000` | `error_message` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | calls | `c2_msgs/srv/ChangeMissionStatus` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:84`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L84) |
        | provides | `c2_msgs/srv/ChangeMissionStatus` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp:48`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp#L48) |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:84`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L84)
        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp:48`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp#L48)

    ## /multi_robot/edge

    4 extracted contracts.

    ??? abstract "multi_robot/edge/agent_{agent_id}/add_task · task_msgs/srv/AddTask"
        ROS service `multi_robot/edge/agent_{agent_id}/add_task`

        [Open standalone page](ros-services/multi-robot-edge-agent-agent-id-add-task.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_service` |
        | Interface | `multi_robot/edge/agent_{agent_id}/add_task` |
        | Type | `task_msgs/srv/AddTask` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | request | `string` | `task_id` |
        | request | `uint8` | `task_type` |
        | request | `bool` | `override` |
        | request | `string<=1048576` | `task_config` |
        | request | `string` | `std` |
        | response | `string` | `task_id` |
        | response | `uint8` | `task_state` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | calls | `task_msgs/srv/AddTask` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:339`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L339) |
        | provides | `task_msgs/srv/AddTask` | [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:89`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L89) |

        #### Verified navigation data

        ##### Fleet installs the stopped waypoint task on Themis

        Phase: **APPROVE** · Evidence class: `observed_excerpt`

        ```json
        {
          "request": {
            "task_id": "<generated-task-uuid>",
            "task_type": 0,
            "override": true,
            "task_config": "{\"primitives\":[{\"primitive_id\":\"<generated-primitive-uuid>\",\"primitive_type\":\"waypoint\"}],\"objectives\":[{\"objective_id\":\"<first-generated-objective-uuid>\",\"primitives\":[{\"primitive_id\":\"<generated-primitive-uuid>\",\"parameters\":{\"coordinates\":[4.3925979,50.8443434],\"speed\":1.3,\"max_speed\":1.3}}]}]}",
            "std": ""
          },
          "response": {
            "task_id": "<generated-task-uuid>",
            "task_state": 0
          }
        }
        ```

        - task_config is an abridged JSON string; the real task contained 10 waypoint objectives.
        - Task state 0 is STOPPED: APPROVE installs the task but does not move the robot.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:750`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L750)

        #### Definition evidence

        - [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:89`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L89)
        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:339`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L339)

    ??? abstract "multi_robot/edge/agent_{agent_id}/change_state · task_msgs/srv/ChangeState"
        ROS service `multi_robot/edge/agent_{agent_id}/change_state`

        [Open standalone page](ros-services/multi-robot-edge-agent-agent-id-change-state.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_service` |
        | Interface | `multi_robot/edge/agent_{agent_id}/change_state` |
        | Type | `task_msgs/srv/ChangeState` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | request | `uint8` | `requested_state` |
        | response | `uint8` | `state` |
        | response | `string<=1024` | `feedback` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | calls | `task_msgs/srv/ChangeState` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:340`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L340) |
        | provides | `task_msgs/srv/ChangeState` | [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:92`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L92) |

        #### Definition evidence

        - [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:92`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L92)
        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:340`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L340)

    ??? abstract "multi_robot/edge/agent_{agent_id}/change_task_state · task_msgs/srv/ChangeTaskState"
        ROS service `multi_robot/edge/agent_{agent_id}/change_task_state`

        [Open standalone page](ros-services/multi-robot-edge-agent-agent-id-change-task-state.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_service` |
        | Interface | `multi_robot/edge/agent_{agent_id}/change_task_state` |
        | Type | `task_msgs/srv/ChangeTaskState` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | request | `string` | `task_id` |
        | request | `uint8` | `task_requested_state` |
        | response | `string` | `task_id` |
        | response | `uint8` | `task_state` |
        | response | `string<=1024` | `feedback` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | calls | `task_msgs/srv/ChangeTaskState` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:341`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L341) |
        | provides | `task_msgs/srv/ChangeTaskState` | [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:95`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L95) |

        #### Definition evidence

        - [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:95`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L95)
        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:341`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L341)

    ??? abstract "multi_robot/edge/agent_{agent_id}/cmd · std_srvs::srv::Trigger"
        ROS service `multi_robot/edge/agent_{agent_id}/cmd`

        [Open standalone page](ros-services/multi-robot-edge-agent-agent-id-cmd.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_service` |
        | Interface | `multi_robot/edge/agent_{agent_id}/cmd` |
        | Type | `std_srvs::srv::Trigger` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | provides | `std_srvs::srv::Trigger` | [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:101`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L101) |

        #### Definition evidence

        - [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:101`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L101)

    ## /multi_robot/fleet

    3 extracted contracts.

    ??? abstract "multi_robot/fleet_manager/change_mission_status · c2_msgs/srv/ChangeMissionStatus"
        ROS service `multi_robot/fleet_manager/change_mission_status`

        [Open standalone page](ros-services/multi-robot-fleet-manager-change-mission-status.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_service` |
        | Interface | `multi_robot/fleet_manager/change_mission_status` |
        | Type | `c2_msgs/srv/ChangeMissionStatus` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | request | `unique_identifier_msgs/UUID` | `mission_id` |
        | request | `uint8` | `mission_request_status` |
        | response | `unique_identifier_msgs/UUID` | `mission_id` |
        | response | `uint8` | `mission_status` |
        | response | `string<=2000` | `error_message` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | calls | `c2_msgs/srv/ChangeMissionStatus` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:93`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L93) |
        | provides | `c2_msgs/srv/ChangeMissionStatus` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:64`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L64) |

        #### Verified navigation data

        ##### APPROVE status request

        Phase: **APPROVE** · Evidence class: `verified_flow`

        ```json
        {
          "mission_id": {
            "uuid": [
              68,
              68,
              68,
              68,
              85,
              85,
              70,
              102,
              135,
              119,
              136,
              136,
              136,
              136,
              136,
              136
            ]
          },
          "mission_request_status": 1
        }
        ```

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:718`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L718)

        ##### START status request

        Phase: **START** · Evidence class: `verified_flow`

        ```json
        {
          "mission_id": {
            "uuid": [
              68,
              68,
              68,
              68,
              85,
              85,
              70,
              102,
              135,
              119,
              136,
              136,
              136,
              136,
              136,
              136
            ]
          },
          "mission_request_status": 2
        }
        ```

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:796`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L796)

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:93`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L93)
        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:64`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L64)

    ??? abstract "multi_robot/fleet_manager/get_agents · centralized_msgs/srv/GetAgents"
        ROS service `multi_robot/fleet_manager/get_agents`

        [Open standalone page](ros-services/multi-robot-fleet-manager-get-agents.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_service` |
        | Interface | `multi_robot/fleet_manager/get_agents` |
        | Type | `centralized_msgs/srv/GetAgents` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | request | `unique_identifier_msgs/UUID[]` | `agent_id_list` |
        | response | `centralized_msgs/Agent[]` | `agents` |
        | response | `string<=2000` | `error_message` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | calls | `centralized_msgs/srv/GetAgents` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:87`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L87) |
        | provides | `centralized_msgs/srv/GetAgents` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:60`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L60) |

        #### Verified navigation data

        ##### Mission manager requests the configured Themis agent

        Phase: **planning** · Evidence class: `verified_flow`

        ```json
        {
          "request": {
            "agent_id_list": [
              {
                "uuid": [
                  249,
                  153,
                  43,
                  179,
                  152,
                  113,
                  69,
                  31,
                  144,
                  160,
                  146,
                  7,
                  235,
                  159,
                  230,
                  197
                ]
              }
            ]
          },
          "response": {
            "agents": [
              {
                "agent_id": "f9992bb3-9871-451f-90a0-9207eb9fe6c5",
                "agent_profile": "<JSON profile published by Edge>",
                "odometry": {
                  "pose": {
                    "pose": {
                      "position": {
                        "x": 4.392588,
                        "y": 50.844317,
                        "z": 0.0
                      }
                    }
                  }
                }
              }
            ],
            "error_message": "ok"
          }
        }
        ```

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:452`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L452)

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:87`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L87)
        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:60`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L60)

    ??? abstract "multi_robot/fleet_manager/send_tasks · c2_msgs/srv/InitMission"
        ROS service `multi_robot/fleet_manager/send_tasks`

        [Open standalone page](ros-services/multi-robot-fleet-manager-send-tasks.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_service` |
        | Interface | `multi_robot/fleet_manager/send_tasks` |
        | Type | `c2_msgs/srv/InitMission` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | request | `unique_identifier_msgs/UUID` | `mission_id` |
        | request | `string<=10000` | `mission_config` |
        | response | `unique_identifier_msgs/UUID` | `mission_id` |
        | response | `string<=10000` | `mission_feedback` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | calls | `c2_msgs/srv/InitMission` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:90`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L90) |
        | provides | `c2_msgs/srv/InitMission` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:62`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L62) |

        #### Verified navigation data

        ##### Mission manager asks Fleet to dispatch the stored plan

        Phase: **APPROVE** · Evidence class: `verified_flow`

        ```json
        {
          "request": {
            "mission_id": {
              "uuid": [
                68,
                68,
                68,
                68,
                85,
                85,
                70,
                102,
                135,
                119,
                136,
                136,
                136,
                136,
                136,
                136
              ]
            },
            "mission_config": ""
          },
          "response": {
            "mission_id": {
              "uuid": [
                68,
                68,
                68,
                68,
                85,
                85,
                70,
                102,
                135,
                119,
                136,
                136,
                136,
                136,
                136,
                136
              ]
            },
            "mission_feedback": ""
          }
        }
        ```

        - This service reuses InitMission.srv, but both string fields are intentionally empty; Fleet reloads the plan from RuntimeDB.Planning by mission ID.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:1056`](https://github.com/LEBaz2211/C2_imugs2/blob/main/legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L1056), [`legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:469`](https://github.com/LEBaz2211/C2_imugs2/blob/main/legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L469)

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:90`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L90)
        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:62`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L62)

    ## /multi_robot/mission

    4 extracted contracts.

    ??? abstract "multi_robot/mission_{mission_id}/cmd · std_srvs::srv::Trigger"
        ROS service `multi_robot/mission_{mission_id}/cmd`

        [Open standalone page](ros-services/multi-robot-mission-mission-id-cmd.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_service` |
        | Interface | `multi_robot/mission_{mission_id}/cmd` |
        | Type | `std_srvs::srv::Trigger` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | provides | `std_srvs::srv::Trigger` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:149`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L149) |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:149`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L149)

    ??? abstract "multi_robot/mission_{mission_id}/environment_change · std_srvs::srv::Trigger"
        ROS service `multi_robot/mission_{mission_id}/environment_change`

        [Open standalone page](ros-services/multi-robot-mission-mission-id-environment-change.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_service` |
        | Interface | `multi_robot/mission_{mission_id}/environment_change` |
        | Type | `std_srvs::srv::Trigger` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | calls | `std_srvs::srv::Trigger` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp:419`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp#L419) |
        | provides | `std_srvs::srv::Trigger` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:78`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L78) |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:78`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L78)
        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp:419`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp#L419)

    ??? abstract "multi_robot/mission_{mission_id}/mission_status_change · c2_msgs/srv/ChangeMissionStatus"
        ROS service `multi_robot/mission_{mission_id}/mission_status_change`

        [Open standalone page](ros-services/multi-robot-mission-mission-id-mission-status-change.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_service` |
        | Interface | `multi_robot/mission_{mission_id}/mission_status_change` |
        | Type | `c2_msgs/srv/ChangeMissionStatus` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | request | `unique_identifier_msgs/UUID` | `mission_id` |
        | request | `uint8` | `mission_request_status` |
        | response | `unique_identifier_msgs/UUID` | `mission_id` |
        | response | `uint8` | `mission_status` |
        | response | `string<=2000` | `error_message` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | calls | `c2_msgs/srv/ChangeMissionStatus` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp:418`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp#L418) |
        | provides | `c2_msgs/srv/ChangeMissionStatus` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:75`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L75) |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:75`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L75)
        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp:418`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp#L418)

    ??? abstract "multi_robot/mission_{mission_id}/vehicle_change · std_srvs::srv::Trigger"
        ROS service `multi_robot/mission_{mission_id}/vehicle_change`

        [Open standalone page](ros-services/multi-robot-mission-mission-id-vehicle-change.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_service` |
        | Interface | `multi_robot/mission_{mission_id}/vehicle_change` |
        | Type | `std_srvs::srv::Trigger` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | calls | `std_srvs::srv::Trigger` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp:420`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp#L420) |
        | provides | `std_srvs::srv::Trigger` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:81`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L81) |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:81`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L81)
        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp:420`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp#L420)

    ## /multi_robot/planner

    5 extracted contracts.

    ??? abstract "/multi_robot/planner/create · centralized_msgs/srv/CreatePlanner"
        ROS service `/multi_robot/planner/create`

        [Open standalone page](ros-services/multi-robot-planner-create.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_service` |
        | Interface | `/multi_robot/planner/create` |
        | Type | `centralized_msgs/srv/CreatePlanner` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | request | `string` | `id` |
        | request | `uint8` | `priority` |
        | request | `Agent[]` | `agents` |
        | request | `string` | `config` |
        | response | `string` | `id` |
        | response | `uint8` | `state` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | calls | `centralized_msgs/srv/CreatePlanner` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:56`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L56) |
        | provides | `centralized_msgs/srv/CreatePlanner` | [`backend/fog/planner/ros2ws/src/planner/planner/planner_node.py:141`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/planner/planner/planner_node.py#L141) |

        #### Verified navigation data

        ##### Create the planner for the mission

        Phase: **planning** · Evidence class: `verified_flow`

        ```json
        {
          "request": {
            "id": "44444444-5555-4666-8777-888888888888",
            "priority": 0,
            "agents": [
              {
                "agent_id": "f9992bb3-9871-451f-90a0-9207eb9fe6c5",
                "agent_profile": "<JSON vehicle profile>",
                "odometry": {
                  "pose": {
                    "pose": {
                      "position": {
                        "x": 4.392588,
                        "y": 50.844317,
                        "z": 0.0
                      }
                    }
                  }
                }
              }
            ],
            "config": "<legacy mission_config JSON string>"
          },
          "response": {
            "id": "44444444-5555-4666-8777-888888888888",
            "state": 0
          }
        }
        ```

        - The verified run then published planner states 0, 1, and 2 asynchronously.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:475`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L475)

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:56`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L56)
        - [`backend/fog/planner/ros2ws/src/planner/planner/planner_node.py:141`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/planner/planner/planner_node.py#L141)

    ??? abstract "/multi_robot/planner/delete_planner · centralized_msgs/srv/DeletePlanner"
        ROS service `/multi_robot/planner/delete_planner`

        [Open standalone page](ros-services/multi-robot-planner-delete-planner.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_service` |
        | Interface | `/multi_robot/planner/delete_planner` |
        | Type | `centralized_msgs/srv/DeletePlanner` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | request | `string` | `id` |
        | response | `string` | `id` |
        | response | `uint8` | `state` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | provides | `centralized_msgs/srv/DeletePlanner` | [`backend/fog/planner/ros2ws/src/planner/planner/planner_node.py:147`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/planner/planner/planner_node.py#L147) |

        #### Definition evidence

        - [`backend/fog/planner/ros2ws/src/planner/planner/planner_node.py:147`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/planner/planner/planner_node.py#L147)

    ??? abstract "/multi_robot/planner/get_plan · centralized_msgs/srv/GetPlan"
        ROS service `/multi_robot/planner/get_plan`

        [Open standalone page](ros-services/multi-robot-planner-get-plan.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_service` |
        | Interface | `/multi_robot/planner/get_plan` |
        | Type | `centralized_msgs/srv/GetPlan` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | request | `string` | `id` |
        | response | `string` | `id` |
        | response | `string` | `plan` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | calls | `centralized_msgs/srv/GetPlan` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:53`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L53) |
        | provides | `centralized_msgs/srv/GetPlan` | [`backend/fog/planner/ros2ws/src/planner/planner/planner_node.py:144`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/planner/planner/planner_node.py#L144) |

        #### Verified navigation data

        ##### Retrieve the generated robot task

        Phase: **plan retrieval** · Evidence class: `observed_excerpt`

        ```json
        {
          "request": {
            "id": "44444444-5555-4666-8777-888888888888"
          },
          "response": {
            "id": "44444444-5555-4666-8777-888888888888",
            "plan": "<JSON-encoded TaskPlan containing one Themis task and 10 waypoint objectives>"
          }
        }
        ```

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:641`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L641)

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:53`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L53)
        - [`backend/fog/planner/ros2ws/src/planner/planner/planner_node.py:144`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/planner/planner/planner_node.py#L144)

    ??? abstract "/multi_robot/planner/set_agents · centralized_msgs/srv/UpdatePlannerAgents"
        ROS service `/multi_robot/planner/set_agents`

        [Open standalone page](ros-services/multi-robot-planner-set-agents.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_service` |
        | Interface | `/multi_robot/planner/set_agents` |
        | Type | `centralized_msgs/srv/UpdatePlannerAgents` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | request | `string` | `id` |
        | request | `Agent[]` | `agents` |
        | response | `string` | `id` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | calls | `centralized_msgs/srv/UpdatePlannerAgents` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:59`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L59) |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:59`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L59)

    ??? abstract "multi_robot/planner/delete · centralized_msgs/srv/DeletePlanner"
        ROS service `multi_robot/planner/delete`

        [Open standalone page](ros-services/multi-robot-planner-delete.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_service` |
        | Interface | `multi_robot/planner/delete` |
        | Type | `centralized_msgs/srv/DeletePlanner` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | request | `string` | `id` |
        | response | `string` | `id` |
        | response | `uint8` | `state` |

        #### Source usages

        | Relationship | Contract | Evidence |
        |---|---|---|
        | calls | `centralized_msgs/srv/DeletePlanner` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp:42`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp#L42) |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp:42`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp#L42)


=== "ROS types (49)"

    ## autonomy_msgs · MSG

    16 extracted contracts.

    ??? abstract "autonomy_msgs/msg/AutonomyObjective · ros_type"
        MSG definition from `autonomy_msgs`

        [Open standalone page](ros-types/autonomy-msgs-msg-autonomyobjective.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/AutonomyObjective.msg` |
        | Package | `autonomy_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `id` |
        | message | `string<=100` | `objective_type` |
        | message | `bool` | `parallel_execution` |
        | message | `string[]` | `primitives` |
        | message | `float32` | `max_speed` |
        | message | `uint8` | `mobility_profile` |

        #### Verified navigation data

        ##### Edge sends the current waypoint to autonomy

        Phase: **execution** · Evidence class: `observed_excerpt`

        ```json
        {
          "null_objective": false,
          "objective": {
            "id": "<first-generated-objective-uuid>",
            "objective_type": "combined_primitives",
            "parallel_execution": true,
            "primitives": [
              "{\"id\":\"<generated-primitive-uuid>\",\"type\":\"waypoint\",\"parameters\":{\"coordinates\":[4.3925979,50.8443434],\"speed\":1.3,\"max_speed\":1.3,\"mobility_profile\":0,\"wait_time\":0}}"
            ],
            "max_speed": 1.3,
            "mobility_profile": 0
          }
        }
        ```

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:850`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L850)

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/AutonomyObjective.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/AutonomyObjective.msg#L1)

    ??? abstract "autonomy_msgs/msg/AutonomyPrimitiveStatus · ros_type"
        MSG definition from `autonomy_msgs`

        [Open standalone page](ros-types/autonomy-msgs-msg-autonomyprimitivestatus.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/AutonomyPrimitiveStatus.msg` |
        | Package | `autonomy_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `primitive_id` |
        | message | `string` | `primitive_type` |
        | message | `uint8` | `status` |
        | message | `float64` | `progress` |
        | message | `string` | `feedback` |
        | message | `uint8` | `PENDING` |
        | message | `uint8` | `ACTIVE` |
        | message | `uint8` | `COMPLETED` |
        | message | `uint8` | `FAILED` |
        | message | `uint8` | `ABORTED` |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/AutonomyPrimitiveStatus.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/AutonomyPrimitiveStatus.msg#L1)

    ??? abstract "autonomy_msgs/msg/AutonomySetObjective · ros_type"
        MSG definition from `autonomy_msgs`

        [Open standalone page](ros-types/autonomy-msgs-msg-autonomysetobjective.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/AutonomySetObjective.msg` |
        | Package | `autonomy_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `bool` | `null_objective` |
        | message | `AutonomyObjective` | `objective` |

        #### Verified navigation data

        ##### Edge sends the current waypoint to autonomy

        Phase: **execution** · Evidence class: `observed_excerpt`

        ```json
        {
          "null_objective": false,
          "objective": {
            "id": "<first-generated-objective-uuid>",
            "objective_type": "combined_primitives",
            "parallel_execution": true,
            "primitives": [
              "{\"id\":\"<generated-primitive-uuid>\",\"type\":\"waypoint\",\"parameters\":{\"coordinates\":[4.3925979,50.8443434],\"speed\":1.3,\"max_speed\":1.3,\"mobility_profile\":0,\"wait_time\":0}}"
            ],
            "max_speed": 1.3,
            "mobility_profile": 0
          }
        }
        ```

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:850`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L850)

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/AutonomySetObjective.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/AutonomySetObjective.msg#L1)

    ??? abstract "autonomy_msgs/msg/AutonomyStatus · ros_type"
        MSG definition from `autonomy_msgs`

        [Open standalone page](ros-types/autonomy-msgs-msg-autonomystatus.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/AutonomyStatus.msg` |
        | Package | `autonomy_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `autonomy_objective_id` |
        | message | `uint8` | `status` |
        | message | `AutonomyPrimitiveStatus[]` | `primitive_statuses` |
        | message | `uint8` | `PENDING` |
        | message | `uint8` | `ACTIVE` |
        | message | `uint8` | `COMPLETED` |
        | message | `uint8` | `FAILED` |
        | message | `uint8` | `ABORTED` |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/AutonomyStatus.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/AutonomyStatus.msg#L1)

    ??? abstract "autonomy_msgs/msg/AutonomyTrajectory · ros_type"
        MSG definition from `autonomy_msgs`

        [Open standalone page](ros-types/autonomy-msgs-msg-autonomytrajectory.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/AutonomyTrajectory.msg` |
        | Package | `autonomy_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `autonomy_objective_id` |
        | message | `string<=150000` | `trajectory` |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/AutonomyTrajectory.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/AutonomyTrajectory.msg#L1)

    ??? abstract "autonomy_msgs/msg/DetectedObstacle · ros_type"
        MSG definition from `autonomy_msgs`

        [Open standalone page](ros-types/autonomy-msgs-msg-detectedobstacle.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/DetectedObstacle.msg` |
        | Package | `autonomy_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `obstacle_id` |
        | message | `string` | `obstacle_geofence` |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/DetectedObstacle.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/DetectedObstacle.msg#L1)

    ??? abstract "autonomy_msgs/msg/Localization · ros_type"
        MSG definition from `autonomy_msgs`

        [Open standalone page](ros-types/autonomy-msgs-msg-localization.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/Localization.msg` |
        | Package | `autonomy_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `std_msgs/Header` | `header` |
        | message | `geographic_msgs/GeoPoint` | `position` |
        | message | `geometry_msgs/Quaternion` | `orientation` |
        | message | `float64[36]` | `covariance` |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/Localization.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/Localization.msg#L1)

    ??? abstract "autonomy_msgs/msg/MissionData · ros_type"
        MSG definition from `autonomy_msgs`

        [Open standalone page](ros-types/autonomy-msgs-msg-missiondata.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/.devcontainer/msg/MissionData.msg` |
        | Package | `autonomy_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `uint8` | `active_autonomy_mode` |
        | message | `uint8` | `mission_status` |
        | message | `VehicleConstraints` | `vehicle_constraints` |
        | message | `VehicleInfo` | `vehicle_info` |
        | message | `float64` | `speed` |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/.devcontainer/msg/MissionData.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/.devcontainer/msg/MissionData.msg#L1)

    ??? abstract "autonomy_msgs/msg/SensorProperties · ros_type"
        MSG definition from `autonomy_msgs`

        [Open standalone page](ros-types/autonomy-msgs-msg-sensorproperties.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/SensorProperties.msg` |
        | Package | `autonomy_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `uint8` | `type` |
        | message | `uint8` | `status` |
        | message | `float64[]` | `field_of_view` |

        #### Verified navigation data

        ##### Autonomy publishes the Themis vehicle profile

        Phase: **robot discovery** · Evidence class: `runtime_observed`

        ```json
        {
          "active_autonomy_mode": 1,
          "vehicle_constraints": {
            "max_speed": {
              "linear": {
                "x": 4.5,
                "y": 0.0,
                "z": 0.0
              },
              "angular": {
                "x": 0.0,
                "y": 0.0,
                "z": 0.0
              }
            },
            "max_acceleration": {
              "linear": {
                "x": 8.0,
                "y": 0.0,
                "z": 0.0
              },
              "angular": {
                "x": 0.0,
                "y": 0.0,
                "z": 0.0
              }
            },
            "max_weight": 16.0,
            "max_tilt_angle": 1.8
          },
          "vehicle_info": {
            "vehicle_type": "ugv",
            "fuel_status_pct": 85,
            "fuel_hours": 1.5,
            "battery_status_pct": 90,
            "battery_hours": 3.0,
            "sensor_list": [
              {
                "type": 1,
                "status": 1,
                "field_of_view": [
                  360.0,
                  3.14
                ]
              },
              {
                "type": 2,
                "status": 1,
                "field_of_view": [
                  120.0,
                  2.0
                ]
              },
              {
                "type": 3,
                "status": 1,
                "field_of_view": [
                  180.0,
                  3.14
                ]
              }
            ],
            "vehicle_dimensions": [
              0.9,
              0.6,
              0.55
            ]
          }
        }
        ```

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`legacy_ros/config/config_autonomy.yaml:6`](https://github.com/LEBaz2211/C2_imugs2/blob/main/legacy_ros/config/config_autonomy.yaml#L6)

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/SensorProperties.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/SensorProperties.msg#L1)

    ??? abstract "autonomy_msgs/msg/SwarmingObjective · ros_type"
        MSG definition from `autonomy_msgs`

        [Open standalone page](ros-types/autonomy-msgs-msg-swarmingobjective.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/.devcontainer/msg/SwarmingObjective.msg` |
        | Package | `autonomy_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `id` |
        | message | `string<=100` | `arrival_point` |
        | message | `string<=150000[<=1]` | `path` |
        | message | `float32` | `max_speed` |
        | message | `uint8` | `mobility_profile` |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/.devcontainer/msg/SwarmingObjective.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/.devcontainer/msg/SwarmingObjective.msg#L1)

    ??? abstract "autonomy_msgs/msg/SwarmingSetObjective · ros_type"
        MSG definition from `autonomy_msgs`

        [Open standalone page](ros-types/autonomy-msgs-msg-swarmingsetobjective.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/.devcontainer/msg/SwarmingSetObjective.msg` |
        | Package | `autonomy_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `bool` | `null_objective` |
        | message | `AutonomyObjective` | `objective` |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/.devcontainer/msg/SwarmingSetObjective.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/.devcontainer/msg/SwarmingSetObjective.msg#L1)

    ??? abstract "autonomy_msgs/msg/SwarmingStatus · ros_type"
        MSG definition from `autonomy_msgs`

        [Open standalone page](ros-types/autonomy-msgs-msg-swarmingstatus.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/.devcontainer/msg/SwarmingStatus.msg` |
        | Package | `autonomy_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `autonomy_objective_id` |
        | message | `uint8` | `status` |
        | message | `uint32` | `time_to_arrival` |
        | message | `uint32` | `distance_to_arrival` |
        | message | `float32` | `needed_energy_to_arrival` |
        | message | `string<=2000` | `blockages` |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/.devcontainer/msg/SwarmingStatus.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/.devcontainer/msg/SwarmingStatus.msg#L1)

    ??? abstract "autonomy_msgs/msg/SwarmingTrajectory · ros_type"
        MSG definition from `autonomy_msgs`

        [Open standalone page](ros-types/autonomy-msgs-msg-swarmingtrajectory.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/.devcontainer/msg/SwarmingTrajectory.msg` |
        | Package | `autonomy_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `autonomy_objective_id` |
        | message | `string<=150000` | `trajectory` |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/.devcontainer/msg/SwarmingTrajectory.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/.devcontainer/msg/SwarmingTrajectory.msg#L1)

    ??? abstract "autonomy_msgs/msg/VehicleConstraints · ros_type"
        MSG definition from `autonomy_msgs`

        [Open standalone page](ros-types/autonomy-msgs-msg-vehicleconstraints.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/VehicleConstraints.msg` |
        | Package | `autonomy_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `geometry_msgs/Twist` | `max_speed` |
        | message | `geometry_msgs/Accel` | `max_acceleration` |
        | message | `float64` | `max_weight` |
        | message | `float64` | `max_tilt_angle` |

        #### Verified navigation data

        ##### Autonomy publishes the Themis vehicle profile

        Phase: **robot discovery** · Evidence class: `runtime_observed`

        ```json
        {
          "active_autonomy_mode": 1,
          "vehicle_constraints": {
            "max_speed": {
              "linear": {
                "x": 4.5,
                "y": 0.0,
                "z": 0.0
              },
              "angular": {
                "x": 0.0,
                "y": 0.0,
                "z": 0.0
              }
            },
            "max_acceleration": {
              "linear": {
                "x": 8.0,
                "y": 0.0,
                "z": 0.0
              },
              "angular": {
                "x": 0.0,
                "y": 0.0,
                "z": 0.0
              }
            },
            "max_weight": 16.0,
            "max_tilt_angle": 1.8
          },
          "vehicle_info": {
            "vehicle_type": "ugv",
            "fuel_status_pct": 85,
            "fuel_hours": 1.5,
            "battery_status_pct": 90,
            "battery_hours": 3.0,
            "sensor_list": [
              {
                "type": 1,
                "status": 1,
                "field_of_view": [
                  360.0,
                  3.14
                ]
              },
              {
                "type": 2,
                "status": 1,
                "field_of_view": [
                  120.0,
                  2.0
                ]
              },
              {
                "type": 3,
                "status": 1,
                "field_of_view": [
                  180.0,
                  3.14
                ]
              }
            ],
            "vehicle_dimensions": [
              0.9,
              0.6,
              0.55
            ]
          }
        }
        ```

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`legacy_ros/config/config_autonomy.yaml:6`](https://github.com/LEBaz2211/C2_imugs2/blob/main/legacy_ros/config/config_autonomy.yaml#L6)

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/VehicleConstraints.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/VehicleConstraints.msg#L1)

    ??? abstract "autonomy_msgs/msg/VehicleInfo · ros_type"
        MSG definition from `autonomy_msgs`

        [Open standalone page](ros-types/autonomy-msgs-msg-vehicleinfo.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/VehicleInfo.msg` |
        | Package | `autonomy_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `string` | `vehicle_type` |
        | message | `uint8` | `fuel_status_pct` |
        | message | `float32` | `fuel_hours` |
        | message | `uint8` | `battery_status_pct` |
        | message | `float32` | `battery_hours` |
        | message | `SensorProperties[]` | `sensor_list` |
        | message | `float32[]` | `vehicle_dimensions` |

        #### Verified navigation data

        ##### Autonomy publishes the Themis vehicle profile

        Phase: **robot discovery** · Evidence class: `runtime_observed`

        ```json
        {
          "active_autonomy_mode": 1,
          "vehicle_constraints": {
            "max_speed": {
              "linear": {
                "x": 4.5,
                "y": 0.0,
                "z": 0.0
              },
              "angular": {
                "x": 0.0,
                "y": 0.0,
                "z": 0.0
              }
            },
            "max_acceleration": {
              "linear": {
                "x": 8.0,
                "y": 0.0,
                "z": 0.0
              },
              "angular": {
                "x": 0.0,
                "y": 0.0,
                "z": 0.0
              }
            },
            "max_weight": 16.0,
            "max_tilt_angle": 1.8
          },
          "vehicle_info": {
            "vehicle_type": "ugv",
            "fuel_status_pct": 85,
            "fuel_hours": 1.5,
            "battery_status_pct": 90,
            "battery_hours": 3.0,
            "sensor_list": [
              {
                "type": 1,
                "status": 1,
                "field_of_view": [
                  360.0,
                  3.14
                ]
              },
              {
                "type": 2,
                "status": 1,
                "field_of_view": [
                  120.0,
                  2.0
                ]
              },
              {
                "type": 3,
                "status": 1,
                "field_of_view": [
                  180.0,
                  3.14
                ]
              }
            ],
            "vehicle_dimensions": [
              0.9,
              0.6,
              0.55
            ]
          }
        }
        ```

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`legacy_ros/config/config_autonomy.yaml:6`](https://github.com/LEBaz2211/C2_imugs2/blob/main/legacy_ros/config/config_autonomy.yaml#L6)

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/VehicleInfo.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/VehicleInfo.msg#L1)

    ??? abstract "autonomy_msgs/msg/VehicleProfile · ros_type"
        MSG definition from `autonomy_msgs`

        [Open standalone page](ros-types/autonomy-msgs-msg-vehicleprofile.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/VehicleProfile.msg` |
        | Package | `autonomy_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `uint8` | `active_autonomy_mode` |
        | message | `VehicleConstraints` | `vehicle_constraints` |
        | message | `VehicleInfo` | `vehicle_info` |

        #### Verified navigation data

        ##### Autonomy publishes the Themis vehicle profile

        Phase: **robot discovery** · Evidence class: `runtime_observed`

        ```json
        {
          "active_autonomy_mode": 1,
          "vehicle_constraints": {
            "max_speed": {
              "linear": {
                "x": 4.5,
                "y": 0.0,
                "z": 0.0
              },
              "angular": {
                "x": 0.0,
                "y": 0.0,
                "z": 0.0
              }
            },
            "max_acceleration": {
              "linear": {
                "x": 8.0,
                "y": 0.0,
                "z": 0.0
              },
              "angular": {
                "x": 0.0,
                "y": 0.0,
                "z": 0.0
              }
            },
            "max_weight": 16.0,
            "max_tilt_angle": 1.8
          },
          "vehicle_info": {
            "vehicle_type": "ugv",
            "fuel_status_pct": 85,
            "fuel_hours": 1.5,
            "battery_status_pct": 90,
            "battery_hours": 3.0,
            "sensor_list": [
              {
                "type": 1,
                "status": 1,
                "field_of_view": [
                  360.0,
                  3.14
                ]
              },
              {
                "type": 2,
                "status": 1,
                "field_of_view": [
                  120.0,
                  2.0
                ]
              },
              {
                "type": 3,
                "status": 1,
                "field_of_view": [
                  180.0,
                  3.14
                ]
              }
            ],
            "vehicle_dimensions": [
              0.9,
              0.6,
              0.55
            ]
          }
        }
        ```

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`legacy_ros/config/config_autonomy.yaml:6`](https://github.com/LEBaz2211/C2_imugs2/blob/main/legacy_ros/config/config_autonomy.yaml#L6)

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/VehicleProfile.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/VehicleProfile.msg#L1)

    ## c2_msgs · MSG

    8 extracted contracts.

    ??? abstract "c2_msgs/msg/ChangeMissionStatusRequest · ros_type"
        MSG definition from `c2_msgs`

        [Open standalone page](ros-types/c2-msgs-msg-changemissionstatusrequest.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/centralized-coordination/src/message_packages/c2_msgs/msg/ChangeMissionStatusRequest.msg` |
        | Package | `c2_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `mission_id` |
        | message | `uint8` | `mission_request_status` |

        #### Verified navigation data

        ##### APPROVE status request

        Phase: **APPROVE** · Evidence class: `verified_flow`

        ```json
        {
          "mission_id": {
            "uuid": [
              68,
              68,
              68,
              68,
              85,
              85,
              70,
              102,
              135,
              119,
              136,
              136,
              136,
              136,
              136,
              136
            ]
          },
          "mission_request_status": 1
        }
        ```

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:718`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L718)

        ##### START status request

        Phase: **START** · Evidence class: `verified_flow`

        ```json
        {
          "mission_id": {
            "uuid": [
              68,
              68,
              68,
              68,
              85,
              85,
              70,
              102,
              135,
              119,
              136,
              136,
              136,
              136,
              136,
              136
            ]
          },
          "mission_request_status": 2
        }
        ```

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:796`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L796)

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/message_packages/c2_msgs/msg/ChangeMissionStatusRequest.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/c2_msgs/msg/ChangeMissionStatusRequest.msg#L1)

    ??? abstract "c2_msgs/msg/ChangeMissionStatusResponse · ros_type"
        MSG definition from `c2_msgs`

        [Open standalone page](ros-types/c2-msgs-msg-changemissionstatusresponse.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/centralized-coordination/src/message_packages/c2_msgs/msg/ChangeMissionStatusResponse.msg` |
        | Package | `c2_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `mission_id` |
        | message | `uint8` | `mission_status` |
        | message | `string<=2000` | `error_message` |

        #### Verified navigation data

        ##### Mission manager accepts the APPROVE transition

        Phase: **APPROVE** · Evidence class: `verified_flow`

        ```json
        {
          "mission_id": {
            "uuid": [
              68,
              68,
              68,
              68,
              85,
              85,
              70,
              102,
              135,
              119,
              136,
              136,
              136,
              136,
              136,
              136
            ]
          },
          "mission_status": 4,
          "error_message": ""
        }
        ```

        - Mission status 4 is ACCEPTED.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:876`](https://github.com/LEBaz2211/C2_imugs2/blob/main/legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L876)

        ##### Mission manager accepts the START transition

        Phase: **START** · Evidence class: `verified_flow`

        ```json
        {
          "mission_id": {
            "uuid": [
              68,
              68,
              68,
              68,
              85,
              85,
              70,
              102,
              135,
              119,
              136,
              136,
              136,
              136,
              136,
              136
            ]
          },
          "mission_status": 5,
          "error_message": ""
        }
        ```

        - Mission status 5 is STARTED.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:876`](https://github.com/LEBaz2211/C2_imugs2/blob/main/legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L876)

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/message_packages/c2_msgs/msg/ChangeMissionStatusResponse.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/c2_msgs/msg/ChangeMissionStatusResponse.msg#L1)

    ??? abstract "c2_msgs/msg/ChangeMissionVehicleRequest · ros_type"
        MSG definition from `c2_msgs`

        [Open standalone page](ros-types/c2-msgs-msg-changemissionvehiclerequest.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/centralized-coordination/src/message_packages/c2_msgs/msg/ChangeMissionVehicleRequest.msg` |
        | Package | `c2_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `mission_id` |
        | message | `string[]` | `vehicule_id_list` |
        | message | `uint8` | `vehicle_changes` |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/message_packages/c2_msgs/msg/ChangeMissionVehicleRequest.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/c2_msgs/msg/ChangeMissionVehicleRequest.msg#L1)

    ??? abstract "c2_msgs/msg/ChangeMissionVehicleResponse · ros_type"
        MSG definition from `c2_msgs`

        [Open standalone page](ros-types/c2-msgs-msg-changemissionvehicleresponse.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/centralized-coordination/src/message_packages/c2_msgs/msg/ChangeMissionVehicleResponse.msg` |
        | Package | `c2_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `mission_id` |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/message_packages/c2_msgs/msg/ChangeMissionVehicleResponse.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/c2_msgs/msg/ChangeMissionVehicleResponse.msg#L1)

    ??? abstract "c2_msgs/msg/InitMissionRequest · ros_type"
        MSG definition from `c2_msgs`

        [Open standalone page](ros-types/c2-msgs-msg-initmissionrequest.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/centralized-coordination/src/message_packages/c2_msgs/msg/InitMissionRequest.msg` |
        | Package | `c2_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `mission_id` |
        | message | `string<=10000` | `mission_config` |

        #### Verified navigation data

        ##### Mission initialization on ROS

        Phase: **INIT** · Evidence class: `verified_flow`

        ```json
        {
          "mission_id": {
            "uuid": [
              68,
              68,
              68,
              68,
              85,
              85,
              70,
              102,
              135,
              119,
              136,
              136,
              136,
              136,
              136,
              136
            ]
          },
          "mission_config": "{\"mission_id\":\"44444444-5555-4666-8777-888888888888\",\"behavior\":0,\"vehicles\":[\"f9992bb3-9871-451f-90a0-9207eb9fe6c5\"],\"objective\":{\"geometries\":[{\"geometry\":{\"geometry_type\":\"Point\",\"coordinates\":[4.39167,50.84417]}}]},\"transit\":{\"optimalization\":{\"road_usage\":1.0},\"desired_vehicle_constraints\":{\"max_speed\":1.3}}}"
        }
        ```

        - mission_config is a JSON-encoded string and uses the legacy key optimalization.
        - The UUID byte array decodes to 44444444-5555-4666-8777-888888888888.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:108`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L108)

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/message_packages/c2_msgs/msg/InitMissionRequest.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/c2_msgs/msg/InitMissionRequest.msg#L1)

    ??? abstract "c2_msgs/msg/InitMissionResponse · ros_type"
        MSG definition from `c2_msgs`

        [Open standalone page](ros-types/c2-msgs-msg-initmissionresponse.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/centralized-coordination/src/message_packages/c2_msgs/msg/InitMissionResponse.msg` |
        | Package | `c2_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `mission_id` |
        | message | `string<=10000` | `mission_feedback` |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/message_packages/c2_msgs/msg/InitMissionResponse.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/c2_msgs/msg/InitMissionResponse.msg#L1)

    ??? abstract "c2_msgs/msg/MissionFeedback · ros_type"
        MSG definition from `c2_msgs`

        [Open standalone page](ros-types/c2-msgs-msg-missionfeedback.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/centralized-coordination/src/message_packages/c2_msgs/msg/MissionFeedback.msg` |
        | Package | `c2_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `mission_id` |
        | message | `string` | `mission_feedback` |

        #### Verified navigation data

        ##### Mission feedback proving that a route was received

        Phase: **PLANNED** · Evidence class: `observed_excerpt`

        ```json
        {
          "mission_id": {
            "uuid": [
              68,
              68,
              68,
              68,
              85,
              85,
              70,
              102,
              135,
              119,
              136,
              136,
              136,
              136,
              136,
              136
            ]
          },
          "mission_feedback": "{\"mission_id\":\"44444444-5555-4666-8777-888888888888\",\"behavior\":0,\"status\":1,\"requested_status\":0,\"tasks\":[{\"vehicle_id\":\"f9992bb3-9871-451f-90a0-9207eb9fe6c5\",\"task_id\":\"<generated-task-uuid>\",\"waypoints\":[{\"coordinates\":[50.8443434,4.3925979]},{\"coordinates\":[50.84417059346137,4.391670213379427]}]}]}"
        }
        ```

        - The JSON string is abridged from 10 waypoints.
        - Legacy MissionFeedback serializes waypoint coordinates as [latitude, longitude]; the adapter swaps them back to [longitude, latitude].

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:678`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L678)

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/message_packages/c2_msgs/msg/MissionFeedback.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/c2_msgs/msg/MissionFeedback.msg#L1)

    ??? abstract "c2_msgs/msg/SwarmLog · ros_type"
        MSG definition from `c2_msgs`

        [Open standalone page](ros-types/c2-msgs-msg-swarmlog.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/centralized-coordination/src/message_packages/c2_msgs/msg/SwarmLog.msg` |
        | Package | `c2_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `mission_id` |
        | message | `string` | `log` |
        | message | `string` | `date` |
        | message | `uint8` | `log_type` |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/message_packages/c2_msgs/msg/SwarmLog.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/c2_msgs/msg/SwarmLog.msg#L1)

    ## c2_msgs · SRV

    3 extracted contracts.

    ??? abstract "c2_msgs/srv/ChangeMissionStatus · ros_type"
        SRV definition from `c2_msgs`

        [Open standalone page](ros-types/c2-msgs-srv-changemissionstatus.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/centralized-coordination/src/message_packages/c2_msgs/srv/ChangeMissionStatus.srv` |
        | Package | `c2_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | request | `unique_identifier_msgs/UUID` | `mission_id` |
        | request | `uint8` | `mission_request_status` |
        | response | `unique_identifier_msgs/UUID` | `mission_id` |
        | response | `uint8` | `mission_status` |
        | response | `string<=2000` | `error_message` |

        #### Verified navigation data

        ##### APPROVE status request

        Phase: **APPROVE** · Evidence class: `verified_flow`

        ```json
        {
          "mission_id": {
            "uuid": [
              68,
              68,
              68,
              68,
              85,
              85,
              70,
              102,
              135,
              119,
              136,
              136,
              136,
              136,
              136,
              136
            ]
          },
          "mission_request_status": 1
        }
        ```

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:718`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L718)

        ##### START status request

        Phase: **START** · Evidence class: `verified_flow`

        ```json
        {
          "mission_id": {
            "uuid": [
              68,
              68,
              68,
              68,
              85,
              85,
              70,
              102,
              135,
              119,
              136,
              136,
              136,
              136,
              136,
              136
            ]
          },
          "mission_request_status": 2
        }
        ```

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:796`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L796)

        ##### Mission manager accepts the APPROVE transition

        Phase: **APPROVE** · Evidence class: `verified_flow`

        ```json
        {
          "mission_id": {
            "uuid": [
              68,
              68,
              68,
              68,
              85,
              85,
              70,
              102,
              135,
              119,
              136,
              136,
              136,
              136,
              136,
              136
            ]
          },
          "mission_status": 4,
          "error_message": ""
        }
        ```

        - Mission status 4 is ACCEPTED.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:876`](https://github.com/LEBaz2211/C2_imugs2/blob/main/legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L876)

        ##### Mission manager accepts the START transition

        Phase: **START** · Evidence class: `verified_flow`

        ```json
        {
          "mission_id": {
            "uuid": [
              68,
              68,
              68,
              68,
              85,
              85,
              70,
              102,
              135,
              119,
              136,
              136,
              136,
              136,
              136,
              136
            ]
          },
          "mission_status": 5,
          "error_message": ""
        }
        ```

        - Mission status 5 is STARTED.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:876`](https://github.com/LEBaz2211/C2_imugs2/blob/main/legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L876)

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/message_packages/c2_msgs/srv/ChangeMissionStatus.srv:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/c2_msgs/srv/ChangeMissionStatus.srv#L1)

    ??? abstract "c2_msgs/srv/ChangeMissionVehicle · ros_type"
        SRV definition from `c2_msgs`

        [Open standalone page](ros-types/c2-msgs-srv-changemissionvehicle.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/centralized-coordination/src/message_packages/c2_msgs/srv/ChangeMissionVehicle.srv` |
        | Package | `c2_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | request | `unique_identifier_msgs/UUID` | `mission_id` |
        | request | `unique_identifier_msgs/UUID[]` | `vehicule_id_list` |
        | request | `uint8` | `vehicle_changes` |
        | response | `unique_identifier_msgs/UUID` | `mission_id` |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/message_packages/c2_msgs/srv/ChangeMissionVehicle.srv:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/c2_msgs/srv/ChangeMissionVehicle.srv#L1)

    ??? abstract "c2_msgs/srv/InitMission · ros_type"
        SRV definition from `c2_msgs`

        [Open standalone page](ros-types/c2-msgs-srv-initmission.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/centralized-coordination/src/message_packages/c2_msgs/srv/InitMission.srv` |
        | Package | `c2_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | request | `unique_identifier_msgs/UUID` | `mission_id` |
        | request | `string<=10000` | `mission_config` |
        | response | `unique_identifier_msgs/UUID` | `mission_id` |
        | response | `string<=10000` | `mission_feedback` |

        #### Verified navigation data

        ##### Mission initialization on ROS

        Phase: **INIT** · Evidence class: `verified_flow`

        ```json
        {
          "mission_id": {
            "uuid": [
              68,
              68,
              68,
              68,
              85,
              85,
              70,
              102,
              135,
              119,
              136,
              136,
              136,
              136,
              136,
              136
            ]
          },
          "mission_config": "{\"mission_id\":\"44444444-5555-4666-8777-888888888888\",\"behavior\":0,\"vehicles\":[\"f9992bb3-9871-451f-90a0-9207eb9fe6c5\"],\"objective\":{\"geometries\":[{\"geometry\":{\"geometry_type\":\"Point\",\"coordinates\":[4.39167,50.84417]}}]},\"transit\":{\"optimalization\":{\"road_usage\":1.0},\"desired_vehicle_constraints\":{\"max_speed\":1.3}}}"
        }
        ```

        - mission_config is a JSON-encoded string and uses the legacy key optimalization.
        - The UUID byte array decodes to 44444444-5555-4666-8777-888888888888.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:108`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L108)

        ##### Mission manager asks Fleet to dispatch the stored plan

        Phase: **APPROVE** · Evidence class: `verified_flow`

        ```json
        {
          "request": {
            "mission_id": {
              "uuid": [
                68,
                68,
                68,
                68,
                85,
                85,
                70,
                102,
                135,
                119,
                136,
                136,
                136,
                136,
                136,
                136
              ]
            },
            "mission_config": ""
          },
          "response": {
            "mission_id": {
              "uuid": [
                68,
                68,
                68,
                68,
                85,
                85,
                70,
                102,
                135,
                119,
                136,
                136,
                136,
                136,
                136,
                136
              ]
            },
            "mission_feedback": ""
          }
        }
        ```

        - This service reuses InitMission.srv, but both string fields are intentionally empty; Fleet reloads the plan from RuntimeDB.Planning by mission ID.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:1056`](https://github.com/LEBaz2211/C2_imugs2/blob/main/legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L1056), [`legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:469`](https://github.com/LEBaz2211/C2_imugs2/blob/main/legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L469)

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/message_packages/c2_msgs/srv/InitMission.srv:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/c2_msgs/srv/InitMission.srv#L1)

    ## centralized_msgs · MSG

    2 extracted contracts.

    ??? abstract "centralized_msgs/msg/Agent · ros_type"
        MSG definition from `centralized_msgs`

        [Open standalone page](ros-types/centralized-msgs-msg-agent.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/msg/Agent.msg` |
        | Package | `centralized_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `string` | `agent_id` |
        | message | `string` | `agent_profile` |
        | message | `nav_msgs/Odometry` | `odometry` |

        #### Verified navigation data

        ##### Fleet forwards Themis and its live pose to Planner

        Phase: **robot discovery** · Evidence class: `observed_excerpt`

        ```json
        {
          "agent_id": "f9992bb3-9871-451f-90a0-9207eb9fe6c5",
          "agent_profile": "<JSON profile published by Edge>",
          "odometry": {
            "pose": {
              "pose": {
                "position": {
                  "x": 4.392588,
                  "y": 50.844317,
                  "z": 0.0
                }
              }
            }
          }
        }
        ```

        - In this global-coordinate simulation, odometry x is longitude and y is latitude.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:304`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L304)

        #### Definition evidence

        - [`backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/msg/Agent.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/msg/Agent.msg#L1)

    ??? abstract "centralized_msgs/msg/PlanCalculated · ros_type"
        MSG definition from `centralized_msgs`

        [Open standalone page](ros-types/centralized-msgs-msg-plancalculated.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/msg/PlanCalculated.msg` |
        | Package | `centralized_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `string` | `id` |
        | message | `string` | `plan` |

        #### Definition evidence

        - [`backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/msg/PlanCalculated.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/msg/PlanCalculated.msg#L1)

    ## centralized_msgs · SRV

    6 extracted contracts.

    ??? abstract "centralized_msgs/srv/CreatePlanner · ros_type"
        SRV definition from `centralized_msgs`

        [Open standalone page](ros-types/centralized-msgs-srv-createplanner.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/srv/CreatePlanner.srv` |
        | Package | `centralized_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | request | `string` | `id` |
        | request | `uint8` | `priority` |
        | request | `Agent[]` | `agents` |
        | request | `string` | `config` |
        | response | `string` | `id` |
        | response | `uint8` | `state` |

        #### Verified navigation data

        ##### Create the planner for the mission

        Phase: **planning** · Evidence class: `verified_flow`

        ```json
        {
          "request": {
            "id": "44444444-5555-4666-8777-888888888888",
            "priority": 0,
            "agents": [
              {
                "agent_id": "f9992bb3-9871-451f-90a0-9207eb9fe6c5",
                "agent_profile": "<JSON vehicle profile>",
                "odometry": {
                  "pose": {
                    "pose": {
                      "position": {
                        "x": 4.392588,
                        "y": 50.844317,
                        "z": 0.0
                      }
                    }
                  }
                }
              }
            ],
            "config": "<legacy mission_config JSON string>"
          },
          "response": {
            "id": "44444444-5555-4666-8777-888888888888",
            "state": 0
          }
        }
        ```

        - The verified run then published planner states 0, 1, and 2 asynchronously.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:475`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L475)

        #### Definition evidence

        - [`backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/srv/CreatePlanner.srv:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/srv/CreatePlanner.srv#L1)

    ??? abstract "centralized_msgs/srv/DeletePlanner · ros_type"
        SRV definition from `centralized_msgs`

        [Open standalone page](ros-types/centralized-msgs-srv-deleteplanner.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/srv/DeletePlanner.srv` |
        | Package | `centralized_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | request | `string` | `id` |
        | response | `string` | `id` |
        | response | `uint8` | `state` |

        #### Definition evidence

        - [`backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/srv/DeletePlanner.srv:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/srv/DeletePlanner.srv#L1)

    ??? abstract "centralized_msgs/srv/GetAgents · ros_type"
        SRV definition from `centralized_msgs`

        [Open standalone page](ros-types/centralized-msgs-srv-getagents.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/srv/GetAgents.srv` |
        | Package | `centralized_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | request | `unique_identifier_msgs/UUID[]` | `agent_id_list` |
        | response | `centralized_msgs/Agent[]` | `agents` |
        | response | `string<=2000` | `error_message` |

        #### Verified navigation data

        ##### Mission manager requests the configured Themis agent

        Phase: **planning** · Evidence class: `verified_flow`

        ```json
        {
          "request": {
            "agent_id_list": [
              {
                "uuid": [
                  249,
                  153,
                  43,
                  179,
                  152,
                  113,
                  69,
                  31,
                  144,
                  160,
                  146,
                  7,
                  235,
                  159,
                  230,
                  197
                ]
              }
            ]
          },
          "response": {
            "agents": [
              {
                "agent_id": "f9992bb3-9871-451f-90a0-9207eb9fe6c5",
                "agent_profile": "<JSON profile published by Edge>",
                "odometry": {
                  "pose": {
                    "pose": {
                      "position": {
                        "x": 4.392588,
                        "y": 50.844317,
                        "z": 0.0
                      }
                    }
                  }
                }
              }
            ],
            "error_message": "ok"
          }
        }
        ```

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:452`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L452)

        #### Definition evidence

        - [`backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/srv/GetAgents.srv:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/srv/GetAgents.srv#L1)

    ??? abstract "centralized_msgs/srv/GetPlan · ros_type"
        SRV definition from `centralized_msgs`

        [Open standalone page](ros-types/centralized-msgs-srv-getplan.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/srv/GetPlan.srv` |
        | Package | `centralized_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | request | `string` | `id` |
        | response | `string` | `id` |
        | response | `string` | `plan` |

        #### Verified navigation data

        ##### Retrieve the generated robot task

        Phase: **plan retrieval** · Evidence class: `observed_excerpt`

        ```json
        {
          "request": {
            "id": "44444444-5555-4666-8777-888888888888"
          },
          "response": {
            "id": "44444444-5555-4666-8777-888888888888",
            "plan": "<JSON-encoded TaskPlan containing one Themis task and 10 waypoint objectives>"
          }
        }
        ```

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:641`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L641)

        #### Definition evidence

        - [`backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/srv/GetPlan.srv:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/srv/GetPlan.srv#L1)

    ??? abstract "centralized_msgs/srv/UpdatePlannerAgents · ros_type"
        SRV definition from `centralized_msgs`

        [Open standalone page](ros-types/centralized-msgs-srv-updateplanneragents.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/srv/UpdatePlannerAgents.srv` |
        | Package | `centralized_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | request | `string` | `id` |
        | request | `Agent[]` | `agents` |
        | response | `string` | `id` |

        #### Definition evidence

        - [`backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/srv/UpdatePlannerAgents.srv:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/srv/UpdatePlannerAgents.srv#L1)

    ??? abstract "centralized_msgs/srv/UpdatePlannerPriority · ros_type"
        SRV definition from `centralized_msgs`

        [Open standalone page](ros-types/centralized-msgs-srv-updateplannerpriority.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/srv/UpdatePlannerPriority.srv` |
        | Package | `centralized_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | request | `string` | `id` |
        | request | `uint8` | `priority` |
        | response | `string` | `id` |

        #### Definition evidence

        - [`backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/srv/UpdatePlannerPriority.srv:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/srv/UpdatePlannerPriority.srv#L1)

    ## environment_msgs · MSG

    6 extracted contracts.

    ??? abstract "environment_msgs/msg/EnvironmentDataGetVersionRequest · ros_type"
        MSG definition from `environment_msgs`

        [Open standalone page](ros-types/environment-msgs-msg-environmentdatagetversionrequest.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/centralized-coordination/src/message_packages/environment_msgs/msg/EnvironmentDataGetVersionRequest.msg` |
        | Package | `environment_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `request_id` |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/message_packages/environment_msgs/msg/EnvironmentDataGetVersionRequest.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/environment_msgs/msg/EnvironmentDataGetVersionRequest.msg#L1)

    ??? abstract "environment_msgs/msg/EnvironmentDataGetVersionResponse · ros_type"
        MSG definition from `environment_msgs`

        [Open standalone page](ros-types/environment-msgs-msg-environmentdatagetversionresponse.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/centralized-coordination/src/message_packages/environment_msgs/msg/EnvironmentDataGetVersionResponse.msg` |
        | Package | `environment_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `request_id` |
        | message | `uint32` | `version_nr` |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/message_packages/environment_msgs/msg/EnvironmentDataGetVersionResponse.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/environment_msgs/msg/EnvironmentDataGetVersionResponse.msg#L1)

    ??? abstract "environment_msgs/msg/EnvironmentDataResetRequest · ros_type"
        MSG definition from `environment_msgs`

        [Open standalone page](ros-types/environment-msgs-msg-environmentdataresetrequest.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/centralized-coordination/src/message_packages/environment_msgs/msg/EnvironmentDataResetRequest.msg` |
        | Package | `environment_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `request_id` |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/message_packages/environment_msgs/msg/EnvironmentDataResetRequest.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/environment_msgs/msg/EnvironmentDataResetRequest.msg#L1)

    ??? abstract "environment_msgs/msg/EnvironmentDataResetResponse · ros_type"
        MSG definition from `environment_msgs`

        [Open standalone page](ros-types/environment-msgs-msg-environmentdataresetresponse.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/centralized-coordination/src/message_packages/environment_msgs/msg/EnvironmentDataResetResponse.msg` |
        | Package | `environment_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `request_id` |
        | message | `uint8` | `result_status` |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/message_packages/environment_msgs/msg/EnvironmentDataResetResponse.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/environment_msgs/msg/EnvironmentDataResetResponse.msg#L1)

    ??? abstract "environment_msgs/msg/EnvironmentDataUploadRequest · ros_type"
        MSG definition from `environment_msgs`

        [Open standalone page](ros-types/environment-msgs-msg-environmentdatauploadrequest.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/centralized-coordination/src/message_packages/environment_msgs/msg/EnvironmentDataUploadRequest.msg` |
        | Package | `environment_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `request_id` |
        | message | `uint32` | `version_nr` |
        | message | `string<=10000` | `insert_geojson` |
        | message | `string<=10000` | `update_geojson` |
        | message | `string<=5000` | `delete_json` |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/message_packages/environment_msgs/msg/EnvironmentDataUploadRequest.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/environment_msgs/msg/EnvironmentDataUploadRequest.msg#L1)

    ??? abstract "environment_msgs/msg/EnvironmentDataUploadResponse · ros_type"
        MSG definition from `environment_msgs`

        [Open standalone page](ros-types/environment-msgs-msg-environmentdatauploadresponse.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/centralized-coordination/src/message_packages/environment_msgs/msg/EnvironmentDataUploadResponse.msg` |
        | Package | `environment_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `unique_identifier_msgs/UUID` | `request_id` |
        | message | `uint8` | `result_status` |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/message_packages/environment_msgs/msg/EnvironmentDataUploadResponse.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/environment_msgs/msg/EnvironmentDataUploadResponse.msg#L1)

    ## environment_msgs · SRV

    3 extracted contracts.

    ??? abstract "environment_msgs/srv/EnvironmentDataGetVersion · ros_type"
        SRV definition from `environment_msgs`

        [Open standalone page](ros-types/environment-msgs-srv-environmentdatagetversion.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/centralized-coordination/src/message_packages/environment_msgs/srv/EnvironmentDataGetVersion.srv` |
        | Package | `environment_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | request | `unique_identifier_msgs/UUID` | `request_id` |
        | response | `unique_identifier_msgs/UUID` | `request_id` |
        | response | `uint32` | `version_nr` |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/message_packages/environment_msgs/srv/EnvironmentDataGetVersion.srv:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/environment_msgs/srv/EnvironmentDataGetVersion.srv#L1)

    ??? abstract "environment_msgs/srv/EnvironmentDataReset · ros_type"
        SRV definition from `environment_msgs`

        [Open standalone page](ros-types/environment-msgs-srv-environmentdatareset.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/centralized-coordination/src/message_packages/environment_msgs/srv/EnvironmentDataReset.srv` |
        | Package | `environment_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | request | `unique_identifier_msgs/UUID` | `request_id` |
        | response | `unique_identifier_msgs/UUID` | `request_id` |
        | response | `uint8` | `result_status` |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/message_packages/environment_msgs/srv/EnvironmentDataReset.srv:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/environment_msgs/srv/EnvironmentDataReset.srv#L1)

    ??? abstract "environment_msgs/srv/EnvironmentDataUpload · ros_type"
        SRV definition from `environment_msgs`

        [Open standalone page](ros-types/environment-msgs-srv-environmentdataupload.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/centralized-coordination/src/message_packages/environment_msgs/srv/EnvironmentDataUpload.srv` |
        | Package | `environment_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | request | `unique_identifier_msgs/UUID` | `request_id` |
        | request | `uint32` | `version_nr` |
        | request | `string<=10000` | `insert_geojson` |
        | request | `string<=10000` | `update_geojson` |
        | request | `string<=5000` | `delete_json` |
        | response | `unique_identifier_msgs/UUID` | `request_id` |
        | response | `uint8` | `result_status` |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/message_packages/environment_msgs/srv/EnvironmentDataUpload.srv:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/environment_msgs/srv/EnvironmentDataUpload.srv#L1)

    ## task_msgs · MSG

    2 extracted contracts.

    ??? abstract "task_msgs/msg/Feedback · ros_type"
        MSG definition from `task_msgs`

        [Open standalone page](ros-types/task-msgs-msg-feedback.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/centralized-coordination/src/message_packages/task_msgs/msg/Feedback.msg` |
        | Package | `task_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `string` | `agent_id` |
        | message | `uint8` | `state` |
        | message | `TaskFeedback[]` | `tasks` |
        | message | `nav_msgs/Odometry` | `odometry` |

        #### Verified navigation data

        ##### Themis reports completion after the final waypoint

        Phase: **COMPLETED** · Evidence class: `verified_flow`

        ```json
        {
          "agent_id": "f9992bb3-9871-451f-90a0-9207eb9fe6c5",
          "state": 1,
          "tasks": [
            {
              "task_id": "<generated-task-uuid>",
              "task_state": 3,
              "current_objective_id": "<final-generated-objective-uuid>"
            }
          ],
          "odometry": {
            "pose": {
              "pose": {
                "position": {
                  "x": 4.391670213379427,
                  "y": 50.84417059346137,
                  "z": 0.0
                }
              }
            }
          }
        }
        ```

        - Task state 3 is COMPLETED. The mission manager then transitions the one-robot mission to COMPLETED(10).

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:918`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L918)

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/message_packages/task_msgs/msg/Feedback.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/task_msgs/msg/Feedback.msg#L1)

    ??? abstract "task_msgs/msg/TaskFeedback · ros_type"
        MSG definition from `task_msgs`

        [Open standalone page](ros-types/task-msgs-msg-taskfeedback.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/centralized-coordination/src/message_packages/task_msgs/msg/TaskFeedback.msg` |
        | Package | `task_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | message | `string` | `task_id` |
        | message | `uint8` | `task_state` |
        | message | `string` | `current_objective_id` |

        #### Verified navigation data

        ##### Themis reports completion after the final waypoint

        Phase: **COMPLETED** · Evidence class: `verified_flow`

        ```json
        {
          "agent_id": "f9992bb3-9871-451f-90a0-9207eb9fe6c5",
          "state": 1,
          "tasks": [
            {
              "task_id": "<generated-task-uuid>",
              "task_state": 3,
              "current_objective_id": "<final-generated-objective-uuid>"
            }
          ],
          "odometry": {
            "pose": {
              "pose": {
                "position": {
                  "x": 4.391670213379427,
                  "y": 50.84417059346137,
                  "z": 0.0
                }
              }
            }
          }
        }
        ```

        - Task state 3 is COMPLETED. The mission manager then transitions the one-robot mission to COMPLETED(10).

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:918`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L918)

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/message_packages/task_msgs/msg/TaskFeedback.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/task_msgs/msg/TaskFeedback.msg#L1)

    ## task_msgs · SRV

    3 extracted contracts.

    ??? abstract "task_msgs/srv/AddTask · ros_type"
        SRV definition from `task_msgs`

        [Open standalone page](ros-types/task-msgs-srv-addtask.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/centralized-coordination/src/message_packages/task_msgs/srv/AddTask.srv` |
        | Package | `task_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | request | `string` | `task_id` |
        | request | `uint8` | `task_type` |
        | request | `bool` | `override` |
        | request | `string<=1048576` | `task_config` |
        | request | `string` | `std` |
        | response | `string` | `task_id` |
        | response | `uint8` | `task_state` |

        #### Verified navigation data

        ##### Fleet installs the stopped waypoint task on Themis

        Phase: **APPROVE** · Evidence class: `observed_excerpt`

        ```json
        {
          "request": {
            "task_id": "<generated-task-uuid>",
            "task_type": 0,
            "override": true,
            "task_config": "{\"primitives\":[{\"primitive_id\":\"<generated-primitive-uuid>\",\"primitive_type\":\"waypoint\"}],\"objectives\":[{\"objective_id\":\"<first-generated-objective-uuid>\",\"primitives\":[{\"primitive_id\":\"<generated-primitive-uuid>\",\"parameters\":{\"coordinates\":[4.3925979,50.8443434],\"speed\":1.3,\"max_speed\":1.3}}]}]}",
            "std": ""
          },
          "response": {
            "task_id": "<generated-task-uuid>",
            "task_state": 0
          }
        }
        ```

        - task_config is an abridged JSON string; the real task contained 10 waypoint objectives.
        - Task state 0 is STOPPED: APPROVE installs the task but does not move the robot.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:750`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L750)

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/message_packages/task_msgs/srv/AddTask.srv:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/task_msgs/srv/AddTask.srv#L1)

    ??? abstract "task_msgs/srv/ChangeState · ros_type"
        SRV definition from `task_msgs`

        [Open standalone page](ros-types/task-msgs-srv-changestate.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/centralized-coordination/src/message_packages/task_msgs/srv/ChangeState.srv` |
        | Package | `task_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | request | `uint8` | `requested_state` |
        | response | `uint8` | `state` |
        | response | `string<=1024` | `feedback` |

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/message_packages/task_msgs/srv/ChangeState.srv:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/task_msgs/srv/ChangeState.srv#L1)

    ??? abstract "task_msgs/srv/ChangeTaskState · ros_type"
        SRV definition from `task_msgs`

        [Open standalone page](ros-types/task-msgs-srv-changetaskstate.md)

        | Property | Extracted value |
        |---|---|
        | Kind | `ros_type` |
        | Path | `backend/fog/centralized-coordination/src/message_packages/task_msgs/srv/ChangeTaskState.srv` |
        | Package | `task_msgs` |

        #### Fields

        | Section | Type | Name |
        |---|---|---|
        | request | `string` | `task_id` |
        | request | `uint8` | `task_requested_state` |
        | response | `string` | `task_id` |
        | response | `uint8` | `task_state` |
        | response | `string<=1024` | `feedback` |

        #### Verified navigation data

        ##### Fleet starts the installed Themis task

        Phase: **START** · Evidence class: `verified_flow`

        ```json
        {
          "request": {
            "task_id": "<generated-task-uuid>",
            "task_requested_state": 1
          },
          "response": {
            "task_id": "<generated-task-uuid>",
            "task_state": 1,
            "feedback": ""
          }
        }
        ```

        - task_requested_state 1 is EXECUTE; task_state 1 is STARTED.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:818`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L818)

        #### Definition evidence

        - [`backend/fog/centralized-coordination/src/message_packages/task_msgs/srv/ChangeTaskState.srv:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/task_msgs/srv/ChangeTaskState.srv#L1)


=== "States (2)"

    ## Source-parsed state machines

    Transitions are parsed from explicit source patterns. The verified path is shown separately inside each state machine.

    ??? abstract "Mission lifecycle · 11 states · 51 transitions"
        Allowed mission status transitions enforced by MissionManager.

        ```mermaid
        stateDiagram-v2
          state "NONE (0)" as N_NONE
          state "PLANNED (1)" as N_PLANNED
          state "PLANNED_ALTERNATIVE (2)" as N_PLANNED_ALTERNATIVE
          state "PLANNED_FAILED (3)" as N_PLANNED_FAILED
          state "ACCEPTED (4)" as N_ACCEPTED
          state "STARTED (5)" as N_STARTED
          state "PAUSED (6)" as N_PAUSED
          state "FAILED (7)" as N_FAILED
          state "STOPPED (8)" as N_STOPPED
          state "DELETED (9)" as N_DELETED
          state "COMPLETED (10)" as N_COMPLETED
          N_NONE --> N_PLANNED: allowed status change
          N_NONE --> N_STOPPED: allowed status change
          N_NONE --> N_FAILED: allowed status change
          N_NONE --> N_DELETED: allowed status change
          N_PLANNED --> N_NONE: allowed status change
          N_PLANNED --> N_PLANNED_ALTERNATIVE: allowed status change
          N_PLANNED --> N_ACCEPTED: allowed status change
          N_PLANNED --> N_STOPPED: allowed status change
          N_PLANNED --> N_FAILED: allowed status change
          N_PLANNED --> N_DELETED: allowed status change
          N_PLANNED_ALTERNATIVE --> N_NONE: allowed status change
          N_PLANNED_ALTERNATIVE --> N_ACCEPTED: allowed status change
          N_PLANNED_ALTERNATIVE --> N_STOPPED: allowed status change
          N_PLANNED_ALTERNATIVE --> N_FAILED: allowed status change
          N_PLANNED_ALTERNATIVE --> N_DELETED: allowed status change
          N_PLANNED_FAILED --> N_STOPPED: allowed status change
          N_PLANNED_FAILED --> N_FAILED: allowed status change
          N_ACCEPTED --> N_NONE: allowed status change
          N_ACCEPTED --> N_PLANNED_ALTERNATIVE: allowed status change
          N_ACCEPTED --> N_STARTED: allowed status change
          N_ACCEPTED --> N_STOPPED: allowed status change
          N_ACCEPTED --> N_FAILED: allowed status change
          N_ACCEPTED --> N_DELETED: allowed status change
          N_STARTED --> N_NONE: allowed status change
          N_STARTED --> N_PLANNED_ALTERNATIVE: allowed status change
          N_STARTED --> N_PAUSED: allowed status change
          N_STARTED --> N_FAILED: allowed status change
          N_STARTED --> N_STOPPED: allowed status change
          N_STARTED --> N_COMPLETED: allowed status change
          N_STARTED --> N_DELETED: allowed status change
          N_PAUSED --> N_NONE: allowed status change
          N_PAUSED --> N_PLANNED_ALTERNATIVE: allowed status change
          N_PAUSED --> N_STARTED: allowed status change
          N_PAUSED --> N_FAILED: allowed status change
          N_PAUSED --> N_STOPPED: allowed status change
          N_PAUSED --> N_COMPLETED: allowed status change
          N_PAUSED --> N_DELETED: allowed status change
          N_FAILED --> N_NONE: allowed status change
          N_FAILED --> N_STOPPED: allowed status change
          N_FAILED --> N_COMPLETED: allowed status change
          N_FAILED --> N_DELETED: allowed status change
          N_STOPPED --> N_NONE: allowed status change
          N_STOPPED --> N_STARTED: allowed status change
          N_STOPPED --> N_FAILED: allowed status change
          N_STOPPED --> N_DELETED: allowed status change
          N_DELETED --> N_NONE: allowed status change
          N_COMPLETED --> N_NONE: allowed status change
          N_COMPLETED --> N_STOPPED: allowed status change
          N_COMPLETED --> N_DELETED: allowed status change
        ```

        #### State values

        | Value | State | Description |
        |---:|---|---|
        | `0` | `NONE` | NOT USED |
        | `1` | `PLANNED` | Mission is correctly planned |
        | `2` | `PLANNED_ALTERNATIVE` | Mission has alternative planned |
        | `3` | `PLANNED_FAILED` | Mission planning failed |
        | `4` | `ACCEPTED` | Mission is accepted |
        | `5` | `STARTED` | Mission is started |
        | `6` | `PAUSED` | Mission is paused |
        | `7` | `FAILED` | Mission has failed |
        | `8` | `STOPPED` | Mission is finished by request.  itwill not stop a mission, except if FAILED or another mission is started. |
        | `9` | `DELETED` | Missio is deleted from the system. |
        | `10` | `COMPLETED` |  |

        #### Extracted transitions

        | From | Trigger | To | Evidence |
        |---|---|---|---|
        | `NONE` | allowed status change | `NONE` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:716`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L716) |
        | `NONE` | allowed status change | `PLANNED` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:716`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L716) |
        | `NONE` | allowed status change | `STOPPED` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:716`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L716) |
        | `NONE` | allowed status change | `FAILED` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:716`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L716) |
        | `NONE` | allowed status change | `DELETED` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:716`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L716) |
        | `PLANNED` | allowed status change | `NONE` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:718`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L718) |
        | `PLANNED` | allowed status change | `PLANNED_ALTERNATIVE` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:718`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L718) |
        | `PLANNED` | allowed status change | `ACCEPTED` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:718`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L718) |
        | `PLANNED` | allowed status change | `STOPPED` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:718`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L718) |
        | `PLANNED` | allowed status change | `FAILED` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:718`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L718) |
        | `PLANNED` | allowed status change | `DELETED` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:718`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L718) |
        | `PLANNED_ALTERNATIVE` | allowed status change | `NONE` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:720`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L720) |
        | `PLANNED_ALTERNATIVE` | allowed status change | `ACCEPTED` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:720`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L720) |
        | `PLANNED_ALTERNATIVE` | allowed status change | `STOPPED` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:720`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L720) |
        | `PLANNED_ALTERNATIVE` | allowed status change | `FAILED` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:720`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L720) |
        | `PLANNED_ALTERNATIVE` | allowed status change | `DELETED` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:720`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L720) |
        | `PLANNED_FAILED` | allowed status change | `STOPPED` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:722`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L722) |
        | `PLANNED_FAILED` | allowed status change | `FAILED` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:722`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L722) |
        | `ACCEPTED` | allowed status change | `NONE` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:724`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L724) |
        | `ACCEPTED` | allowed status change | `PLANNED_ALTERNATIVE` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:724`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L724) |
        | `ACCEPTED` | allowed status change | `ACCEPTED` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:724`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L724) |
        | `ACCEPTED` | allowed status change | `STARTED` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:724`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L724) |
        | `ACCEPTED` | allowed status change | `STOPPED` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:724`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L724) |
        | `ACCEPTED` | allowed status change | `FAILED` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:724`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L724) |
        | `ACCEPTED` | allowed status change | `DELETED` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:724`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L724) |
        | `STARTED` | allowed status change | `NONE` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:726`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L726) |
        | `STARTED` | allowed status change | `PLANNED_ALTERNATIVE` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:726`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L726) |
        | `STARTED` | allowed status change | `PAUSED` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:726`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L726) |
        | `STARTED` | allowed status change | `FAILED` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:726`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L726) |
        | `STARTED` | allowed status change | `STOPPED` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:726`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L726) |
        | `STARTED` | allowed status change | `COMPLETED` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:726`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L726) |
        | `STARTED` | allowed status change | `DELETED` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:726`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L726) |
        | `PAUSED` | allowed status change | `NONE` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:728`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L728) |
        | `PAUSED` | allowed status change | `PLANNED_ALTERNATIVE` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:728`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L728) |
        | `PAUSED` | allowed status change | `STARTED` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:728`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L728) |
        | `PAUSED` | allowed status change | `FAILED` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:728`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L728) |
        | `PAUSED` | allowed status change | `STOPPED` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:728`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L728) |
        | `PAUSED` | allowed status change | `COMPLETED` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:728`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L728) |
        | `PAUSED` | allowed status change | `DELETED` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:728`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L728) |
        | `FAILED` | allowed status change | `NONE` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:730`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L730) |
        | `FAILED` | allowed status change | `STOPPED` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:730`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L730) |
        | `FAILED` | allowed status change | `COMPLETED` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:730`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L730) |
        | `FAILED` | allowed status change | `DELETED` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:730`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L730) |
        | `STOPPED` | allowed status change | `NONE` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:732`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L732) |
        | `STOPPED` | allowed status change | `STARTED` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:732`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L732) |
        | `STOPPED` | allowed status change | `FAILED` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:732`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L732) |
        | `STOPPED` | allowed status change | `DELETED` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:732`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L732) |
        | `DELETED` | allowed status change | `NONE` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:734`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L734) |
        | `COMPLETED` | allowed status change | `NONE` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:736`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L736) |
        | `COMPLETED` | allowed status change | `STOPPED` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:736`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L736) |
        | `COMPLETED` | allowed status change | `DELETED` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:736`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L736) |

        #### Request mapping

        | Request | Resulting state | Evidence |
        |---|---|---|
        | `INIT` | `NONE` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:930`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L930) |
        | `APPROVE` | `ACCEPTED` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:933`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L933) |
        | `START` | `STARTED` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:936`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L936) |
        | `PAUSE` | `PAUSED` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:939`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L939) |
        | `STOP` | `STOPPED` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:942`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L942) |
        | `DELETE` | `DELETED` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:945`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L945) |

        #### Verified navigation path

        ```mermaid
        flowchart LR
          V0["NONE (0)"]
          V1["PLANNED (1)"]
          V0 -->|10-waypoint plan received| V1
          V2["ACCEPTED (4)"]
          V1 -->|APPROVE| V2
          V3["STARTED (5)"]
          V2 -->|START| V3
          V4["COMPLETED (10)"]
          V3 -->|Themis completed the task| V4
        ```

        | Order | State | Value | Runtime event |
        |---:|---|---:|---|
        | 1 | `NONE` | `0` | INIT accepted |
        | 2 | `PLANNED` | `1` | 10-waypoint plan received |
        | 3 | `ACCEPTED` | `4` | APPROVE |
        | 4 | `STARTED` | `5` | START |
        | 5 | `COMPLETED` | `10` | Themis completed the task |

    ??? abstract "Edge task lifecycle · 6 states · 4 transitions"
        The edge service copies TaskRequestState's numeric value directly into TaskState.

        ```mermaid
        stateDiagram-v2
          state "Any current state" as N_ANY
          state "STOPPED (0)" as N_STOPPED
          state "STARTED (1)" as N_STARTED
          state "PAUSED (2)" as N_PAUSED
          state "COMPLETED (3)" as N_COMPLETED
          state "ABORTED (4)" as N_ABORTED
          state "DELETED (5)" as N_DELETED
          N_ANY --> N_STOPPED: STOP
          N_ANY --> N_STARTED: EXECUTE
          N_ANY --> N_PAUSED: PAUSE
          N_ANY --> N_COMPLETED: DELETE
        ```

        #### State values

        | Value | State | Description |
        |---:|---|---|
        | `0` | `STOPPED` | stopped, but not completed or started |
        | `1` | `STARTED` | started |
        | `2` | `PAUSED` | paused |
        | `3` | `COMPLETED` | completed the task |
        | `4` | `ABORTED` | aborted |
        | `5` | `DELETED` | deleted |

        #### Extracted transitions

        | From | Trigger | To | Evidence |
        |---|---|---|---|
        | `ANY` | STOP | `STOPPED` | [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:987`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L987) |
        | `ANY` | EXECUTE | `STARTED` | [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:987`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L987) |
        | `ANY` | PAUSE | `PAUSED` | [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:987`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L987) |
        | `ANY` | DELETE | `COMPLETED` | [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:987`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L987) |

        #### Request mapping

        | Request | Resulting state | Evidence |
        |---|---|---|
        | `STOP` | `STOPPED` | [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:987`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L987) |
        | `EXECUTE` | `STARTED` | [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:987`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L987) |
        | `PAUSE` | `PAUSED` | [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:987`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L987) |
        | `DELETE` | `COMPLETED` | [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:987`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L987) |

        #### Verified navigation path

        ```mermaid
        flowchart LR
          V0["STOPPED (0)"]
          V1["STARTED (1)"]
          V0 -->|EXECUTE during START| V1
          V2["COMPLETED (3)"]
          V1 -->|final waypoint reached| V2
        ```

        | Order | State | Value | Runtime event |
        |---:|---|---:|---|
        | 1 | `STOPPED` | `0` | AddTask during APPROVE |
        | 2 | `STARTED` | `1` | EXECUTE during START |
        | 3 | `COMPLETED` | `3` | final waypoint reached |


=== "Enums (20)"

    ## Source enum registry

    Same-name declarations are compared by their member/value signatures.

    ??? abstract "Behavior · consistent · 4 definitions"
        #### c2_msgs.Behavior

        Language: **C++** · Evidence: [`backend/fog/centralized-coordination/src/message_packages/c2_msgs/json/Enums.hpp:53`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/c2_msgs/json/Enums.hpp#L53)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `NAVIGATE` | Navigation/driving based behavior. Used for mission types: Good transportation, CASEVAC, Comm relay, Screen mission, Ballistic protection |
        | `1` | `COVERAGE` | Monitoring/patrolling the objective. Used for mission types: Reconnaissance mission, Patrolling mission |
        | `2` | `NAVIGATE_NO_PLANNING` | Navigation/driving based behavior, but without using the planner: Used to test the navigation (local space) |

        #### centralized_msgs.Behavior

        Language: **C++** · Evidence: [`backend/fog/centralized-coordination/src/message_packages/centralized_msgs/json/Enums.hpp:62`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/centralized_msgs/json/Enums.hpp#L62)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `NAVIGATE` | Navigation/driving based behavior. Used for mission types: Good transportation, CASEVAC, Comm relay, Screen mission, Ballistic protection |
        | `1` | `COVERAGE` | Monitoring/patrolling the objective. Used for mission types: Reconnaissance mission, Patrolling mission |
        | `2` | `NAVIGATE_NO_PLANNING` | Navigation/driving based behavior, but without using the planner: Used to test the navigation (local space) |

        #### centralized_msgs.Behavior

        Language: **C++** · Evidence: [`backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/json/Enums.hpp:62`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/json/Enums.hpp#L62)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `NAVIGATE` | Navigation/driving based behavior. Used for mission types: Good transportation, CASEVAC, Comm relay, Screen mission, Ballistic protection |
        | `1` | `COVERAGE` | Monitoring/patrolling the objective. Used for mission types: Reconnaissance mission, Patrolling mission |
        | `2` | `NAVIGATE_NO_PLANNING` | Navigation/driving based behavior, but without using the planner: Used to test the navigation (local space) |

        #### c2_imugs2.core.models.Behavior

        Language: **Python** · Evidence: [`src/c2_imugs2/core/models.py:10`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/core/models.py#L10)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `NAVIGATE` |  |
        | `1` | `COVERAGE` |  |
        | `2` | `NAVIGATE_NO_PLANNING` |  |

        #### Values used by the verified navigation run

        | Value | Member | Where it appeared |
        |---:|---|---|
        | `0` | `NAVIGATE` | mission configuration |

    ??? abstract "EnvironmentDataResultStatus · consistent · 3 definitions"
        #### c2_msgs.EnvironmentDataResultStatus

        Language: **C++** · Evidence: [`backend/fog/centralized-coordination/src/message_packages/c2_msgs/json/Enums.hpp:85`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/c2_msgs/json/Enums.hpp#L85)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `SUCCESS` |  |
        | `1` | `ERROR` |  |

        #### centralized_msgs.EnvironmentDataResultStatus

        Language: **C++** · Evidence: [`backend/fog/centralized-coordination/src/message_packages/centralized_msgs/json/Enums.hpp:94`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/centralized_msgs/json/Enums.hpp#L94)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `SUCCESS` |  |
        | `1` | `ERROR` |  |

        #### centralized_msgs.EnvironmentDataResultStatus

        Language: **C++** · Evidence: [`backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/json/Enums.hpp:94`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/json/Enums.hpp#L94)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `SUCCESS` |  |
        | `1` | `ERROR` |  |


    ??? abstract "EnvironmentDataUploadResultStatus · consistent · 3 definitions"
        #### c2_msgs.EnvironmentDataUploadResultStatus

        Language: **C++** · Evidence: [`backend/fog/centralized-coordination/src/message_packages/c2_msgs/json/Enums.hpp:91`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/c2_msgs/json/Enums.hpp#L91)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `SUCCESS` |  |
        | `1` | `INVALID_VERSION` |  |
        | `2` | `ALREADY_EXECUTING_ANOTHER_UPLOAD` |  |
        | `3` | `ERROR_WHILE_UPDATING_DATABASE` |  |

        #### centralized_msgs.EnvironmentDataUploadResultStatus

        Language: **C++** · Evidence: [`backend/fog/centralized-coordination/src/message_packages/centralized_msgs/json/Enums.hpp:100`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/centralized_msgs/json/Enums.hpp#L100)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `SUCCESS` |  |
        | `1` | `INVALID_VERSION` |  |
        | `2` | `ALREADY_EXECUTING_ANOTHER_UPLOAD` |  |
        | `3` | `ERROR_WHILE_UPDATING_DATABASE` |  |

        #### centralized_msgs.EnvironmentDataUploadResultStatus

        Language: **C++** · Evidence: [`backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/json/Enums.hpp:100`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/json/Enums.hpp#L100)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `SUCCESS` |  |
        | `1` | `INVALID_VERSION` |  |
        | `2` | `ALREADY_EXECUTING_ANOTHER_UPLOAD` |  |
        | `3` | `ERROR_WHILE_UPDATING_DATABASE` |  |


    ??? abstract "Freshness · consistent · 1 definitions"
        #### c2_imugs2.operations.models.Freshness

        Language: **Python** · Evidence: [`src/c2_imugs2/operations/models.py:32`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/operations/models.py#L32)

        | Value | Member | Source comment |
        |---:|---|---|
        | `fresh` | `FRESH` |  |
        | `stale` | `STALE` |  |
        | `missing` | `MISSING` |  |
        | `inferred` | `INFERRED` |  |
        | `unknown` | `UNKNOWN` |  |


    ??? abstract "FullSnapshotReason · consistent · 1 definitions"
        #### c2_imugs2.operations.service.FullSnapshotReason

        Language: **Python** · Evidence: [`src/c2_imugs2/operations/service.py:41`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/operations/service.py#L41)

        | Value | Member | Source comment |
        |---:|---|---|
        | `initial` | `INITIAL` |  |
        | `base_revision_unavailable` | `BASE_REVISION_UNAVAILABLE` |  |
        | `runtime_mismatch` | `RUNTIME_MISMATCH` |  |
        | `checksum_mismatch` | `CHECKSUM_MISMATCH` |  |
        | `schema_version_mismatch` | `SCHEMA_VERSION_MISMATCH` |  |


    ??? abstract "LogType · consistent · 3 definitions"
        #### c2_msgs.LogType

        Language: **C++** · Evidence: [`backend/fog/centralized-coordination/src/message_packages/c2_msgs/json/Enums.hpp:77`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/c2_msgs/json/Enums.hpp#L77)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `INFO` |  |
        | `1` | `WARNING` |  |
        | `2` | `ERROR` |  |
        | `3` | `FATAL` |  |

        #### centralized_msgs.LogType

        Language: **C++** · Evidence: [`backend/fog/centralized-coordination/src/message_packages/centralized_msgs/json/Enums.hpp:86`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/centralized_msgs/json/Enums.hpp#L86)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `INFO` |  |
        | `1` | `WARNING` |  |
        | `2` | `ERROR` |  |
        | `3` | `FATAL` |  |

        #### centralized_msgs.LogType

        Language: **C++** · Evidence: [`backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/json/Enums.hpp:86`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/json/Enums.hpp#L86)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `INFO` |  |
        | `1` | `WARNING` |  |
        | `2` | `ERROR` |  |
        | `3` | `FATAL` |  |


    ??? abstract "MissionIssue · consistent · 4 definitions"
        #### c2_msgs.MissionIssue

        Language: **C++** · Evidence: [`backend/fog/centralized-coordination/src/message_packages/c2_msgs/json/Enums.hpp:5`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/c2_msgs/json/Enums.hpp#L5)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `NONE` | No issue |
        | `10` | `MISSION_WARN_ID_ALREADY_USED` | Mission ID is already in use. The corresponding mission configuration will be overwritten. Mission state will be set to INIT. |
        | `11` | `MISSION_WARN_UGV_UNAVAILABLE` | At least one UGV is unavailable. Reduced set of UGVs will be used. Mission state will be set to PLANNED_ALTERNATIVE |
        | `12` | `MISSION_WARN_CONFIG_UNKNOWN_DATA` | The provided mission_config file contains unknown keys. The latter data will simply be ignored. |
        | `13` | `MISSION_WARN_STATUS_NOT_CHANGED` | The requested mission status change was not valid. The transition will be ignored. |
        | `14` | `MISSION_WARN_DISCONNECTED_SWARM_PLANNER` | Could not communicate with swarm planner. Mission state will not change |
        | `15` | `MISSION_WARN_DISCONNECTED_SWARMING_EDGE` | Could not communicate with at least one  edge module. Mission state will not change |
        | `16` | `MISSION_WARN_DISCONNECTED_AUTONOMY` | Could not communicate with at least one autonomy module. Mission state will not change |
        | `20` | `MISSION_FAILED_CONFIG_PARSING_UNSUCCESSFUL` | The provided mission_config file could not be parsed. Mission state will be set to FAILED. |
        | `21` | `MISSION_FAILED_CONFIG_MISSING_DATA` | The provided mission_config file does not contain sufficient data for plannification. Mission state will be set to FAILED. |
        | `22` | `MISSION_FAILED_MISSION_COMPROMISED` | The mission is compromised and is unable to continue. Mission state will be set to FAILED. |
        | `23` | `MISSION_FAILED_DISCONNECTED_SWARM_PLANNER` | Could not communicate with swarm planner, results in process failure. Mission state will be set to FAILED. |
        | `24` | `MISSION_FAILED_DISCONNECTED_EDGE` | Could not communicate with  edge modules, results in process failure. Mission state will be set to FAILED. |
        | `25` | `MISSION_FAILED_DISCONNECTED_AUTONOMY` | Could not communicate with at least one autonomy module, timeout results in mission failure. Mission state will be set to FAILED |
        | `30` | `PLANNING_WARN_VEHICLES_MISMATCH` | Not enough vehicles for the given mission configuration. Mission state will be set to PLANNED_ALTERNATIVE |
        | `31` | `PLANNING_WARN_NOT_ENOUGH_COVERAGE` | not enough coverage for the given mission configuration. Mission state will be set to PLANNED_ALTERNATIVE |
        | `32` | `PLANNING_WARN_DATE_COMPROMISED` | Requested start or end date is compromised in planning solution. Mission state will be set to PLANNED anyway |
        | `40` | `PLANNING_FAILED_NO_SOLUTION_FOUND` | No planning solution found. New init_mission needed with adjusted configuration. Mission state will be set to PLANNED_FAILED |
        | `41` | `PLANNING_FAILED` | Swarm planner process fail,  Mission state will be set to PLANNED_FAILED. |

        #### centralized_msgs.MissionIssue

        Language: **C++** · Evidence: [`backend/fog/centralized-coordination/src/message_packages/centralized_msgs/json/Enums.hpp:14`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/centralized_msgs/json/Enums.hpp#L14)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `NONE` | No issue |
        | `10` | `MISSION_WARN_ID_ALREADY_USED` | Mission ID is already in use. The corresponding mission configuration will be overwritten. Mission state will be set to INIT. |
        | `11` | `MISSION_WARN_UGV_UNAVAILABLE` | At least one UGV is unavailable. Reduced set of UGVs will be used. Mission state will be set to PLANNED_ALTERNATIVE |
        | `12` | `MISSION_WARN_CONFIG_UNKNOWN_DATA` | The provided mission_config file contains unknown keys. The latter data will simply be ignored. |
        | `13` | `MISSION_WARN_STATUS_NOT_CHANGED` | The requested mission status change was not valid. The transition will be ignored. |
        | `14` | `MISSION_WARN_DISCONNECTED_SWARM_PLANNER` | Could not communicate with swarm planner. Mission state will not change |
        | `15` | `MISSION_WARN_DISCONNECTED_SWARMING_EDGE` | Could not communicate with at least one  edge module. Mission state will not change |
        | `16` | `MISSION_WARN_DISCONNECTED_AUTONOMY` | Could not communicate with at least one autonomy module. Mission state will not change |
        | `20` | `MISSION_FAILED_CONFIG_PARSING_UNSUCCESSFUL` | The provided mission_config file could not be parsed. Mission state will be set to FAILED. |
        | `21` | `MISSION_FAILED_CONFIG_MISSING_DATA` | The provided mission_config file does not contain sufficient data for plannification. Mission state will be set to FAILED. |
        | `22` | `MISSION_FAILED_MISSION_COMPROMISED` | The mission is compromised and is unable to continue. Mission state will be set to FAILED. |
        | `23` | `MISSION_FAILED_DISCONNECTED_SWARM_PLANNER` | Could not communicate with swarm planner, results in process failure. Mission state will be set to FAILED. |
        | `24` | `MISSION_FAILED_DISCONNECTED_EDGE` | Could not communicate with  edge modules, results in process failure. Mission state will be set to FAILED. |
        | `25` | `MISSION_FAILED_DISCONNECTED_AUTONOMY` | Could not communicate with at least one autonomy module, timeout results in mission failure. Mission state will be set to FAILED |
        | `30` | `PLANNING_WARN_VEHICLES_MISMATCH` | Not enough vehicles for the given mission configuration. Mission state will be set to PLANNED_ALTERNATIVE |
        | `31` | `PLANNING_WARN_NOT_ENOUGH_COVERAGE` | not enough coverage for the given mission configuration. Mission state will be set to PLANNED_ALTERNATIVE |
        | `32` | `PLANNING_WARN_DATE_COMPROMISED` | Requested start or end date is compromised in planning solution. Mission state will be set to PLANNED anyway |
        | `40` | `PLANNING_FAILED_NO_SOLUTION_FOUND` | No planning solution found. New init_mission needed with adjusted configuration. Mission state will be set to PLANNED_FAILED |
        | `41` | `PLANNING_FAILED` | Swarm planner process fail,  Mission state will be set to PLANNED_FAILED. |

        #### centralized_msgs.MissionIssue

        Language: **C++** · Evidence: [`backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/json/Enums.hpp:14`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/json/Enums.hpp#L14)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `NONE` | No issue |
        | `10` | `MISSION_WARN_ID_ALREADY_USED` | Mission ID is already in use. The corresponding mission configuration will be overwritten. Mission state will be set to INIT. |
        | `11` | `MISSION_WARN_UGV_UNAVAILABLE` | At least one UGV is unavailable. Reduced set of UGVs will be used. Mission state will be set to PLANNED_ALTERNATIVE |
        | `12` | `MISSION_WARN_CONFIG_UNKNOWN_DATA` | The provided mission_config file contains unknown keys. The latter data will simply be ignored. |
        | `13` | `MISSION_WARN_STATUS_NOT_CHANGED` | The requested mission status change was not valid. The transition will be ignored. |
        | `14` | `MISSION_WARN_DISCONNECTED_SWARM_PLANNER` | Could not communicate with swarm planner. Mission state will not change |
        | `15` | `MISSION_WARN_DISCONNECTED_SWARMING_EDGE` | Could not communicate with at least one  edge module. Mission state will not change |
        | `16` | `MISSION_WARN_DISCONNECTED_AUTONOMY` | Could not communicate with at least one autonomy module. Mission state will not change |
        | `20` | `MISSION_FAILED_CONFIG_PARSING_UNSUCCESSFUL` | The provided mission_config file could not be parsed. Mission state will be set to FAILED. |
        | `21` | `MISSION_FAILED_CONFIG_MISSING_DATA` | The provided mission_config file does not contain sufficient data for plannification. Mission state will be set to FAILED. |
        | `22` | `MISSION_FAILED_MISSION_COMPROMISED` | The mission is compromised and is unable to continue. Mission state will be set to FAILED. |
        | `23` | `MISSION_FAILED_DISCONNECTED_SWARM_PLANNER` | Could not communicate with swarm planner, results in process failure. Mission state will be set to FAILED. |
        | `24` | `MISSION_FAILED_DISCONNECTED_EDGE` | Could not communicate with  edge modules, results in process failure. Mission state will be set to FAILED. |
        | `25` | `MISSION_FAILED_DISCONNECTED_AUTONOMY` | Could not communicate with at least one autonomy module, timeout results in mission failure. Mission state will be set to FAILED |
        | `30` | `PLANNING_WARN_VEHICLES_MISMATCH` | Not enough vehicles for the given mission configuration. Mission state will be set to PLANNED_ALTERNATIVE |
        | `31` | `PLANNING_WARN_NOT_ENOUGH_COVERAGE` | not enough coverage for the given mission configuration. Mission state will be set to PLANNED_ALTERNATIVE |
        | `32` | `PLANNING_WARN_DATE_COMPROMISED` | Requested start or end date is compromised in planning solution. Mission state will be set to PLANNED anyway |
        | `40` | `PLANNING_FAILED_NO_SOLUTION_FOUND` | No planning solution found. New init_mission needed with adjusted configuration. Mission state will be set to PLANNED_FAILED |
        | `41` | `PLANNING_FAILED` | Swarm planner process fail,  Mission state will be set to PLANNED_FAILED. |

        #### c2_imugs2.core.models.MissionIssue

        Language: **Python** · Evidence: [`src/c2_imugs2/core/models.py:49`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/core/models.py#L49)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `NONE` |  |
        | `10` | `MISSION_WARN_ID_ALREADY_USED` |  |
        | `11` | `MISSION_WARN_UGV_UNAVAILABLE` |  |
        | `12` | `MISSION_WARN_CONFIG_UNKNOWN_DATA` |  |
        | `13` | `MISSION_WARN_STATUS_NOT_CHANGED` |  |
        | `14` | `MISSION_WARN_DISCONNECTED_SWARM_PLANNER` |  |
        | `15` | `MISSION_WARN_DISCONNECTED_SWARMING_EDGE` |  |
        | `16` | `MISSION_WARN_DISCONNECTED_AUTONOMY` |  |
        | `20` | `MISSION_FAILED_CONFIG_PARSING_UNSUCCESSFUL` |  |
        | `21` | `MISSION_FAILED_CONFIG_MISSING_DATA` |  |
        | `22` | `MISSION_FAILED_MISSION_COMPROMISED` |  |
        | `23` | `MISSION_FAILED_DISCONNECTED_SWARM_PLANNER` |  |
        | `24` | `MISSION_FAILED_DISCONNECTED_EDGE` |  |
        | `25` | `MISSION_FAILED_DISCONNECTED_AUTONOMY` |  |
        | `30` | `PLANNING_WARN_VEHICLES_MISMATCH` |  |
        | `31` | `PLANNING_WARN_NOT_ENOUGH_COVERAGE` |  |
        | `32` | `PLANNING_WARN_DATE_COMPROMISED` |  |
        | `40` | `PLANNING_FAILED_NO_SOLUTION_FOUND` |  |
        | `41` | `PLANNING_FAILED` |  |


    ??? abstract "MissionRequest · consistent · 1 definitions"
        #### c2_imugs2.core.models.MissionRequest

        Language: **Python** · Evidence: [`src/c2_imugs2/core/models.py:40`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/core/models.py#L40)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `INIT` |  |
        | `1` | `APPROVE` |  |
        | `2` | `START` |  |
        | `3` | `PAUSE` |  |
        | `4` | `STOP` |  |
        | `5` | `DELETE` |  |

        #### Values used by the verified navigation run

        | Value | Member | Where it appeared |
        |---:|---|---|
        | `0` | `INIT` | initialize |
        | `1` | `APPROVE` | install stopped task |
        | `2` | `START` | execute task |

    ??? abstract "MissionStatus · consistent · 4 definitions"
        #### c2_msgs.MissionStatus

        Language: **C++** · Evidence: [`backend/fog/centralized-coordination/src/message_packages/c2_msgs/json/Enums.hpp:28`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/c2_msgs/json/Enums.hpp#L28)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `NONE` | NOT USED |
        | `1` | `PLANNED` | Mission is correctly planned |
        | `2` | `PLANNED_ALTERNATIVE` | Mission has alternative planned |
        | `3` | `PLANNED_FAILED` | Mission planning failed |
        | `4` | `ACCEPTED` | Mission is accepted |
        | `5` | `STARTED` | Mission is started |
        | `6` | `PAUSED` | Mission is paused |
        | `7` | `FAILED` | Mission has failed |
        | `8` | `STOPPED` | Mission is finished by request.  it will not stop a mission, except if FAILED or another mission is started. |
        | `9` | `DELETED` | Missio is deleted from the system. |
        | `10` | `COMPLETED` |  |

        #### centralized_msgs.MissionStatus

        Language: **C++** · Evidence: [`backend/fog/centralized-coordination/src/message_packages/centralized_msgs/json/Enums.hpp:37`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/centralized_msgs/json/Enums.hpp#L37)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `NONE` | NOT USED |
        | `1` | `PLANNED` | Mission is correctly planned |
        | `2` | `PLANNED_ALTERNATIVE` | Mission has alternative planned |
        | `3` | `PLANNED_FAILED` | Mission planning failed |
        | `4` | `ACCEPTED` | Mission is accepted |
        | `5` | `STARTED` | Mission is started |
        | `6` | `PAUSED` | Mission is paused |
        | `7` | `FAILED` | Mission has failed |
        | `8` | `STOPPED` | Mission is finished by request.  itwill not stop a mission, except if FAILED or another mission is started. |
        | `9` | `DELETED` | Missio is deleted from the system. |
        | `10` | `COMPLETED` |  |

        #### centralized_msgs.MissionStatus

        Language: **C++** · Evidence: [`backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/json/Enums.hpp:37`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/json/Enums.hpp#L37)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `NONE` | NOT USED |
        | `1` | `PLANNED` | Mission is correctly planned |
        | `2` | `PLANNED_ALTERNATIVE` | Mission has alternative planned |
        | `3` | `PLANNED_FAILED` | Mission planning failed |
        | `4` | `ACCEPTED` | Mission is accepted |
        | `5` | `STARTED` | Mission is started |
        | `6` | `PAUSED` | Mission is paused |
        | `7` | `FAILED` | Mission has failed |
        | `8` | `STOPPED` | Mission is finished by request.  itwill not stop a mission, except if FAILED or another mission is started. |
        | `9` | `DELETED` | Missio is deleted from the system. |
        | `10` | `COMPLETED` |  |

        #### c2_imugs2.core.models.MissionStatus

        Language: **Python** · Evidence: [`src/c2_imugs2/core/models.py:26`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/core/models.py#L26)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `NONE` |  |
        | `1` | `PLANNED` |  |
        | `2` | `PLANNED_ALTERNATIVE` |  |
        | `3` | `PLANNED_FAILED` |  |
        | `4` | `ACCEPTED` |  |
        | `5` | `STARTED` |  |
        | `6` | `PAUSED` |  |
        | `7` | `FAILED` |  |
        | `8` | `STOPPED` |  |
        | `9` | `DELETED` |  |
        | `10` | `COMPLETED` |  |

        #### Values used by the verified navigation run

        | Value | Member | Where it appeared |
        |---:|---|---|
        | `0` | `NONE` | planning begins |
        | `1` | `PLANNED` | 10-waypoint plan received |
        | `4` | `ACCEPTED` | task dispatched stopped |
        | `5` | `STARTED` | task execution requested |
        | `10` | `COMPLETED` | Themis finished its task |

    ??? abstract "MissionStatusRequest · consistent · 3 definitions"
        #### c2_msgs.MissionStatusRequest

        Language: **C++** · Evidence: [`backend/fog/centralized-coordination/src/message_packages/c2_msgs/json/Enums.hpp:43`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/c2_msgs/json/Enums.hpp#L43)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `INIT` | Initialize mission |
        | `1` | `APPROVE` | Approve mission |
        | `2` | `START` | Start mission |
        | `3` | `PAUSE` | Pause mission |
        | `4` | `STOP` | Stop mission |
        | `5` | `DELETE` | Delete mission |

        #### centralized_msgs.MissionStatusRequest

        Language: **C++** · Evidence: [`backend/fog/centralized-coordination/src/message_packages/centralized_msgs/json/Enums.hpp:52`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/centralized_msgs/json/Enums.hpp#L52)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `INIT` | Initialize mission |
        | `1` | `APPROVE` | Approve mission |
        | `2` | `START` | Start mission |
        | `3` | `PAUSE` | Pause mission |
        | `4` | `STOP` | Stop mission |
        | `5` | `DELETE` | Delete mission |

        #### centralized_msgs.MissionStatusRequest

        Language: **C++** · Evidence: [`backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/json/Enums.hpp:52`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/json/Enums.hpp#L52)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `INIT` | Initialize mission |
        | `1` | `APPROVE` | Approve mission |
        | `2` | `START` | Start mission |
        | `3` | `PAUSE` | Pause mission |
        | `4` | `STOP` | Stop mission |
        | `5` | `DELETE` | Delete mission |

        #### Values used by the verified navigation run

        | Value | Member | Where it appeared |
        |---:|---|---|
        | `0` | `INIT` | initialize |
        | `1` | `APPROVE` | install stopped task |
        | `2` | `START` | execute task |

    ??? abstract "ObjectiveType · consistent · 3 definitions"
        #### c2_msgs.ObjectiveType

        Language: **C++** · Evidence: [`backend/fog/centralized-coordination/src/message_packages/c2_msgs/json/Enums.hpp:99`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/c2_msgs/json/Enums.hpp#L99)

        | Value | Member | Source comment |
        |---:|---|---|
        | `2` | `TRACKING_TARGET_INFORMATION` |  |

        #### centralized_msgs.ObjectiveType

        Language: **C++** · Evidence: [`backend/fog/centralized-coordination/src/message_packages/centralized_msgs/json/Enums.hpp:108`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/centralized_msgs/json/Enums.hpp#L108)

        | Value | Member | Source comment |
        |---:|---|---|
        | `2` | `TRACKING_TARGET_INFORMATION` |  |

        #### centralized_msgs.ObjectiveType

        Language: **C++** · Evidence: [`backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/json/Enums.hpp:108`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/json/Enums.hpp#L108)

        | Value | Member | Source comment |
        |---:|---|---|
        | `2` | `TRACKING_TARGET_INFORMATION` |  |


    ??? abstract "PlanStatus · consistent · 2 definitions"
        #### centralized_msgs.PlanStatus

        Language: **C++** · Evidence: [`backend/fog/centralized-coordination/src/message_packages/centralized_msgs/json/Enums.hpp:5`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/centralized_msgs/json/Enums.hpp#L5)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `NONE` |  |
        | `1` | `PLANNED` |  |
        | `3` | `PLAN_FAILED` |  |

        #### centralized_msgs.PlanStatus

        Language: **C++** · Evidence: [`backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/json/Enums.hpp:5`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/json/Enums.hpp#L5)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `NONE` |  |
        | `1` | `PLANNED` |  |
        | `3` | `PLAN_FAILED` |  |


    ??? abstract "RequestState · consistent · 4 definitions"
        #### autonomy_msgs.RequestState

        Language: **C++** · Evidence: [`backend/edge/agent-tasks-supervisor/ros2ws/src/message_packages/autonomy_msgs/json/Enums.hpp:4`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/message_packages/autonomy_msgs/json/Enums.hpp#L4)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `INACTIVATE` | inactivate client & do nothing |
        | `1` | `ACTIVATE` | activate the client & start tasks |

        #### task_msgs.RequestState

        Language: **C++** · Evidence: [`backend/edge/agent-tasks-supervisor/ros2ws/src/message_packages/task_msgs/json/Enums.hpp:4`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/message_packages/task_msgs/json/Enums.hpp#L4)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `INACTIVATE` | inactivate client & do nothing |
        | `1` | `ACTIVATE` | activate the client & start tasks |

        #### autonomy_msgs.RequestState

        Language: **C++** · Evidence: [`backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/json/Enums.hpp:4`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/json/Enums.hpp#L4)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `INACTIVATE` | inactivate client & do nothing |
        | `1` | `ACTIVATE` | activate the client & start tasks |

        #### task_msgs.RequestState

        Language: **C++** · Evidence: [`backend/fog/centralized-coordination/src/message_packages/task_msgs/json/Enums.hpp:4`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/task_msgs/json/Enums.hpp#L4)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `INACTIVATE` | inactivate client & do nothing |
        | `1` | `ACTIVATE` | activate the client & start tasks |


    ??? abstract "State · consistent · 4 definitions"
        #### autonomy_msgs.State

        Language: **C++** · Evidence: [`backend/edge/agent-tasks-supervisor/ros2ws/src/message_packages/autonomy_msgs/json/Enums.hpp:10`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/message_packages/autonomy_msgs/json/Enums.hpp#L10)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `INACTIVE` | inactive |
        | `1` | `ACTIVE` | active |

        #### task_msgs.State

        Language: **C++** · Evidence: [`backend/edge/agent-tasks-supervisor/ros2ws/src/message_packages/task_msgs/json/Enums.hpp:10`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/message_packages/task_msgs/json/Enums.hpp#L10)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `INACTIVE` | inactive |
        | `1` | `ACTIVE` | active |

        #### autonomy_msgs.State

        Language: **C++** · Evidence: [`backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/json/Enums.hpp:10`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/json/Enums.hpp#L10)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `INACTIVE` | inactive |
        | `1` | `ACTIVE` | active |

        #### task_msgs.State

        Language: **C++** · Evidence: [`backend/fog/centralized-coordination/src/message_packages/task_msgs/json/Enums.hpp:10`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/task_msgs/json/Enums.hpp#L10)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `INACTIVE` | inactive |
        | `1` | `ACTIVE` | active |


    ??? abstract "TaskRequestState · consistent · 4 definitions"
        #### autonomy_msgs.TaskRequestState

        Language: **C++** · Evidence: [`backend/edge/agent-tasks-supervisor/ros2ws/src/message_packages/autonomy_msgs/json/Enums.hpp:16`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/message_packages/autonomy_msgs/json/Enums.hpp#L16)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `STOP` | request to stop the task & re-init |
        | `1` | `EXECUTE` | request to execute the task |
        | `2` | `PAUSE` | request to pause the task |
        | `3` | `DELETE` | request to delete the task |

        #### task_msgs.TaskRequestState

        Language: **C++** · Evidence: [`backend/edge/agent-tasks-supervisor/ros2ws/src/message_packages/task_msgs/json/Enums.hpp:16`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/message_packages/task_msgs/json/Enums.hpp#L16)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `STOP` | request to stop the task & re-init |
        | `1` | `EXECUTE` | request to execute the task |
        | `2` | `PAUSE` | request to pause the task |
        | `3` | `DELETE` | request to delete the task |

        #### autonomy_msgs.TaskRequestState

        Language: **C++** · Evidence: [`backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/json/Enums.hpp:16`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/json/Enums.hpp#L16)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `STOP` | request to stop the task & re-init |
        | `1` | `EXECUTE` | request to execute the task |
        | `2` | `PAUSE` | request to pause the task |
        | `3` | `DELETE` | request to delete the task |

        #### task_msgs.TaskRequestState

        Language: **C++** · Evidence: [`backend/fog/centralized-coordination/src/message_packages/task_msgs/json/Enums.hpp:16`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/task_msgs/json/Enums.hpp#L16)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `STOP` | request to stop the task & re-init |
        | `1` | `EXECUTE` | request to execute the task |
        | `2` | `PAUSE` | request to pause the task |
        | `3` | `DELETE` | request to delete the task |

        #### Values used by the verified navigation run

        | Value | Member | Where it appeared |
        |---:|---|---|
        | `1` | `EXECUTE` | START fan-out |

    ??? abstract "TaskState · conflict · 5 definitions"
        !!! warning "Conflicting extracted definitions"
            2 different member/value signatures were found.

        #### autonomy_msgs.TaskState

        Language: **C++** · Evidence: [`backend/edge/agent-tasks-supervisor/ros2ws/src/message_packages/autonomy_msgs/json/Enums.hpp:24`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/message_packages/autonomy_msgs/json/Enums.hpp#L24)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `STOPPED` | stopped, but not completed or started |
        | `1` | `STARTED` | started |
        | `2` | `PAUSED` | paused |
        | `3` | `COMPLETED` | completed the task |
        | `4` | `ABORTED` | aborted |
        | `5` | `DELETED` | deleted |

        #### task_msgs.TaskState

        Language: **C++** · Evidence: [`backend/edge/agent-tasks-supervisor/ros2ws/src/message_packages/task_msgs/json/Enums.hpp:24`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/message_packages/task_msgs/json/Enums.hpp#L24)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `STOPPED` | stopped, but not completed or started |
        | `1` | `STARTED` | started |
        | `2` | `PAUSED` | paused |
        | `3` | `COMPLETED` | completed the task |
        | `4` | `ABORTED` | aborted |
        | `5` | `DELETED` | deleted |

        #### autonomy_msgs.TaskState

        Language: **C++** · Evidence: [`backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/json/Enums.hpp:24`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/json/Enums.hpp#L24)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `STOPPED` | stopped, but not completed or started |
        | `1` | `STARTED` | started |
        | `2` | `PAUSED` | paused |
        | `3` | `COMPLETED` | completed the task |
        | `4` | `ABORTED` | aborted |
        | `5` | `DELETED` | deleted |

        #### task_msgs.TaskState

        Language: **C++** · Evidence: [`backend/fog/centralized-coordination/src/message_packages/task_msgs/json/Enums.hpp:24`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/task_msgs/json/Enums.hpp#L24)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `STOPPED` | stopped, but not completed or started |
        | `1` | `STARTED` | started |
        | `2` | `PAUSED` | paused |
        | `3` | `COMPLETED` | completed the task |
        | `4` | `ABORTED` | aborted |
        | `5` | `DELETED` | deleted |

        #### c2_imugs2.core.models.TaskState

        Language: **Python** · Evidence: [`src/c2_imugs2/core/models.py:71`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/core/models.py#L71)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `STOP` |  |
        | `1` | `EXECUTE` |  |
        | `2` | `PAUSE` |  |
        | `3` | `DELETE` |  |
        | `4` | `COMPLETED` |  |

        #### Values used by the verified navigation run

        Runtime definition: **task_msgs.TaskState used by Fleet and Edge; not c2_imugs2.core.models.TaskState**.

        | Value | Member | Where it appeared |
        |---:|---|---|
        | `0` | `STOPPED` | after APPROVE |
        | `1` | `STARTED` | after START |
        | `3` | `COMPLETED` | final waypoint reached |

    ??? abstract "TaskType · consistent · 4 definitions"
        #### autonomy_msgs.TaskType

        Language: **C++** · Evidence: [`backend/edge/agent-tasks-supervisor/ros2ws/src/message_packages/autonomy_msgs/json/Enums.hpp:34`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/message_packages/autonomy_msgs/json/Enums.hpp#L34)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `DRIVE` | waypoint drive task |
        | `1` | `EXAMPLE_PERIPHERAL_CAMERA` | move camera task (example) |
        | `2` | `EXAMPLE_DEFENSE_SHIELDS` | move camera task (example) |

        #### task_msgs.TaskType

        Language: **C++** · Evidence: [`backend/edge/agent-tasks-supervisor/ros2ws/src/message_packages/task_msgs/json/Enums.hpp:34`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/message_packages/task_msgs/json/Enums.hpp#L34)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `DRIVE` | waypoint drive task |
        | `1` | `EXAMPLE_PERIPHERAL_CAMERA` | move camera task (example) |
        | `2` | `EXAMPLE_DEFENSE_SHIELDS` | move camera task (example) |

        #### autonomy_msgs.TaskType

        Language: **C++** · Evidence: [`backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/json/Enums.hpp:34`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/json/Enums.hpp#L34)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `DRIVE` | waypoint drive task |
        | `1` | `EXAMPLE_PERIPHERAL_CAMERA` | move camera task (example) |
        | `2` | `EXAMPLE_DEFENSE_SHIELDS` | move camera task (example) |

        #### task_msgs.TaskType

        Language: **C++** · Evidence: [`backend/fog/centralized-coordination/src/message_packages/task_msgs/json/Enums.hpp:34`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/task_msgs/json/Enums.hpp#L34)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `DRIVE` | waypoint drive task |
        | `1` | `EXAMPLE_PERIPHERAL_CAMERA` | move camera task (example) |
        | `2` | `EXAMPLE_DEFENSE_SHIELDS` | move camera task (example) |

        #### Values used by the verified navigation run

        | Value | Member | Where it appeared |
        |---:|---|---|
        | `0` | `DRIVE` | Fleet AddTask request |

    ??? abstract "UpdateMode · consistent · 1 definitions"
        #### c2_imugs2.operations.service.UpdateMode

        Language: **Python** · Evidence: [`src/c2_imugs2/operations/service.py:36`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/operations/service.py#L36)

        | Value | Member | Source comment |
        |---:|---|---|
        | `full` | `FULL` |  |
        | `delta` | `DELTA` |  |


    ??? abstract "VehicleChanges · consistent · 3 definitions"
        #### c2_msgs.VehicleChanges

        Language: **C++** · Evidence: [`backend/fog/centralized-coordination/src/message_packages/c2_msgs/json/Enums.hpp:71`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/c2_msgs/json/Enums.hpp#L71)

        | Value | Member | Source comment |
        |---:|---|---|
        | `1` | `ADD` | Add the vehicles in the list to the mission |
        | `0` | `REMOVE` | Remove the vehicles in the list from the mission |

        #### centralized_msgs.VehicleChanges

        Language: **C++** · Evidence: [`backend/fog/centralized-coordination/src/message_packages/centralized_msgs/json/Enums.hpp:80`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/centralized_msgs/json/Enums.hpp#L80)

        | Value | Member | Source comment |
        |---:|---|---|
        | `1` | `ADD` | Add the vehicles in the list to the mission |
        | `0` | `REMOVE` | Remove the vehicles in the list from the mission |

        #### centralized_msgs.VehicleChanges

        Language: **C++** · Evidence: [`backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/json/Enums.hpp:80`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/json/Enums.hpp#L80)

        | Value | Member | Source comment |
        |---:|---|---|
        | `1` | `ADD` | Add the vehicles in the list to the mission |
        | `0` | `REMOVE` | Remove the vehicles in the list from the mission |


    ??? abstract "VehicleFormation · consistent · 4 definitions"
        #### c2_msgs.VehicleFormation

        Language: **C++** · Evidence: [`backend/fog/centralized-coordination/src/message_packages/c2_msgs/json/Enums.hpp:60`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/c2_msgs/json/Enums.hpp#L60)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `NONE` |  |
        | `1` | `COLUMN` |  |
        | `2` | `LINE` |  |
        | `3` | `WEDGE` |  |
        | `4` | `VEE` |  |
        | `5` | `LEFT_FLANK` |  |
        | `6` | `RIGHT_FLANK` |  |

        #### centralized_msgs.VehicleFormation

        Language: **C++** · Evidence: [`backend/fog/centralized-coordination/src/message_packages/centralized_msgs/json/Enums.hpp:69`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/centralized_msgs/json/Enums.hpp#L69)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `NONE` |  |
        | `1` | `COLUMN` |  |
        | `2` | `LINE` |  |
        | `3` | `WEDGE` |  |
        | `4` | `VEE` |  |
        | `5` | `LEFT_FLANK` |  |
        | `6` | `RIGHT_FLANK` |  |

        #### centralized_msgs.VehicleFormation

        Language: **C++** · Evidence: [`backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/json/Enums.hpp:69`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/json/Enums.hpp#L69)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `NONE` |  |
        | `1` | `COLUMN` |  |
        | `2` | `LINE` |  |
        | `3` | `WEDGE` |  |
        | `4` | `VEE` |  |
        | `5` | `LEFT_FLANK` |  |
        | `6` | `RIGHT_FLANK` |  |

        #### c2_imugs2.core.models.VehicleFormation

        Language: **Python** · Evidence: [`src/c2_imugs2/core/models.py:16`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/core/models.py#L16)

        | Value | Member | Source comment |
        |---:|---|---|
        | `0` | `NONE` |  |
        | `1` | `COLUMN` |  |
        | `2` | `LINE` |  |
        | `3` | `WEDGE` |  |
        | `4` | `VEE` |  |
        | `5` | `LEFT_FLANK` |  |
        | `6` | `RIGHT_FLANK` |  |



=== "Schemas (4)"

    ## Canonical JSON schemas

    Each entry includes the flattened contract and complete checked-in schema.

    ??? abstract "AgentProfile · agent_profile.schema.json"
        [Open standalone page](schemas/agent-profile.md)

        | JSON path | Type | Required | Constraints / description |
        |---|---|---|---|
        | `$` | `object` | yes |  |
        | `$.agent_id` | `string` | yes |  |
        | `$.name` | `string` | no |  |
        | `$.vehicle_type` | `string` | no |  |
        | `$.status` | `string` | no |  |
        | `$.current_location` | `array` | yes | minItems: 2; maxItems: 2 |
        | `$.current_location[]` | `number` | yes |  |
        | `$.constraints` | `object` | no |  |
        | `$.capabilities` | `array` | no |  |
        | `$.capabilities[]` | `string` | yes |  |

        #### Verified navigation data

        ##### Canonical profile for the participating robot

        Phase: **robot discovery** · Evidence class: `runtime_observed`

        ```json
        {
          "agent_id": "f9992bb3-9871-451f-90a0-9207eb9fe6c5",
          "name": "Themis Fr",
          "vehicle_type": "UGV",
          "status": "1",
          "current_location": [
            4.392588,
            50.844317
          ],
          "constraints": {
            "max_speed": 4.5,
            "max_acceleration": 8.0,
            "max_weight": 16.0,
            "max_tilt_angle": 1.8
          }
        }
        ```

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`legacy_ros/config/config_autonomy.yaml:6`](https://github.com/LEBaz2211/C2_imugs2/blob/main/legacy_ros/config/config_autonomy.yaml#L6)

        #### Complete schema

        ```json
        {
          "$schema": "https://json-schema.org/draft/2020-12/schema",
          "title": "AgentProfile",
          "type": "object",
          "required": [
            "agent_id",
            "current_location"
          ],
          "properties": {
            "agent_id": {
              "type": "string"
            },
            "name": {
              "type": "string"
            },
            "vehicle_type": {
              "type": "string"
            },
            "status": {
              "type": "string"
            },
            "current_location": {
              "type": "array",
              "items": {
                "type": "number"
              },
              "minItems": 2,
              "maxItems": 2
            },
            "constraints": {
              "type": "object"
            },
            "capabilities": {
              "type": "array",
              "items": {
                "type": "string"
              }
            }
          }
        }
        ```

    ??? abstract "MapFeature · map_feature.schema.json"
        [Open standalone page](schemas/map-feature.md)

        | JSON path | Type | Required | Constraints / description |
        |---|---|---|---|
        | `$` | `object` | yes |  |
        | `$.feature_id` | `string` | yes |  |
        | `$.name` | `string` | no |  |
        | `$.feature_type` | `string` | yes |  |
        | `$.geometry` | `object` | yes |  |
        | `$.properties` | `object` | no |  |

        #### Complete schema

        ```json
        {
          "$schema": "https://json-schema.org/draft/2020-12/schema",
          "title": "MapFeature",
          "type": "object",
          "required": [
            "feature_id",
            "feature_type",
            "geometry"
          ],
          "properties": {
            "feature_id": {
              "type": "string"
            },
            "name": {
              "type": "string"
            },
            "feature_type": {
              "type": "string"
            },
            "geometry": {
              "type": "object"
            },
            "properties": {
              "type": "object"
            }
          }
        }
        ```

    ??? abstract "MissionConfig · mission_config.schema.json"
        [Open standalone page](schemas/mission-config.md)

        | JSON path | Type | Required | Constraints / description |
        |---|---|---|---|
        | `$` | `object` | yes |  |
        | `$.schema_version` | `string` | no |  |
        | `$.mission_id` | `string` | yes |  |
        | `$.phase` | `integer` | no | minimum: 0 |
        | `$.name` | `string` | no |  |
        | `$.behavior` | `integer` | yes | enum: 0, 1, 2 |
        | `$.vehicles` | `array` | yes | minItems: 1 |
        | `$.vehicles[]` | `string` | yes |  |
        | `$.start` | `object` | no |  |
        | `$.transit` | `object` | no |  |
        | `$.objective` | `object` | yes |  |
        | `$.objective.geometries` | `array` | yes | minItems: 1 |
        | `$.objective.geometries[]` | `$ref` | yes | $ref: #/$defs/geometryRef |
        | `$.objective.minimum_distance` | `number` | no |  |
        | `$.objective.maximum_distance` | `number` | no |  |
        | `$.objective.vehicle_formation` | `integer` | no | enum: 0, 1, 2, 3, 4, 5, 6 |
        | `$.objective.vehicle_formation_distance` | `number` | no |  |
        | `$.objective.vehicle_orientation` | `array` | no |  |
        | `$.objective.vehicle_orientation[]` | `number` | yes |  |
        | `$.objective.vehicle_orientation_origin` | `$ref` | no | $ref: #/$defs/geometryRef |
        | `$.objective.vehicle_order` | `boolean` | no |  |
        | `$.objective.line_of_sight` | `$ref` | no | $ref: #/$defs/geometryRef |
        | `$.objective.line_of_sight_propagation` | `boolean` | no |  |
        | `$.objective.maximize_coverage` | `boolean` | no |  |
        | `$.objective.maximum_coverage_distances` | `array` | no | description: Coverage swath widths in metres: one shared value or one value per mission vehicle.; minItems: 1 |
        | `$.objective.maximum_coverage_distances[]` | `number` | yes |  |
        | `$.objective.arrival_time` | `$ref` | no | $ref: #/$defs/timeWindow |
        | `$.mission_end_time` | `string` | no |  |

        #### Verified navigation data

        ##### Canonical mission submitted to the adapter

        Phase: **INIT** · Evidence class: `verified_flow`

        ```json
        {
          "mission_id": "44444444-5555-4666-8777-888888888888",
          "behavior": 0,
          "vehicles": [
            "f9992bb3-9871-451f-90a0-9207eb9fe6c5"
          ],
          "objective": {
            "geometries": [
              {
                "geometry": {
                  "geometry_type": "Point",
                  "coordinates": [
                    4.39167,
                    50.84417
                  ]
                }
              }
            ]
          },
          "transit": {
            "optimization": {
              "road_usage": 1.0
            },
            "desired_vehicle_constraints": {
              "max_speed": 1.3
            }
          }
        }
        ```

        - The adapter uses canonical optimization; the legacy REST payload below translates it to optimalization.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:108`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L108), [`src/c2_imugs2/infrastructure/legacy/rest.py:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/infrastructure/legacy/rest.py#L1)

        #### Complete schema

        ```json
        {
          "$schema": "https://json-schema.org/draft/2020-12/schema",
          "title": "MissionConfig",
          "type": "object",
          "required": [
            "mission_id",
            "behavior",
            "vehicles",
            "objective"
          ],
          "properties": {
            "schema_version": {
              "type": "string"
            },
            "mission_id": {
              "type": "string"
            },
            "phase": {
              "type": "integer",
              "minimum": 0
            },
            "name": {
              "type": "string"
            },
            "behavior": {
              "type": "integer",
              "enum": [
                0,
                1,
                2
              ]
            },
            "vehicles": {
              "type": "array",
              "items": {
                "type": "string"
              },
              "minItems": 1
            },
            "start": {
              "type": "object"
            },
            "transit": {
              "type": "object"
            },
            "objective": {
              "type": "object",
              "required": [
                "geometries"
              ],
              "properties": {
                "geometries": {
                  "type": "array",
                  "items": {
                    "$ref": "#/$defs/geometryRef"
                  },
                  "minItems": 1
                },
                "minimum_distance": {
                  "type": "number"
                },
                "maximum_distance": {
                  "type": "number"
                },
                "vehicle_formation": {
                  "type": "integer",
                  "enum": [
                    0,
                    1,
                    2,
                    3,
                    4,
                    5,
                    6
                  ]
                },
                "vehicle_formation_distance": {
                  "type": "number"
                },
                "vehicle_orientation": {
                  "type": "array",
                  "items": {
                    "type": "number"
                  }
                },
                "vehicle_orientation_origin": {
                  "$ref": "#/$defs/geometryRef"
                },
                "vehicle_order": {
                  "type": "boolean"
                },
                "line_of_sight": {
                  "$ref": "#/$defs/geometryRef"
                },
                "line_of_sight_propagation": {
                  "type": "boolean"
                },
                "maximize_coverage": {
                  "type": "boolean"
                },
                "maximum_coverage_distances": {
                  "type": "array",
                  "description": "Coverage swath widths in metres: one shared value or one value per mission vehicle.",
                  "items": {
                    "type": "number",
                    "exclusiveMinimum": 0
                  },
                  "minItems": 1
                },
                "arrival_time": {
                  "$ref": "#/$defs/timeWindow"
                }
              }
            },
            "mission_end_time": {
              "type": "string"
            }
          },
          "$defs": {
            "geometryRef": {
              "type": "object",
              "oneOf": [
                {
                  "required": [
                    "feature_id"
                  ]
                },
                {
                  "required": [
                    "geometry"
                  ]
                }
              ],
              "properties": {
                "feature_id": {
                  "type": "string"
                },
                "geometry": {
                  "$ref": "#/$defs/inlineGeometry"
                }
              }
            },
            "position": {
              "type": "array",
              "prefixItems": [
                {
                  "type": "number",
                  "minimum": -180,
                  "maximum": 180
                },
                {
                  "type": "number",
                  "minimum": -90,
                  "maximum": 90
                }
              ],
              "items": false,
              "minItems": 2,
              "maxItems": 2
            },
            "inlineGeometry": {
              "type": "object",
              "required": [
                "geometry_type",
                "coordinates"
              ],
              "oneOf": [
                {
                  "properties": {
                    "geometry_type": {
                      "const": "Point"
                    },
                    "coordinates": {
                      "$ref": "#/$defs/position"
                    }
                  }
                },
                {
                  "properties": {
                    "geometry_type": {
                      "const": "LineString"
                    },
                    "coordinates": {
                      "type": "array",
                      "items": {
                        "$ref": "#/$defs/position"
                      },
                      "minItems": 2
                    }
                  }
                },
                {
                  "properties": {
                    "geometry_type": {
                      "const": "Polygon"
                    },
                    "coordinates": {
                      "type": "array",
                      "items": {
                        "type": "array",
                        "items": {
                          "$ref": "#/$defs/position"
                        },
                        "minItems": 4
                      },
                      "minItems": 1,
                      "maxItems": 1
                    }
                  }
                }
              ]
            },
            "timeWindow": {
              "type": "object",
              "required": [
                "earliest",
                "target",
                "latest"
              ],
              "properties": {
                "earliest": {
                  "type": "string"
                },
                "target": {
                  "type": "string"
                },
                "latest": {
                  "type": "string"
                }
              }
            }
          }
        }
        ```

    ??? abstract "TaskPlan · task_plan.schema.json"
        [Open standalone page](schemas/task-plan.md)

        | JSON path | Type | Required | Constraints / description |
        |---|---|---|---|
        | `$` | `object` | yes |  |
        | `$.mission_id` | `string` | yes |  |
        | `$.tasks` | `object` | yes |  |

        #### Verified navigation data

        ##### Observed 10-waypoint plan (recorded coordinate excerpt)

        Phase: **plan retrieval** · Evidence class: `observed_excerpt`

        ```json
        {
          "mission_id": "44444444-5555-4666-8777-888888888888",
          "tasks": {
            "f9992bb3-9871-451f-90a0-9207eb9fe6c5": {
              "task_id": "<generated-task-uuid>",
              "primitives": [
                {
                  "primitive_id": "<generated-primitive-uuid>",
                  "primitive_type": "waypoint",
                  "completion": {
                    "ends_objective": true,
                    "ends_task": false
                  }
                }
              ],
              "objectives": [
                {
                  "objective_id": "<first-generated-objective-uuid>",
                  "parallel_execution": true,
                  "primitives": [
                    {
                      "primitive_id": "<generated-primitive-uuid>",
                      "parameters": {
                        "coordinates": [
                          4.3925979,
                          50.8443434
                        ],
                        "speed": 1.3,
                        "max_speed": 1.3
                      }
                    }
                  ]
                },
                {
                  "objective_id": "<second-generated-objective-uuid>",
                  "parallel_execution": true,
                  "primitives": [
                    {
                      "primitive_id": "<generated-primitive-uuid>",
                      "parameters": {
                        "coordinates": [
                          4.3923021488298595,
                          50.8442681286928
                        ],
                        "speed": 1.3,
                        "max_speed": 1.3
                      }
                    }
                  ]
                },
                {
                  "objective_id": "<final-generated-objective-uuid>",
                  "parallel_execution": true,
                  "primitives": [
                    {
                      "primitive_id": "<generated-primitive-uuid>",
                      "parameters": {
                        "coordinates": [
                          4.391670213379427,
                          50.84417059346137
                        ],
                        "speed": 1.3,
                        "max_speed": 1.3
                      }
                    }
                  ]
                }
              ]
            }
          }
        }
        ```

        - This is deliberately an excerpt: the verified route contained 10 objectives, while the runtime record preserved in the walkthrough names the first two and final coordinates.
        - Generated task, primitive, and objective UUIDs change on every GetPlan serialization.

        Evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:599`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L599)

        #### Complete schema

        ```json
        {
          "$schema": "https://json-schema.org/draft/2020-12/schema",
          "title": "TaskPlan",
          "type": "object",
          "required": [
            "mission_id",
            "tasks"
          ],
          "properties": {
            "mission_id": {
              "type": "string"
            },
            "tasks": {
              "type": "object",
              "additionalProperties": {
                "type": "object",
                "required": [
                  "task_id",
                  "primitives",
                  "objectives"
                ],
                "properties": {
                  "task_id": {
                    "type": "string"
                  },
                  "primitives": {
                    "type": "array"
                  },
                  "objectives": {
                    "type": "array"
                  }
                }
              }
            }
          }
        }
        ```



## Extraction limitation

Static extraction can miss names assembled dynamically at runtime. A declaration proves that it exists in source; it does not by itself prove that it was observed on a running ROS graph.
