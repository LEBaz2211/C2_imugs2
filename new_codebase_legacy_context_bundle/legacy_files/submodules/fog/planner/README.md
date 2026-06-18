# planner


## Publish   

- /multi_robot/planner/state
    - message: `std_msgs.msg.String (PlannerState interface)`
    - info: state of the full service incl. planners
    - example: 
          `{"state": 1, "planners": [{"state": 1, "created": "2022-02-16T13:02:58.157897", "calculate": "2022-02-16T13:03:19.612051"}]}`

- /multi_robot/planner/global_calculated
    - message: `std_msgs.msg.String (Plan interface)`
    - info: Global plan with tasks for each agent in the same region. This is a combined plan.

- /multi_robot/planner/planner_calculated
    - message: `centralized_msgs.msg.PlanCalculated`
    - info: Planner plan with tasks for each agent used in the planner.

## Subscribe
 - /multi_robot/planner/agent
     - message: `centralized_msgs.msg.Agent`
     - info: localization update of an agent

## Services 
- /multi_robot/planner/create
   - message: `centralized_msgs.srv.CreatePlanner`
   - request:
        - id: string = id of the planner
        - priority: uint8 = priority of the planner
        - agents: Agent[] = list of agent for the planner
        - config: string = json string with the planning config
   - response:
        - id: string = id of the planner 
        - state: uint8 = state of the planner

- /multi_robot/planner/set_agents
   - message: `centralized_msgs.srv.UpdatePlannerAgents`
   - request:
        - id: string = id of the planner
        - agents: Agent[] = list of agent for the planner
   - response:
        - id: string = id of the planner 

- /multi_robot/planner/set_priority
   - message: `centralized_msgs.srv.UpdatePlannerPriority`
   - request:
        - id: string = id of the planner
        - priority: uint8 = priority of the planner
   - response:
        - id: string = id of the planner 

- /multi_robot/planner/delete
   - message: `centralized_msgs.srv.DeletePlanner`
   - request:
        - id: string = id of the planner
   - response:
        - id: string = id of the planner 
        - state: uint8 = state of the planner

- /multi_robot/planner/get_plan
   - message: `centralized_msgs.srv.GetPlan`
   - request:
        - id: string = id of the planner
   - response:
        - id = id of the planner 
        - plan = json string with the calculated plan

### Interfaces
```   
export interface PlannerState {
     state: ServiceState,
     planners: [{
          state: PlannerState,
          created: Date,
          calculate: Date?
     }]
}

export interface Plan {
     status: PlanState,
     from: Date, // calculate from date
     to: Date, // calculate to date
     tasks:[{
          agent_id: string,
          std: Date,
          waypoints:[{
               position: [],
               speed: float,
               yaw: float,
               eta: Date
               tags: {} // tags can contain for example the planner_id who has calculated this waypoint for the agent
          }]
     }]
}

export enum PlanStatus{
    NONE = 0,
    PLANNED = 1,
    PLAN_FAILED = 3
}

export enum ServiceState{
     NORMAL = 1
     ERROR = 3
}

export enum PlannerState{
     NORMAL = 1
     CALCULATING = 2
     ERROR = 3
}

```
