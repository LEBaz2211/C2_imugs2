# Legacy ROS Mission Flow Diagram

## System View

```mermaid
flowchart LR
  UI[UI / Operator] -->|HTTP POST| REST[c2-ros-rest<br/>/c2_node]
  UI -->|optional read via WebSocket 9090| RB[rosbridge_websocket]

  REST -->|/multi_robot/mission_init_request| C2I[c2_interface_node<br/>Interface]
  REST -->|/multi_robot/change_mission_status_request| C2I

  C2I -->|flag_new_mission| ORCH[orchestrator_node<br/>OrchestratorNode]
  ORCH -->|creates per mission| MM[mission_<mission_id><br/>MissionManager]

  MM -->|get agents| FM[fleet_manager_node<br/>FleetManagerNode]
  FM -->|Agent msg| PLANNER[planner_node<br/>PlannerNode]
  MM -->|create/get plan| PLANNER
  PLANNER -->|task_plan JSON| MM

  MM -->|send tasks / task state| FM
  FM -->|AddTask / ChangeTaskState| EDGE[agent_<uuid><br/>AgentTaskSupervisorNode]

  EDGE -->|AutonomySetObjective| AUTO[autonomy_test_node_Themis_Fr<br/>Autonomy sim]
  AUTO -->|localization / status / profile| EDGE
  EDGE -->|edge feedback / agent profile| FM
  EDGE -->|edge feedback| MM

  MM -->|/multi_robot/mission_feedback| UI
  RB -->|exposes ROS graph| UI
```

## Mission Sequence

```mermaid
sequenceDiagram
  participant UI as UI / Operator
  participant REST as c2_node<br/>C2
  participant C2I as c2_interface_node<br/>Interface
  participant ORCH as orchestrator_node
  participant MM as mission_<id><br/>MissionManager
  participant FM as fleet_manager_node
  participant PL as planner_node
  participant EDGE as agent_<uuid>
  participant AUTO as autonomy_test_node

  UI->>REST: POST /mission_control initialize
  REST->>REST: C2::setMissionConfig()
  REST->>C2I: C2::sendInitMission()<br/>/multi_robot/mission_init_request
  C2I->>C2I: Interface::_initMissionCallback()
  C2I->>ORCH: stores flag_new_mission

  ORCH->>ORCH: OrchestratorNode::_TimerLoop()
  ORCH->>MM: OrchestratorNode::_addMission()
  MM->>MM: MissionManager::_stateMachineCallback()

  MM->>FM: MissionManager::_createPlanner()<br/>multi_robot/fleet_manager/get_agents
  FM->>MM: FleetManagerNode::GetAgents_callback()
  MM->>PL: /multi_robot/planner/create
  PL->>PL: PlannerNode.set_mission_service_callback()
  PL->>PL: PlannerNode.planning_timer_callback()
  PL->>MM: /multi_robot/planner/state = planned
  MM->>PL: MissionManager::_requestPlanning()<br/>/multi_robot/planner/get_plan
  PL->>MM: PlannerNode.get_plan_service_callback()<br/>task_plan JSON
  MM->>MM: MissionManager::_register_planning_result()

  UI->>REST: POST /mission_control change_status APPROVE
  REST->>C2I: /multi_robot/change_mission_status_request
  C2I->>MM: MissionManager::_changeMissionStatus_callback()
  MM->>FM: MissionManager::_sendAgentTasks()
  FM->>EDGE: FleetManagerNode::_sendAgentTask()<br/>AddTask
  EDGE->>EDGE: AgentTaskSupervisorNode::_addTaskService_callback()

  UI->>REST: POST /mission_control change_status START
  REST->>C2I: /multi_robot/change_mission_status_request
  C2I->>MM: MissionManager::_changeMissionStatus_callback()
  MM->>FM: MissionManager::_changeAgentTaskStatuses(1)
  FM->>EDGE: FleetManagerNode::_changeAgentTaskStatus()<br/>ChangeTaskState EXECUTE
  EDGE->>AUTO: AgentTaskSupervisorNode::_set_objective_publisher_callback()
  AUTO->>AUTO: Autonomy::_motion_control_callback()
  AUTO->>EDGE: localization / autonomy_status
  EDGE->>MM: AgentTaskSupervisorNode::_feedback_publisher_callback()
  MM->>UI: MissionManager::_publishMissionFeedback()
```

## Read This First

If you only remember one thing:

```text
UI -> C2 REST -> C2 Interface -> Orchestrator -> Mission Manager -> Planner
   -> Fleet Manager -> Edge Agent -> Autonomy Sim -> Feedback back up
```

`rosbridge` is only a WebSocket gateway for browser/debug access to ROS. It is not the mission brain.
