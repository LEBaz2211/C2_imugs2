from __future__ import annotations

from pathlib import Path
from typing import Any


MISSION_ID = "85b6dc76-774c-4db8-a208-48c68ac6237d"
AGENT_ID = "f9992bb3-9871-451f-90a0-9207eb9fe6c5"
OBJECTIVE = [4.39167, 50.84417]
START = [4.392588, 50.844317]

CENTRAL = "backend/fog/centralized-coordination/src/centralized_coordination/src"
CENTRAL_MSGS = "backend/fog/centralized-coordination/src/message_packages"
REST = "backend/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src"
PLANNER = "backend/fog/planner/ros2ws/src/planner/planner/planner_node.py"
EDGE = "backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp"
AUTONOMY = "backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/test/test_autonomy.cpp"
EDGE_MSGS = "backend/edge/agent-tasks-supervisor/ros2ws/src/message_packages"


def build_verified_contract_atlas(repo_root: Path, runtime: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build the deliberately curated, source-backed view used by the system atlas.

    The broader graph in ``contracts.py`` is a discovery catalog. It is useful for
    finding possible interfaces, but regex discoveries are not authoritative. This
    atlas only contains the active mission path and explicitly-labelled gaps that
    were checked against the runnable source selected by the Docker Compose files.
    """

    repo_root = repo_root.resolve()
    runtime = runtime or {}
    ref = lambda path, needle, claim="": _evidence(repo_root, path, needle, claim)

    components = [
        _component(
            "operator",
            "Operator",
            "operator_ui",
            "actor",
            "Creates, reviews, approves, and starts a mission.",
            responsibilities=["Mission intent", "Human approval", "Start authority"],
            tags=["human", "command"],
            source_refs=[ref("frontend/src/App.tsx", 'value: "c2", label: "C2"', "Operator workspace")],
        ),
        _component(
            "browser_ui",
            "Browser UI",
            "operator_ui",
            "application",
            "React mission editor and map. It speaks only the adapter's JSON/SSE contract.",
            runtime_name="http://localhost:5173",
            container="c2-imugs2-ui",
            responsibilities=["Canonical mission draft", "Client-side normalization", "Map and path rendering"],
            tags=["react", "canonical-json"],
            source_refs=[
                ref("frontend/src/App.tsx", "const canSendMission", "Client-side send gate"),
                ref("frontend/src/mission.ts", "export function normalizeMission", "Browser normalization"),
            ],
        ),
        _component(
            "fastapi_adapter",
            "FastAPI compatibility adapter",
            "adapter",
            "adapter",
            "Stable UI boundary. Owns validation, legacy aliases, feature inlining, UUID repair, and ROS read normalization.",
            runtime_name="http://localhost:8000",
            container="c2-imugs2-api",
            responsibilities=["UI API", "Canonical-to-legacy translation", "ROS-to-SSE normalization"],
            tags=["fastapi", "compatibility-boundary"],
            source_refs=[
                ref("src/c2_imugs2/api.py", '@app.post("/api/missions/init")', "Mission Init endpoint"),
                ref("src/c2_imugs2/api.py", '@app.get("/api/events")', "SSE endpoint"),
                ref("src/c2_imugs2/legacy_rest.py", "def to_legacy_mission_config", "Legacy spelling adapter"),
            ],
        ),
        _component(
            "legacy_rest",
            "Old REST bridge · /c2_node",
            "legacy_fog",
            "gateway",
            "Stateful C++ HTTP-to-ROS bridge. It remembers one current mission id.",
            runtime_name="/c2_node",
            container="c2-imugs2-c2-ros-rest",
            responsibilities=["POST /mission_control", "InitMissionRequest publisher", "Status request publisher"],
            tags=["legacy", "http", "ros2"],
            source_refs=[
                ref(f"{REST}/MissionHandler.cpp", 'action == "initialize"', "Initialize handler"),
                ref(f"{REST}/c2_rest.cpp", 'Node("c2_node")', "ROS node identity"),
            ],
        ),
        _component(
            "rosbridge",
            "rosbridge read gateway",
            "data_observability",
            "gateway",
            "Exposes the ROS graph over WebSocket. The adapter uses it for diagnostics and three live topics.",
            runtime_name="/rosbridge_websocket",
            container="c2-imugs2-rosbridge",
            responsibilities=["ROS graph inspection", "Topic subscriptions", "Read-only event transport"],
            tags=["observability", "websocket", "rosapi"],
            source_refs=[
                ref("src/c2_imugs2/rosbridge.py", "LIVE_TOPICS = (", "Adapter live topic allow-list"),
                ref("docker-compose.backend.yml", "rosbridge_websocket_launch.xml", "Runtime launch"),
            ],
        ),
        _component(
            "c2_interface",
            "C2 Interface · /c2_interface_node",
            "legacy_fog",
            "ros_node",
            "Parses C2 messages, writes shared InterfaceC2State, and directly calls the orchestrator for status changes.",
            runtime_name="/c2_interface_node",
            container="c2-imugs2-centralized-coordination",
            responsibilities=["MissionConfig legacy parse", "C2 topic ingress", "In-process state handoff"],
            tags=["legacy", "ros2", "in-process"],
            source_refs=[ref(f"{CENTRAL}/c2_interface_node.cpp", 'Interface::Interface() : Node("c2_interface_node")', "ROS node identity")],
        ),
        _component(
            "orchestrator",
            "Orchestrator · /orchestrator_node",
            "legacy_fog",
            "ros_node",
            "Polls InterfaceC2State, persists mission configs, and creates one MissionManager node per mission.",
            runtime_name="/orchestrator_node",
            container="c2-imugs2-centralized-coordination",
            responsibilities=["Mission registry", "Dynamic node lifecycle", "Status routing"],
            tags=["legacy", "ros2", "state-machine"],
            source_refs=[ref(f"{CENTRAL}/orchestrator_node.cpp", 'OrchestratorNode::OrchestratorNode() : Node("orchestrator_node")', "ROS node identity")],
        ),
        _component(
            "mission_manager",
            "Mission Manager · /mission_<id>",
            "legacy_fog",
            "dynamic_ros_node",
            "Per-mission state machine. Coordinates planner, fleet, feedback, and persistence.",
            runtime_name="/mission_{mission_id_with_underscores}",
            container="c2-imugs2-centralized-coordination",
            responsibilities=["Mission state machine", "Planner orchestration", "Task dispatch", "Mission feedback"],
            tags=["legacy", "dynamic", "ros2"],
            runtime_status="dynamic",
            source_refs=[
                ref(f"{CENTRAL}/orchestrator_node.cpp", "std::make_shared<MissionManager>", "Dynamic node creation"),
                ref(f"{CENTRAL}/mission_manager.cpp", 'Node("mission_" + mission_id)', "Dynamic ROS node identity"),
            ],
        ),
        _component(
            "planner",
            "Legacy Planner · /planner_node",
            "legacy_fog",
            "ros_node",
            "Builds the road/risk graph, computes paths, caches one current plan, and emits task-plan JSON.",
            runtime_name="/planner_node",
            container="c2-imugs2-planner",
            responsibilities=["Map graph construction", "Allocation and A*", "Task-plan serialization"],
            tags=["legacy", "python", "planning"],
            source_refs=[
                ref(PLANNER, "class PlannerNode(Node):", "Planner implementation"),
                ref(PLANNER, "def path_to_plan_json", "Task-plan serializer"),
            ],
        ),
        _component(
            "fleet_manager",
            "Fleet Manager · /fleet_manager_node",
            "legacy_fog",
            "ros_node",
            "Maintains the agent registry, returns Agent records, reads stored planning, and calls per-agent edge services.",
            runtime_name="/fleet_manager_node",
            container="c2-imugs2-centralized-coordination",
            responsibilities=["Agent registry", "Planning-to-edge dispatch", "Agent updates to planner"],
            tags=["legacy", "ros2", "dispatch"],
            source_refs=[ref(f"{CENTRAL}/fleet_manager_node.cpp", 'FleetManagerNode::FleetManagerNode() : Node("fleet_manager_node")', "ROS node identity")],
        ),
        _component(
            "edge_supervisor",
            "Edge supervisor · /agent_<uuid>",
            "edge_robot",
            "dynamic_ros_node",
            "Per-robot task supervisor. Expands task primitives, commands autonomy, and reports execution state.",
            runtime_name="/agent_f9992bb3_9871_451f_90a0_9207eb9fe6c5",
            container="c2-imugs2-edge-agent-sim-1",
            responsibilities=["Task queue", "Primitive execution", "Autonomy adapter", "Edge feedback"],
            tags=["legacy", "edge", "ros2"],
            source_refs=[
                ref(EDGE, "AgentTaskSupervisorNode::AgentTaskSupervisorNode(std::string node_name) : Node(node_name)", "ROS node construction"),
                ref("backend/config/launch_agent_tasks_supervisor.sh", "swarm_edge_executable agent_$AGENT_ID", "ROS node identity"),
                ref(EDGE, "_addTaskService_callback", "Task ingestion"),
            ],
        ),
        _component(
            "autonomy_sim",
            "Themis Fr autonomy simulator",
            "edge_robot",
            "ros_node",
            "Consumes autonomy objectives, moves a simulated pose, and publishes status and vehicle profile.",
            runtime_name="/autonomy_test_node_Themis_Fr",
            container="c2-imugs2-edge-agent-sim-1",
            responsibilities=["Objective following", "Odometry", "Autonomy status", "Vehicle profile"],
            tags=["legacy", "simulator", "themis-fr"],
            source_refs=[
                ref(AUTONOMY, "Autonomy::Autonomy(std::string node_name) : Node(node_name)", "ROS node construction"),
                ref("backend/config/launch_autonomy_sim.sh", "test_autonomy_sim autonomy_test_node_$AUTONOMY_TOPIC_PREFIX", "ROS node identity"),
            ],
        ),
        _component(
            "mongodb",
            "MongoDB",
            "data_observability",
            "database",
            "Legacy runtime persistence plus the required MapDB.rma planner feature collection.",
            runtime_name="mongodb://127.0.0.1:27017",
            container="c2-imugs2-mongodb",
            responsibilities=["RuntimeDB", "VehicleDB", "Required planner MapDB.rma"],
            tags=["mongodb", "persistence"],
            source_refs=[
                ref("docker-compose.backend.yml", "MONGODB_CONNSTRING:", "Backend DB connection"),
                ref(
                    "backend/fog/centralized-coordination/src/centralized_coordination/include/custom_libraries/mongodb_handler.hpp",
                    'kDatabaseName[] = "RuntimeDB"',
                    "Runtime database",
                ),
            ],
        ),
        _component(
            "map_files",
            "Planner map · MapDB.rma + OSM",
            "data_observability",
            "data_source",
            "MongoDB GeoJSON features used to construct and connect the planner's OSMnx graph. Compose seeds them from the mounted local folder before Planner starts.",
            runtime_name="MapDB.rma",
            container="c2-imugs2-planner",
            responsibilities=["MapDB roads/workspaces", "MapDB risk polygons", "OSM road graph"],
            tags=["mongodb", "geojson", "osmnx", "lon-lat"],
            source_refs=[
                ref("backend/config/config_planner.yaml", "map_feature_collection:", "MapDB collection"),
                ref(PLANNER, "def initialize_map", "Planner map construction"),
            ],
        ),
    ]

    interactions = [
        _interaction(
            "operator_compose",
            "operator",
            "browser_ui",
            "Compose and review mission",
            "ui",
            "Human interaction",
            "Canonical MissionConfig draft and explicit approval authority.",
            ["author", "approve", "start"],
            source_refs=[ref("frontend/src/App.tsx", "canSendMission", "Mission send gate")],
        ),
        _interaction(
            "ui_init_http",
            "browser_ui",
            "fastapi_adapter",
            "Init mission",
            "http",
            "HTTP JSON",
            "The browser sends canonical mission JSON.",
            ["init"],
            interface="POST /api/missions/init",
            contract="Canonical MissionConfig",
            source_refs=[
                ref("frontend/src/api.ts", "export async function initMission", "HTTP caller"),
                ref("src/c2_imugs2/api.py", '@app.post("/api/missions/init")', "HTTP handler"),
            ],
        ),
        _interaction(
            "ui_approve_http",
            "browser_ui",
            "fastapi_adapter",
            "Approve mission",
            "http",
            "HTTP JSON",
            "Route looks mission-specific; the legacy command it becomes is not.",
            ["approve"],
            interface="POST /api/missions/{mission_id}/approve",
            contract="MissionRequest.APPROVE = 1",
            source_refs=[ref("src/c2_imugs2/api.py", '@app.post("/api/missions/{mission_id}/approve")', "Approve handler")],
            notes=["Adapter response ACCEPTED=4 is optimistic until ROS feedback confirms it."],
        ),
        _interaction(
            "ui_start_http",
            "browser_ui",
            "fastapi_adapter",
            "Start mission",
            "http",
            "HTTP JSON",
            "Requests START=2 after the UI sees ACCEPTED.",
            ["start"],
            interface="POST /api/missions/{mission_id}/start",
            contract="MissionRequest.START = 2",
            source_refs=[ref("src/c2_imugs2/api.py", '@app.post("/api/missions/{mission_id}/start")', "Start handler")],
            notes=["UI may enable Start from the adapter's optimistic ACCEPTED state."],
        ),
        _interaction(
            "api_rest_initialize",
            "fastapi_adapter",
            "legacy_rest",
            "Legacy initialize envelope",
            "http",
            "HTTP JSON",
            "Canonical optimization is renamed to optimalization; mission_config becomes a JSON string inside JSON.",
            ["init"],
            interface="POST http://localhost:5001/mission_control",
            contract='{action:"initialize", mission_id, mission_config:"<JSON>"}',
            source_refs=[
                ref("src/c2_imugs2/legacy_rest.py", "def initialize_mission", "Envelope construction"),
                ref(f"{REST}/MissionHandler.cpp", 'action == "initialize"', "Envelope consumption"),
            ],
            notes=["The adapter also inlines runtime feature references and repairs non-UUID mission ids before this boundary."],
        ),
        _interaction(
            "api_rest_status",
            "fastapi_adapter",
            "legacy_rest",
            "Legacy status command",
            "http",
            "HTTP JSON",
            "Sends only requested_state; it does not include the route's mission_id.",
            ["approve", "start"],
            interface="POST http://localhost:5001/mission_control",
            contract='{action:"change_status", requested_state:1|2}',
            source_refs=[
                ref("src/c2_imugs2/legacy_rest.py", "def change_status", "Status envelope"),
                ref(f"{REST}/MissionHandler.cpp", 'action == "change_status"', "Status handler"),
            ],
            notes=["Critical: /c2_node supplies its mutable last-initialized mission id."],
        ),
        _interaction(
            "rest_init_topic",
            "legacy_rest",
            "c2_interface",
            "Initialize mission request",
            "ros_topic",
            "ROS 2 topic",
            "Carries a UUID plus the legacy MissionConfig JSON string.",
            ["init"],
            interface="/multi_robot/mission_init_request",
            contract="c2_msgs/msg/InitMissionRequest",
            fields=_idl_fields(repo_root, f"{CENTRAL_MSGS}/c2_msgs/msg/InitMissionRequest.msg"),
            source_refs=[
                ref(f"{REST}/c2_rest.cpp", '"/multi_robot/mission_init_request"', "Publisher"),
                ref(f"{CENTRAL}/c2_interface_node.cpp", '"/multi_robot/mission_init_request"', "Subscriber"),
            ],
        ),
        _interaction(
            "rest_status_topic",
            "legacy_rest",
            "c2_interface",
            "Mission status request",
            "ros_topic",
            "ROS 2 topic",
            "Adds /c2_node's stored mission UUID to APPROVE=1 or START=2.",
            ["approve", "start"],
            interface="/multi_robot/change_mission_status_request",
            contract="c2_msgs/msg/ChangeMissionStatusRequest",
            fields=_idl_fields(repo_root, f"{CENTRAL_MSGS}/c2_msgs/msg/ChangeMissionStatusRequest.msg"),
            source_refs=[
                ref(f"{REST}/c2_rest.cpp", '"/multi_robot/change_mission_status_request"', "Publisher"),
                ref(f"{CENTRAL}/c2_interface_node.cpp", '"/multi_robot/change_mission_status_request"', "Subscriber"),
            ],
        ),
        _interaction(
            "interface_state",
            "c2_interface",
            "orchestrator",
            "InterfaceC2State handoff",
            "in_process",
            "Shared C++ state + 5 s poll",
            "Init writes flag_new_mission; the orchestrator polls and flushes the shared state.",
            ["init"],
            contract="InterfaceC2State",
            source_refs=[
                ref(f"{CENTRAL}/c2_interface_node.cpp", "flag_new_mission = true", "State write"),
                ref(f"{CENTRAL}/orchestrator_node.cpp", "_updateC2InterfaceState", "State poll"),
            ],
            notes=["This central handoff is not a ROS topic or service."],
        ),
        _interaction(
            "interface_status_call",
            "c2_interface",
            "orchestrator",
            "Direct status method call",
            "in_process",
            "C++ shared pointer",
            "The C2 Interface calls setRequestMissionChangeStatus synchronously.",
            ["approve", "start"],
            contract="setRequestMissionChangeStatus(mission_id, request)",
            source_refs=[ref(f"{CENTRAL}/c2_interface_node.cpp", "setRequestMissionChangeStatus", "Direct method call")],
        ),
        _interaction(
            "orchestrator_create_mission",
            "orchestrator",
            "mission_manager",
            "Create per-mission node",
            "in_process",
            "C++ object + detached ROS spin thread",
            "Creates /mission_<UUID_with_underscores> and waits for its dynamic services.",
            ["init"],
            contract="MissionManager(mission_id, existing_mission)",
            source_refs=[ref(f"{CENTRAL}/orchestrator_node.cpp", "std::make_shared<MissionManager>", "Dynamic node construction")],
        ),
        _interaction(
            "orchestrator_status_service",
            "orchestrator",
            "mission_manager",
            "Change mission status",
            "ros_service",
            "ROS 2 service",
            "Routes the mission request to the matching dynamic MissionManager.",
            ["approve", "start"],
            interface="/multi_robot/mission_{mission_id}/mission_status_change",
            contract="c2_msgs/srv/ChangeMissionStatus",
            request_fields=_idl_section(repo_root, f"{CENTRAL_MSGS}/c2_msgs/srv/ChangeMissionStatus.srv", "request"),
            response_fields=_idl_section(repo_root, f"{CENTRAL_MSGS}/c2_msgs/srv/ChangeMissionStatus.srv", "response"),
            source_refs=[
                ref(f"{CENTRAL}/orchestrator_node.cpp", '"/mission_status_change"', "Client template"),
                ref(f"{CENTRAL}/mission_manager.cpp", '"/mission_status_change"', "Provider template"),
            ],
        ),
        _interaction(
            "mission_get_agents",
            "mission_manager",
            "fleet_manager",
            "Resolve mission agents",
            "ros_service",
            "ROS 2 service",
            "Requests the configured vehicle ids and receives Agent records.",
            ["plan"],
            interface="/multi_robot/fleet_manager/get_agents",
            contract="centralized_msgs/srv/GetAgents",
            request_fields=_idl_section(repo_root, f"{CENTRAL_MSGS}/centralized_msgs/srv/GetAgents.srv", "request"),
            response_fields=_idl_section(repo_root, f"{CENTRAL_MSGS}/centralized_msgs/srv/GetAgents.srv", "response"),
            source_refs=[
                ref(f"{CENTRAL}/mission_manager.cpp", '"multi_robot/fleet_manager/get_agents"', "Client"),
                ref(f"{CENTRAL}/fleet_manager_node.cpp", '"multi_robot/fleet_manager/get_agents"', "Provider"),
            ],
        ),
        _interaction(
            "mission_create_planner",
            "mission_manager",
            "planner",
            "Create planner job",
            "ros_service",
            "ROS 2 service",
            "Sends mission id, priority, selected Agent messages, and legacy config JSON.",
            ["plan"],
            interface="/multi_robot/planner/create",
            contract="centralized_msgs/srv/CreatePlanner",
            request_fields=_idl_section(repo_root, f"{CENTRAL_MSGS}/centralized_msgs/srv/CreatePlanner.srv", "request"),
            response_fields=_idl_section(repo_root, f"{CENTRAL_MSGS}/centralized_msgs/srv/CreatePlanner.srv", "response"),
            source_refs=[
                ref(f"{CENTRAL}/mission_manager.cpp", '"/multi_robot/planner/create"', "Client"),
                ref(PLANNER, "'/multi_robot/planner/create'", "Provider"),
            ],
        ),
        _interaction(
            "fleet_agent_topic",
            "fleet_manager",
            "planner",
            "Live agent record",
            "ros_topic",
            "ROS 2 topic",
            "Planner location is x/y from Agent.odometry; the current sim config uses x=lon, y=lat.",
            ["plan", "execute"],
            interface="/multi_robot/planner/agent",
            contract="centralized_msgs/msg/Agent",
            fields=_idl_fields(repo_root, f"{CENTRAL_MSGS}/centralized_msgs/msg/Agent.msg"),
            source_refs=[
                ref(f"{CENTRAL}/fleet_manager_node.cpp", '"/multi_robot/planner/agent"', "Publisher"),
                ref(PLANNER, "'/multi_robot/planner/agent'", "Subscriber"),
            ],
        ),
        _interaction(
            "planner_map",
            "map_files",
            "planner",
            "Build planning graph",
            "data",
            "MongoDB GeoJSON + OSMnx",
            "Reads MapDB.rma features, builds an OSM road graph around their centroid, and joins graph representations generated from the database features to it.",
            ["plan"],
            contract="GeoJSON coordinates [lon, lat]",
            source_refs=[
                ref("backend/config/config_planner.yaml", "map_feature_collection:", "MapDB feature collection"),
                ref(PLANNER, "def initialize_map", "Graph initialization"),
            ],
            notes=["Compose idempotently seeds the three valid RMA features; CreatePlanner also has a synchronous readiness guard."],
        ),
        _interaction(
            "planner_state",
            "planner",
            "mission_manager",
            "Planner job state 0 → 1 → 2",
            "ros_topic",
            "ROS 2 topic",
            "MissionManager reacts to state=2 by requesting the plan.",
            ["plan", "feedback"],
            interface="/multi_robot/planner/state",
            contract='std_msgs/msg/String · {"planners":[{"mission_id", "state"}]}',
            fields=[{"section": "message", "type": "string", "name": "data"}],
            source_refs=[
                ref(PLANNER, "'/multi_robot/planner/state'", "Publisher"),
                ref(f"{CENTRAL}/mission_manager.cpp", '"/multi_robot/planner/state"', "Subscriber"),
            ],
            notes=["The local timer rejects empty paths before state 2 and publishes state 4 on solver failure; mission feedback remains the execution-facing contract."],
        ),
        _interaction(
            "mission_get_plan",
            "mission_manager",
            "planner",
            "Fetch cached TaskPlan",
            "ros_service",
            "ROS 2 service",
            "Returns the planner's current cached path serialized as task JSON.",
            ["plan"],
            interface="/multi_robot/planner/get_plan",
            contract="centralized_msgs/srv/GetPlan",
            request_fields=_idl_section(repo_root, f"{CENTRAL_MSGS}/centralized_msgs/srv/GetPlan.srv", "request"),
            response_fields=_idl_section(repo_root, f"{CENTRAL_MSGS}/centralized_msgs/srv/GetPlan.srv", "response"),
            source_refs=[
                ref(f"{CENTRAL}/mission_manager.cpp", '"/multi_robot/planner/get_plan"', "Client"),
                ref(PLANNER, "'/multi_robot/planner/get_plan'", "Provider"),
            ],
            notes=["Planner provider ignores request.id and serializes global current_mission_id/current paths."],
        ),
        _interaction(
            "orchestrator_store_config",
            "orchestrator",
            "mongodb",
            "Persist MissionConfig",
            "data",
            "MongoDB write",
            "Stores the legacy MissionConfig used to create/recover MissionManager nodes.",
            ["init"],
            interface="RuntimeDB.MissionConfig",
            contract="Legacy MissionConfig JSON",
            source_refs=[ref(f"{CENTRAL}/orchestrator_node.cpp", "databaseAddMission", "MissionConfig write")],
        ),
        _interaction(
            "mission_store_plan",
            "mission_manager",
            "mongodb",
            "Persist full planner result",
            "data",
            "MongoDB write",
            "Stores the planner TaskPlan before edge dispatch.",
            ["plan", "approve"],
            interface="RuntimeDB.Planning",
            contract="Planner TaskPlan JSON",
            source_refs=[ref(f"{CENTRAL}/mission_manager.cpp", "databaseUpdatePlanning", "Planning write")],
        ),
        _interaction(
            "fleet_read_plan",
            "mongodb",
            "fleet_manager",
            "Read plan for dispatch",
            "data",
            "MongoDB read",
            "Fleet ignores InitMission.mission_config and loads Planning by mission id.",
            ["approve"],
            interface="RuntimeDB.Planning",
            contract="Planner TaskPlan JSON",
            source_refs=[ref(f"{CENTRAL}/fleet_manager_node.cpp", "databaseFindPlanning", "Planning read")],
        ),
        _interaction(
            "mission_send_tasks",
            "mission_manager",
            "fleet_manager",
            "Tell fleet to dispatch tasks",
            "ros_service",
            "ROS 2 service",
            "On APPROVE, sends the mission id; Fleet then reads Planning from MongoDB.",
            ["approve"],
            interface="/multi_robot/fleet_manager/send_tasks",
            contract="c2_msgs/srv/InitMission",
            request_fields=_idl_section(repo_root, f"{CENTRAL_MSGS}/c2_msgs/srv/InitMission.srv", "request"),
            response_fields=_idl_section(repo_root, f"{CENTRAL_MSGS}/c2_msgs/srv/InitMission.srv", "response"),
            source_refs=[
                ref(f"{CENTRAL}/mission_manager.cpp", '"multi_robot/fleet_manager/send_tasks"', "Client"),
                ref(f"{CENTRAL}/fleet_manager_node.cpp", '"multi_robot/fleet_manager/send_tasks"', "Provider"),
            ],
        ),
        _interaction(
            "fleet_add_task",
            "fleet_manager",
            "edge_supervisor",
            "Add planned task",
            "ros_service",
            "ROS 2 dynamic service",
            "Fleet sends each agent's task definition to its edge supervisor.",
            ["approve"],
            interface="/multi_robot/edge/agent_{agent_id}/add_task",
            contract="task_msgs/srv/AddTask",
            request_fields=_idl_section(repo_root, f"{EDGE_MSGS}/task_msgs/srv/AddTask.srv", "request"),
            response_fields=_idl_section(repo_root, f"{EDGE_MSGS}/task_msgs/srv/AddTask.srv", "response"),
            source_refs=[
                ref(f"{CENTRAL}/fleet_manager_node.cpp", '"/add_task"', "Dynamic client"),
                ref(EDGE, '"/add_task"', "Dynamic provider"),
            ],
        ),
        _interaction(
            "mission_change_task",
            "mission_manager",
            "fleet_manager",
            "Request task EXECUTE=1",
            "ros_service",
            "ROS 2 service",
            "On START, MissionManager reuses ChangeMissionStatus with mission_request_status=1 as task EXECUTE.",
            ["start"],
            interface="/multi_robot/fleet_manager/change_mission_status",
            contract="c2_msgs/srv/ChangeMissionStatus · task request EXECUTE=1",
            request_fields=_idl_section(repo_root, f"{CENTRAL_MSGS}/c2_msgs/srv/ChangeMissionStatus.srv", "request"),
            response_fields=_idl_section(repo_root, f"{CENTRAL_MSGS}/c2_msgs/srv/ChangeMissionStatus.srv", "response"),
            source_refs=[
                ref(f"{CENTRAL}/mission_manager.cpp", '"multi_robot/fleet_manager/change_mission_status"', "Client"),
                ref(f"{CENTRAL}/fleet_manager_node.cpp", '"multi_robot/fleet_manager/change_mission_status"', "Provider"),
            ],
        ),
        _interaction(
            "fleet_change_task",
            "fleet_manager",
            "edge_supervisor",
            "Change task state · EXECUTE=1",
            "ros_service",
            "ROS 2 dynamic service",
            "Starts the previously-added task on the target edge supervisor.",
            ["start"],
            interface="/multi_robot/edge/agent_{agent_id}/change_task_state",
            contract="task_msgs/srv/ChangeTaskState",
            request_fields=_idl_section(repo_root, f"{EDGE_MSGS}/task_msgs/srv/ChangeTaskState.srv", "request"),
            response_fields=_idl_section(repo_root, f"{EDGE_MSGS}/task_msgs/srv/ChangeTaskState.srv", "response"),
            source_refs=[
                ref(f"{CENTRAL}/fleet_manager_node.cpp", '"/change_task_state"', "Dynamic client"),
                ref(EDGE, '"/change_task_state"', "Dynamic provider"),
            ],
        ),
        _interaction(
            "edge_objective",
            "edge_supervisor",
            "autonomy_sim",
            "Set autonomy objective",
            "ros_topic",
            "ROS 2 topic",
            "Converts the current waypoint primitive into AutonomySetObjective.",
            ["execute"],
            interface="Themis_Fr/edge/multi_robot/autonomy_set_objective",
            contract="autonomy_msgs/msg/AutonomySetObjective",
            fields=_idl_fields(repo_root, f"{EDGE_MSGS}/autonomy_msgs/msg/AutonomySetObjective.msg"),
            source_refs=[
                ref(EDGE, '"/edge/multi_robot/autonomy_set_objective"', "Publisher"),
                ref(AUTONOMY, '"/edge/multi_robot/autonomy_set_objective"', "Subscriber"),
            ],
        ),
        _interaction(
            "autonomy_localization",
            "autonomy_sim",
            "edge_supervisor",
            "Localization / odometry",
            "ros_topic",
            "ROS 2 topic",
            "The sim publishes pose and twist; coordinate meaning depends on its configured coordinate mode.",
            ["execute", "feedback"],
            interface="Themis_Fr/edge/multi_robot/localization",
            contract="nav_msgs/msg/Odometry",
            source_refs=[
                ref(AUTONOMY, '"/edge/multi_robot/localization"', "Publisher"),
                ref(EDGE, '"/edge/multi_robot/localization"', "Subscriber"),
            ],
        ),
        _interaction(
            "autonomy_status",
            "autonomy_sim",
            "edge_supervisor",
            "Autonomy status",
            "ros_topic",
            "ROS 2 topic",
            "Reports objective UUID, objective status, and primitive statuses.",
            ["execute", "feedback"],
            interface="Themis_Fr/edge/multi_robot/autonomy_status",
            contract="autonomy_msgs/msg/AutonomyStatus",
            fields=_idl_fields(repo_root, f"{EDGE_MSGS}/autonomy_msgs/msg/AutonomyStatus.msg"),
            source_refs=[
                ref(AUTONOMY, '"/edge/multi_robot/autonomy_status"', "Publisher"),
                ref(EDGE, '"/edge/multi_robot/autonomy_status"', "Subscriber"),
            ],
        ),
        _interaction(
            "autonomy_profile",
            "autonomy_sim",
            "edge_supervisor",
            "Vehicle profile",
            "ros_topic",
            "ROS 2 topic",
            "Supplies capabilities and constraints used in the edge's agent profile.",
            ["register", "execute"],
            interface="Themis_Fr/edge/multi_robot/vehicle_profile",
            contract="autonomy_msgs/msg/VehicleProfile",
            fields=_idl_fields(repo_root, f"{EDGE_MSGS}/autonomy_msgs/msg/VehicleProfile.msg"),
            source_refs=[
                ref(AUTONOMY, '"/edge/multi_robot/vehicle_profile"', "Publisher"),
                ref(EDGE, '"/edge/multi_robot/vehicle_profile"', "Subscriber"),
            ],
        ),
        _interaction(
            "edge_profile",
            "edge_supervisor",
            "fleet_manager",
            "Register / update agent",
            "ros_topic",
            "ROS 2 topic",
            "Edge publishes agent profile JSON; Fleet stores it and publishes Agent updates to Planner.",
            ["register", "execute"],
            interface="/multi_robot/edge/agent_profile",
            contract="std_msgs/msg/String · AgentProfile JSON",
            fields=[{"section": "message", "type": "string", "name": "data"}],
            source_refs=[
                ref(EDGE, '"/multi_robot/edge/agent_profile"', "Publisher"),
                ref(f"{CENTRAL}/fleet_manager_node.cpp", '"/multi_robot/edge/agent_profile"', "Subscriber"),
            ],
        ),
        _interaction(
            "edge_feedback_mission",
            "edge_supervisor",
            "mission_manager",
            "Execution feedback",
            "ros_topic",
            "ROS 2 topic",
            "MissionManager trims completed waypoints and moves the mission toward COMPLETED.",
            ["execute", "feedback"],
            interface="/multi_robot/edge/feedback",
            contract="task_msgs/msg/Feedback",
            fields=_idl_fields(repo_root, f"{EDGE_MSGS}/task_msgs/msg/Feedback.msg"),
            source_refs=[
                ref(EDGE, '"/multi_robot/edge/feedback"', "Publisher"),
                ref(f"{CENTRAL}/mission_manager.cpp", '"/multi_robot/edge/feedback"', "Subscriber"),
            ],
        ),
        _interaction(
            "edge_feedback_fleet",
            "edge_supervisor",
            "fleet_manager",
            "Live agent feedback",
            "ros_topic",
            "ROS 2 topic",
            "Fleet refreshes agent state and forwards location to Planner.",
            ["execute", "feedback"],
            interface="/multi_robot/edge/feedback",
            contract="task_msgs/msg/Feedback",
            fields=_idl_fields(repo_root, f"{EDGE_MSGS}/task_msgs/msg/Feedback.msg"),
            source_refs=[
                ref(EDGE, '"/multi_robot/edge/feedback"', "Publisher"),
                ref(f"{CENTRAL}/fleet_manager_node.cpp", '"/multi_robot/edge/feedback"', "Subscriber"),
            ],
        ),
        _interaction(
            "mission_feedback_topic",
            "mission_manager",
            "rosbridge",
            "Mission feedback JSON",
            "ros_topic",
            "ROS 2 topic",
            "Publishes status and at most the first 50 waypoints per task; rosbridge exposes it to the adapter.",
            ["plan", "feedback", "execute", "complete"],
            interface="/multi_robot/mission_feedback",
            contract="c2_msgs/msg/MissionFeedback",
            fields=_idl_fields(repo_root, f"{CENTRAL_MSGS}/c2_msgs/msg/MissionFeedback.msg"),
            source_refs=[
                ref(f"{CENTRAL}/mission_manager.cpp", '"/multi_robot/mission_feedback"', "Publisher"),
                ref("src/c2_imugs2/rosbridge.py", '"/multi_robot/mission_feedback"', "WebSocket subscription"),
            ],
            notes=["MissionFeedback serializes waypoint coordinates as [lat, lng], unlike planner/UI [lon, lat]."],
        ),
        _interaction(
            "planner_state_observe",
            "planner",
            "rosbridge",
            "Observe planner state",
            "ros_topic",
            "ROS 2 topic via rosbridge",
            "Read-side visibility only; it does not command the planner.",
            ["plan", "feedback"],
            interface="/multi_robot/planner/state",
            contract="std_msgs/msg/String",
            fields=[{"section": "message", "type": "string", "name": "data"}],
            source_refs=[
                ref(PLANNER, "'/multi_robot/planner/state'", "Publisher"),
                ref("src/c2_imugs2/rosbridge.py", '"/multi_robot/planner/state"', "WebSocket subscription"),
            ],
        ),
        _interaction(
            "edge_feedback_observe",
            "edge_supervisor",
            "rosbridge",
            "Observe edge feedback",
            "ros_topic",
            "ROS 2 topic via rosbridge",
            "Read-side visibility used to update the adapter's agent state.",
            ["execute", "feedback"],
            interface="/multi_robot/edge/feedback",
            contract="task_msgs/msg/Feedback",
            fields=_idl_fields(repo_root, f"{EDGE_MSGS}/task_msgs/msg/Feedback.msg"),
            source_refs=[
                ref(EDGE, '"/multi_robot/edge/feedback"', "Publisher"),
                ref("src/c2_imugs2/rosbridge.py", '"/multi_robot/edge/feedback"', "WebSocket subscription"),
            ],
        ),
        _interaction(
            "rosbridge_websocket",
            "rosbridge",
            "fastapi_adapter",
            "ROS JSON frames",
            "websocket",
            "rosbridge WebSocket",
            "Adapter subscribes to mission feedback, edge feedback, and planner state.",
            ["plan", "feedback", "execute", "complete"],
            interface="ws://localhost:9090",
            contract="rosbridge publish frames",
            source_refs=[ref("src/c2_imugs2/rosbridge.py", "async def topic_messages", "WebSocket read loop")],
        ),
        _interaction(
            "adapter_sse",
            "fastapi_adapter",
            "browser_ui",
            "Normalized live events",
            "sse",
            "Server-Sent Events",
            "Emits mission.updated, planner.updated, agent.updated, and diagnostics.updated variants.",
            ["plan", "feedback", "execute", "complete"],
            interface="GET /api/events",
            contract="Normalized SSE event variants",
            source_refs=[
                ref("src/c2_imugs2/api.py", '@app.get("/api/events")', "SSE producer"),
                ref("frontend/src/api.ts", "export function createEventSource", "SSE consumer"),
            ],
            notes=["Mission feedback [lat,lng] is swapped back to UI [lon,lat].", "planner.updated and mission.updated each have more than one payload shape."],
        ),
        _interaction(
            "mission_store_feedback",
            "mission_manager",
            "mongodb",
            "Persist feedback snapshot",
            "data",
            "MongoDB write",
            "Stores the same truncated MissionFeedback snapshot that is published.",
            ["plan", "feedback", "execute", "complete"],
            interface="RuntimeDB.MissionFeedback",
            contract="Legacy MissionFeedback JSON",
            source_refs=[ref(f"{CENTRAL}/mission_manager.cpp", "databaseAddMissionFeedback", "Feedback write")],
        ),
        _interaction(
            "mission_status_response",
            "mission_manager",
            "legacy_rest",
            "Status response",
            "ros_topic",
            "ROS 2 topic",
            "MissionManager publishes the actual status response; /c2_node only logs it.",
            ["approve", "start"],
            interface="/multi_robot/change_mission_status_response",
            contract="c2_msgs/msg/ChangeMissionStatusResponse",
            fields=_idl_fields(repo_root, f"{CENTRAL_MSGS}/c2_msgs/msg/ChangeMissionStatusResponse.msg"),
            source_refs=[
                ref(f"{CENTRAL}/mission_manager.cpp", '"/multi_robot/change_mission_status_response"', "Publisher"),
                ref(f"{REST}/c2_rest.cpp", '"/multi_robot/change_mission_status_response"', "Subscriber"),
            ],
        ),
    ]

    gaps = [
        _gap(
            "stateful_rest_target",
            "critical",
            "Approve/start target the last REST-initialized mission",
            "The FastAPI URL contains a mission id, but the legacy status envelope does not. /c2_node injects its one mutable current mission id.",
            [
                ref("src/c2_imugs2/legacy_rest.py", 'requested_state"', "No mission id in status envelope"),
                ref(f"{REST}/c2_rest.cpp", "request.mission_id = convertStringUuidtoRosUuid(this->_mission_id)", "Stored id injection"),
            ],
        ),
        _gap(
            "optimistic_status",
            "high",
            "HTTP success is presented as mission-state confirmation",
            "The adapter sets ACCEPTED/STARTED immediately after old REST returns HTTP 200, before ROS confirms the transition.",
            [
                ref("src/c2_imugs2/api.py", 'mission["status"] = status', "Adapter optimistic state"),
                ref(f"{REST}/MissionHandler.cpp", "sendChangeStatus(requested_state)", "HTTP handler only publishes"),
            ],
        ),
        _gap(
            "planner_singleton",
            "critical",
            "Planner state and GetPlan cache are effectively singleton",
            "current_mission_id, paths, and mission_defined are global; GetPlan ignores request.id when choosing the cached plan.",
            [
                ref(PLANNER, "self.current_mission_id", "Global current mission"),
                ref(PLANNER, "response.plan = plan_json", "GetPlan returns current cache"),
            ],
        ),
        _gap(
            "legacy_empty_task_sentinel",
            "medium",
            "MissionManager's empty-plan sentinel has the wrong JSON shape",
            "Planner now rejects empty paths before state 2, but MissionManager still checks only tasks: []; the protection lives at the planner boundary.",
            [
                ref(PLANNER, 'mission = {"mission_id": mission_id, "tasks": tasks}', "Empty dict is serializable"),
                ref(f"{CENTRAL}/mission_manager.cpp", 'result->plan.find("\\"tasks\\":[]")', "Wrong empty check"),
            ],
        ),
        _gap(
            "partial_schema_validation",
            "high",
            "JSON Schemas are documentation, not the enforced API contract",
            "FastAPI accepts dict[str, Any] and a handwritten subset validator. Several schema constraints and execution invariants are not checked.",
            [
                ref("src/c2_imugs2/api.py", "async def init_mission(mission_config: dict[str, Any])", "Generic request type"),
                ref("src/c2_imugs2/mission_config.py", "def validate_mission_config", "Partial validator"),
            ],
        ),
        _gap(
            "feedback_waypoint_limit",
            "medium",
            "Published/UI paths are capped at 50 waypoints per task",
            "MissionFeedback and RuntimeDB.MissionFeedback contain a display subset; RuntimeDB.Planning may contain the full plan.",
            [ref(f"{CENTRAL}/mission_manager.cpp", "waypoints.size() >50", "Feedback waypoint cap")],
        ),
        _gap(
            "coordinate_roundtrip",
            "medium",
            "Waypoint coordinate order changes twice",
            "Planner/UI use [lon,lat]; MissionFeedback serializes [lat,lng]; the adapter swaps back to [lon,lat].",
            [
                ref(f"{CENTRAL}/mission_manager.cpp", 'params["coordinates"][1]', "Planner to feedback swap"),
                ref("src/c2_imugs2/api.py", "return [lng, lat]", "Feedback to UI swap"),
            ],
        ),
        _gap(
            "declared_unmatched_interfaces",
            "high",
            "Several planner interfaces are declared but unmatched",
            "Orchestrator calls /planner/delete while Planner provides /planner/delete_planner; set_agents and planner_calculated have consumers but no active providers.",
            [
                ref(f"{CENTRAL}/orchestrator_node.cpp", '"multi_robot/planner/delete"', "Unmatched delete client"),
                ref(PLANNER, "'/multi_robot/planner/delete_planner'", "Active delete provider"),
            ],
        ),
        _gap(
            "init_response_unused",
            "medium",
            "Init response is constructed but never published",
            "C2 Interface declares /mission_init_response and creates response objects, but the active callback never calls publish.",
            [
                ref(f"{CENTRAL}/c2_interface_node.cpp", "_init_mission_publisher", "Declared publisher"),
                ref(f"{CENTRAL}/c2_interface_node.cpp", "c2_msgs::msg::InitMissionResponse _response", "Unpublished response"),
            ],
        ),
        _gap(
            "incomplete_legacy_alias_translation",
            "high",
            "Canonical-to-legacy translation is incomplete",
            "The boundary translates optimization only; several normalized coverage/formation names differ from fields the old parser expects.",
            [
                ref("src/c2_imugs2/legacy_rest.py", "if isinstance(transit, dict) and", "Only optimization is translated"),
                ref("src/c2_imugs2/mission_config.py", '"maximum_coverage_distances"', "Other canonical aliases"),
            ],
        ),
    ]

    workflow = _workflow(repo_root, ref)
    for component in components:
        component["runtime_status"] = component.get("runtime_status") or _runtime_status(
            component.get("runtime_name"), runtime, component["kind"]
        )
    for interaction in interactions:
        interaction["runtime_status"] = _runtime_status(interaction.get("interface"), runtime, interaction["channel"])

    source_refs = _collect_source_refs(components, interactions, gaps, workflow)
    unresolved = [item for item in source_refs if not item.get("resolved")]
    runtime_checked = bool(runtime.get("nodes") or runtime.get("topics") or runtime.get("services"))
    return {
        "title": "Legacy Mission System Atlas",
        "scope": "Active Dockerized mission path from operator command through planning, edge execution, and normalized UI feedback.",
        "verification": {
            "status": "source_verified" if not unresolved else "source_gaps",
            "method": "Curated against active Docker Compose commands, runnable node source, embedded ROS IDL, adapter code, and frontend callers. Test/backup sources are excluded.",
            "source_evidence_count": len(source_refs) - len(unresolved),
            "runtime_status": "runtime_observed" if runtime_checked else "not_connected",
            "caveats": [
                "Static source verification is complete for this path; the legacy containers were not running during this audit.",
                "Runtime name presence, when available, proves visibility only—not matching types, endpoints, QoS, or payload correctness.",
                "The broad generated node/edge catalog remains discovery evidence; this curated atlas is the authoritative visualization.",
            ],
        },
        "zones": [
            _zone("operator_ui", "Operator + UI", "CANONICAL", "Mission intent, review, and the browser's canonical JSON boundary.", "blue", 0),
            _zone("adapter", "Compatibility adapter", "REPLACEMENT", "Stable API, legacy translation, and normalized read-side events.", "cyan", 1),
            _zone("legacy_fog", "Legacy fog / control plane", "ACTUAL ROS 2", "C2 ingress, lifecycle, planner, fleet, and per-mission orchestration.", "amber", 2),
            _zone("edge_robot", "Edge + robot", "PER VEHICLE", "Task supervision and autonomy execution for Themis Fr.", "emerald", 3),
            _zone("data_observability", "Data + observability", "SUPPORTING PLANE", "MongoDB, maps, rosbridge, and read-only feedback transport.", "slate", 4),
        ],
        "components": components,
        "interactions": interactions,
        "workflow": workflow,
        "contract_gaps": gaps,
    }


def _workflow(repo_root: Path, ref: Any) -> dict[str, Any]:
    canonical_config = {
        "mission_id": MISSION_ID,
        "behavior": 0,
        "vehicles": [AGENT_ID],
        "transit": {
            "optimization": {"road_usage": 1.0, "energy": 0.8},
            "desired_vehicle_constraints": {"max_speed": 4.0},
        },
        "objective": {
            "geometries": [
                {"geometry": {"geometry_type": "Point", "coordinates": OBJECTIVE}}
            ]
        },
    }
    legacy_config = {
        **canonical_config,
        "transit": {
            "optimalization": {"road_usage": 1.0, "energy": 0.8},
            "desired_vehicle_constraints": {"max_speed": 4.0},
        },
    }
    planner_task = {
        "mission_id": MISSION_ID,
        "tasks": {
            AGENT_ID: {
                "task_id": "<uuid>",
                "primitives": [{"primitive_type": "waypoint"}],
                "objectives": [
                    {
                        "objective_type": "combined_primitives",
                        "primitives": [
                            {
                                "parameters": {
                                    "coordinates": "<nearest graph-node [lon,lat]>",
                                    "speed": 4.0,
                                    "max_speed": 4.0,
                                }
                            }
                        ],
                    }
                ],
            }
        },
    }
    normalized_feedback = {
        "mission_id": MISSION_ID,
        "status": 1,
        "status_name": "PLANNED",
        "path_status": "received",
        "planned_paths": {AGENT_ID: ["<nearest start graph-node>", "<nearest destination graph-node>"]},
    }
    steps = [
        _step(
            1,
            "author",
            "Author a canonical NAVIGATE mission",
            "The operator chooses Themis Fr and a Point objective. Browser coordinates are [lon, lat].",
            "author",
            ["operator", "browser_ui"],
            ["operator_compose"],
            output=canonical_config,
            transformations=["Draft aliases are normalized in the browser.", "Client validation gates Init."],
            source_refs=[ref("frontend/src/mission.ts", "export function normalizeMission", "Browser normalizer")],
        ),
        _step(
            2,
            "post_init",
            "POST canonical JSON to the adapter",
            "The UI calls the stable mission-init endpoint; it never constructs a ROS message.",
            "init",
            ["browser_ui", "fastapi_adapter"],
            ["ui_init_http"],
            input=canonical_config,
            output={"http": "POST /api/missions/init", "content_type": "application/json"},
            source_refs=[ref("frontend/src/api.ts", "export async function initMission", "UI caller")],
        ),
        _step(
            3,
            "adapter_boundary",
            "Normalize, validate, inline, and repair",
            "Backend normalization adds aliases the browser lacks, inlines runtime feature refs, and replaces a non-UUID mission id.",
            "init",
            ["fastapi_adapter"],
            ["ui_init_http", "api_rest_initialize"],
            input=canonical_config,
            output={"canonical_validated": True, "runtime_feature_refs": "inline geometry", "mission_id": MISSION_ID},
            transformations=["Partial handwritten validation—not full JSON Schema validation.", "Runtime feature lookup currently defaults to map rma."],
            source_refs=[
                ref("src/c2_imugs2/api.py", "normalized = _inline_user_feature_refs", "Runtime geometry inlining"),
                ref("src/c2_imugs2/api.py", 'normalized["mission_id"] = _legacy_uuid', "UUID repair"),
            ],
        ),
        _step(
            4,
            "legacy_envelope",
            "Translate and double-encode the legacy envelope",
            "optimization becomes optimalization and the inner mission becomes a JSON string.",
            "init",
            ["fastapi_adapter", "legacy_rest"],
            ["api_rest_initialize"],
            input=canonical_config,
            output={"action": "initialize", "mission_id": MISSION_ID, "mission_config": legacy_config},
            transformations=["transit.optimization → transit.optimalization", "MissionConfig object → JSON string inside HTTP JSON"],
            source_refs=[ref("src/c2_imugs2/legacy_rest.py", "legacy_config = to_legacy_mission_config", "Legacy envelope")],
        ),
        _step(
            5,
            "ros_init",
            "/c2_node publishes InitMissionRequest",
            "The bridge stores this mission as its one current mission and publishes UUID + bounded JSON string.",
            "init",
            ["legacy_rest", "c2_interface"],
            ["rest_init_topic"],
            input={"action": "initialize", "mission_id": MISSION_ID},
            output={"mission_id": "unique_identifier_msgs/UUID", "mission_config": "<legacy JSON string>"},
            source_refs=[ref(f"{REST}/c2_rest.cpp", "void C2::sendInitMission", "ROS init publisher")],
        ),
        _step(
            6,
            "interface_state",
            "C2 Interface writes in-process state",
            "It parses the legacy JSON and sets flag_new_mission. No ROS link exists between Interface and Orchestrator.",
            "init",
            ["c2_interface", "orchestrator"],
            ["interface_state"],
            input={"mission_config": "<legacy JSON string>"},
            output={"InterfaceC2State": {"flag_new_mission": True, "mission_id": MISSION_ID}},
            transformations=["ROS UUID overwrites MissionConfig.MissionId.", "Legacy generated parser converts JSON into C++ fields."],
            source_refs=[ref(f"{CENTRAL}/c2_interface_node.cpp", "flag_new_mission = true", "Shared state write")],
        ),
        _step(
            7,
            "create_manager",
            "Persist config and create /mission_<id>",
            "The 5-second orchestrator loop reads the flag, stores RuntimeDB.MissionConfig, and starts a dynamic MissionManager.",
            "init",
            ["orchestrator", "mission_manager", "mongodb"],
            ["orchestrator_store_config", "orchestrator_create_mission"],
            output={"mongo": "RuntimeDB.MissionConfig", "node": f"/mission_{MISSION_ID.replace('-', '_')}"},
            source_refs=[ref(f"{CENTRAL}/orchestrator_node.cpp", "void OrchestratorNode::_addMission", "Mission registration")],
        ),
        _step(
            8,
            "resolve_agents",
            "Resolve the configured vehicle",
            "MissionManager asks Fleet for Themis Fr and receives Agent profile + Odometry.",
            "plan",
            ["mission_manager", "fleet_manager"],
            ["mission_get_agents"],
            input={"agent_id_list": [AGENT_ID]},
            output={"agents": [{"agent_id": AGENT_ID, "agent_profile": "<JSON>", "odometry": "<nav_msgs/Odometry>"}]},
            source_refs=[ref(f"{CENTRAL}/mission_manager.cpp", "get_agents_request->agent_id_list", "Agent request")],
        ),
        _step(
            9,
            "plan",
            "Create the planner and calculate a route",
            "Compose seeds MapDB.rma first. Planner's timer or synchronous CreatePlanner guard combines cached live Agent state, legacy mission JSON, MapDB features, and the OSMnx graph.",
            "plan",
            ["mission_manager", "fleet_manager", "planner", "map_files"],
            ["mission_create_planner", "fleet_agent_topic", "planner_map"],
            input={"id": MISSION_ID, "agents": [AGENT_ID], "config": "<legacy JSON>"},
            output={"success": {"planner_state": 2, "cached_paths": {AGENT_ID: "nearest graph-node path"}}, "failure": {"planner_state": 4, "cached_paths": {}}},
            transformations=["Success: 0 initialized → 1 planning → 2 planned; failure: state 4 without node termination.", "Both endpoints snap to graph nodes; road_usage is ignored; risk edges cost 100x."],
            source_refs=[ref(PLANNER, "new_paths = self.mr_path_planner.solve_mission", "Path solve")],
            notes=["No matching live agent remains in state 1; later steps require a non-empty robot-keyed plan."],
        ),
        _step(
            10,
            "collect_plan",
            "Fetch and publish the planned path",
            "MissionManager fetches TaskPlan JSON, stores the full plan, then publishes a 50-waypoint-capped MissionFeedback view.",
            "plan",
            ["planner", "mission_manager", "mongodb", "rosbridge", "fastapi_adapter", "browser_ui"],
            ["planner_state", "mission_get_plan", "mission_store_plan", "mission_feedback_topic", "rosbridge_websocket", "adapter_sse"],
            input=planner_task,
            output=normalized_feedback,
            transformations=["TaskPlan [lon,lat] → MissionFeedback [lat,lng].", "Adapter swaps feedback back to [lon,lat].", "Non-empty Waypoints set path_status=received."],
            source_refs=[
                ref(PLANNER, "def path_to_plan_json", "TaskPlan construction"),
                ref("src/c2_imugs2/api.py", "path_status = ", "Path availability"),
            ],
        ),
        _step(
            11,
            "approve",
            "APPROVE dispatches AddTask",
            "The apparent mission-specific URL collapses to a stateful legacy status command. ACCEPTED causes Fleet to load Planning and send AddTask.",
            "approve",
            ["operator", "browser_ui", "fastapi_adapter", "legacy_rest", "c2_interface", "orchestrator", "mission_manager", "fleet_manager", "edge_supervisor"],
            ["operator_compose", "ui_approve_http", "api_rest_status", "rest_status_topic", "interface_status_call", "orchestrator_status_service", "mission_send_tasks", "fleet_read_plan", "fleet_add_task"],
            input={"http": f"POST /api/missions/{MISSION_ID}/approve"},
            output={"legacy": {"action": "change_status", "requested_state": 1}, "edge": "AddTask"},
            transformations=["APPROVE request 1 → MissionStatus ACCEPTED 4.", "HTTP 200 is not ROS confirmation."],
            source_refs=[ref(f"{CENTRAL}/mission_manager.cpp", "case (int) MissionStatusRequest::APPROVE", "Approve transition")],
            notes=["Critical targeting hazard: legacy envelope contains no mission id."],
        ),
        _step(
            12,
            "start",
            "START sends task EXECUTE=1",
            "STARTED causes MissionManager → Fleet → edge ChangeTaskState.",
            "start",
            ["operator", "browser_ui", "fastapi_adapter", "legacy_rest", "c2_interface", "orchestrator", "mission_manager", "fleet_manager", "edge_supervisor"],
            ["operator_compose", "ui_start_http", "api_rest_status", "rest_status_topic", "interface_status_call", "orchestrator_status_service", "mission_change_task", "fleet_change_task"],
            input={"http": f"POST /api/missions/{MISSION_ID}/start"},
            output={"legacy_request": 2, "mission_status": 5, "task_request": 1},
            transformations=["Mission START=2 → MissionStatus STARTED=5.", "Task request EXECUTE=1 is a different enum using the same field."],
            source_refs=[ref(f"{CENTRAL}/mission_manager.cpp", "case (int) MissionStatusRequest::START", "Start transition")],
        ),
        _step(
            13,
            "objective",
            "Edge emits AutonomySetObjective",
            "The edge turns the active waypoint primitive into the autonomy contract for Themis Fr.",
            "execute",
            ["edge_supervisor", "autonomy_sim"],
            ["edge_objective"],
            input={"primitive_type": "waypoint", "coordinates": OBJECTIVE, "speed": 4.0},
            output={"topic": "Themis_Fr/edge/multi_robot/autonomy_set_objective", "objective": OBJECTIVE},
            transformations=["Task primitive parameters → AutonomyObjective."],
            source_refs=[ref(EDGE, "_set_objective_publisher_callback", "Objective publication")],
        ),
        _step(
            14,
            "robot_feedback",
            "Autonomy moves; edge reports execution",
            "The simulator publishes Odometry and AutonomyStatus. Edge converts them into task Feedback for both MissionManager and Fleet.",
            "execute",
            ["autonomy_sim", "edge_supervisor", "mission_manager", "fleet_manager"],
            ["autonomy_localization", "autonomy_status", "autonomy_profile", "edge_feedback_mission", "edge_feedback_fleet"],
            input={"objective": OBJECTIVE},
            output={"edge_feedback": {"agent_id": AGENT_ID, "state": "<uint8>", "tasks": "<TaskFeedback[]>", "odometry": "<Odometry>"}},
            transformations=["Autonomy state → primitive/task completion.", "Fleet republishes live Agent state to Planner."],
            source_refs=[ref(AUTONOMY, "void Autonomy::_localization_publisher_callback", "Sim localization")],
        ),
        _step(
            15,
            "complete",
            "Feedback closes the loop in the UI",
            "MissionManager removes completed waypoints, persists/publishes MissionFeedback, and eventually sets COMPLETED. Adapter emits normalized SSE.",
            "complete",
            ["mission_manager", "mongodb", "rosbridge", "fastapi_adapter", "browser_ui", "operator"],
            ["mission_store_feedback", "mission_feedback_topic", "rosbridge_websocket", "adapter_sse"],
            input={"MissionFeedback": {"Status": 10, "Tasks": []}},
            output={"sse": "mission.updated", "status": "COMPLETED", "path_status": "received or prior path retained"},
            transformations=["Legacy MissionFeedback JSON → normalized mission.updated.", "UI status and displayed path remain separate concepts."],
            source_refs=[ref(f"{CENTRAL}/mission_manager.cpp", "_mission_feedback_publisher->publish", "Mission feedback publish")],
        ),
    ]
    return {
        "id": "themis_navigate_lifecycle",
        "label": "Themis Fr NAVIGATE · verified seeded execution",
        "summary": "The verified path seeds MapDB.rma, creates a 10-waypoint Themis route, and continues through dispatch, execution, and feedback.",
        "example": {
            "mission_id": MISSION_ID,
            "agent_id": AGENT_ID,
            "agent_name": "Themis Fr",
            "behavior": "NAVIGATE = 0",
            "start_lon_lat": START,
            "objective_lon_lat": OBJECTIVE,
        },
        "steps": steps,
    }


def _component(
    component_id: str,
    label: str,
    zone: str,
    kind: str,
    description: str,
    *,
    responsibilities: list[str],
    tags: list[str],
    source_refs: list[dict[str, Any]],
    runtime_name: str | None = None,
    container: str | None = None,
    runtime_status: str | None = None,
) -> dict[str, Any]:
    return {
        "id": component_id,
        "label": label,
        "short_label": label.split(" · ", 1)[0],
        "zone": zone,
        "kind": kind,
        "description": description,
        "runtime_name": runtime_name,
        "container": container,
        "responsibilities": responsibilities,
        "tags": tags,
        "source_refs": source_refs,
        **({"runtime_status": runtime_status} if runtime_status else {}),
    }


def _interaction(
    interaction_id: str,
    source: str,
    target: str,
    label: str,
    channel: str,
    protocol: str,
    description: str,
    phases: list[str],
    *,
    interface: str | None = None,
    contract: str | None = None,
    fields: list[dict[str, str]] | None = None,
    request_fields: list[dict[str, str]] | None = None,
    response_fields: list[dict[str, str]] | None = None,
    source_refs: list[dict[str, Any]],
    notes: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": interaction_id,
        "source": source,
        "target": target,
        "label": label,
        "channel": channel,
        "protocol": protocol,
        "interface": interface,
        "contract": contract,
        "direction": f"{source} → {target}",
        "description": description,
        "phases": phases,
        "fields": fields or [],
        "request_fields": request_fields or [],
        "response_fields": response_fields or [],
        "source_refs": source_refs,
        "notes": notes or [],
    }


def _step(
    number: int,
    step_id: str,
    title: str,
    summary: str,
    phase: str,
    actor_ids: list[str],
    interaction_ids: list[str],
    *,
    input: Any = None,
    output: Any = None,
    transformations: list[str] | None = None,
    source_refs: list[dict[str, Any]],
    notes: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": step_id,
        "number": number,
        "title": title,
        "summary": summary,
        "phase": phase,
        "actor_ids": actor_ids,
        "interaction_ids": interaction_ids,
        "input": input,
        "output": output,
        "transformations": transformations or [],
        "source_refs": source_refs,
        "notes": notes or [],
    }


def _gap(
    gap_id: str,
    severity: str,
    title: str,
    description: str,
    source_refs: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "id": gap_id,
        "severity": severity,
        "title": title,
        "description": description,
        "source_refs": source_refs,
    }


def _zone(zone_id: str, label: str, eyebrow: str, description: str, tone: str, order: int) -> dict[str, Any]:
    return {
        "id": zone_id,
        "label": label,
        "eyebrow": eyebrow,
        "description": description,
        "tone": tone,
        "order": order,
    }


def _evidence(repo_root: Path, relative_path: str, needle: str, claim: str = "") -> dict[str, Any]:
    path = repo_root / relative_path
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        text = ""
    index = text.find(needle)
    resolved = index >= 0
    line = text[:index].count("\n") + 1 if resolved else 1
    return {
        "path": relative_path,
        "line": line,
        "symbol": needle,
        "claim": claim,
        "verification": "source" if resolved else "documented",
        "resolved": resolved,
    }


def _idl_fields(repo_root: Path, relative_path: str) -> list[dict[str, str]]:
    path = repo_root / relative_path
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    section = "request" if path.suffix == ".srv" else "message"
    fields: list[dict[str, str]] = []
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if line == "---":
            section = "response"
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        fields.append({"section": section, "type": parts[0], "name": parts[1]})
    return fields


def _idl_section(repo_root: Path, relative_path: str, section: str) -> list[dict[str, str]]:
    return [field for field in _idl_fields(repo_root, relative_path) if field["section"] == section]


def _runtime_status(name: str | None, runtime: dict[str, Any], kind: str) -> str:
    if not name:
        return "not_checked"
    values: list[str]
    if kind == "ros_topic":
        values = [str(value) for value in runtime.get("topics", [])]
    elif kind == "ros_service":
        values = [str(value) for value in runtime.get("services", [])]
    elif kind in {"ros_node", "dynamic_ros_node"} or (kind == "gateway" and name.startswith("/")):
        values = [str(value) for value in runtime.get("nodes", [])]
    else:
        return "not_checked"
    if not values:
        return "not_checked"
    canonical = name if name.startswith("/") else f"/{name}"
    if "{" in canonical:
        prefix = canonical.split("{", 1)[0]
        return "visible" if any(value.startswith(prefix) for value in values) else "not_seen"
    return "visible" if canonical in values else "not_seen"


def _collect_source_refs(*payloads: Any) -> list[dict[str, Any]]:
    refs: dict[tuple[str, int, str], dict[str, Any]] = {}

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            if "path" in value and "line" in value and "verification" in value:
                key = (str(value["path"]), int(value["line"]), str(value.get("symbol", "")))
                refs[key] = value
                return
            for nested in value.values():
                visit(nested)
        elif isinstance(value, list):
            for nested in value:
                visit(nested)

    for payload in payloads:
        visit(payload)
    return list(refs.values())
