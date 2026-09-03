# ICD Mission Examples

> **Documentation label: CURRENT**
> Describes the executable example templates and their current planner/edge
> interpretation. Verify volatile details against source, tests, and the
> running editable backend.

## Purpose

The examples in `fixtures/mission_examples/` are loaded by
`GET /api/mission-examples` and shown in the UI's new-mission flow. They make
the original Mission Config ICD concepts easy to select and edit. They do not
create, launch, or bundle a world. Their geometry is inline and uses the RMA
area; it is not automatically reprojected to an unrelated world.

When an operator chooses an example, the UI:

1. assigns a fresh mission UUID;
2. treats the example vehicle IDs as ordered template slots;
3. filters active-world vehicles by every declared `required_capabilities`
   value and comparable requested vehicle limit, then, when enough match,
   replaces the slots in displayed order; and
4. otherwise warns and leaves the template IDs for the operator to resolve.

Always inspect and edit the resulting JSON before Init. Template coordinates
must fall on or connect safely to the routing graph in the world you launched.
The requested capabilities and constraints must match its vehicle profiles.
Inline mission geometry supplies destinations and task regions; it does not
add roads or free-space topology to the world graph. In particular, a mission
LineString is not a replacement for a launched road feature.

For a useful test world, provide robot start positions, a connected road or
workspace/geofence-derived free-space graph spanning the selected template,
and any risk polygons you intend the planner to avoid. Use the exact
capability labels requested by the template. Coverage vehicles need a positive
`constraints.coverage_width_m` unless the mission itself specifies
`objective.coverage_swath_widths`. The planner routes robots from their
launched positions to `start.geometry` as a staging waypoint (using the start
or transit formation when declared) before continuing; it never teleports
them.

## Templates And Prerequisites

| UI template | Vehicles | Planner interpretation | World/profile prerequisites |
| --- | ---: | --- | --- |
| ICD 1 — road navigation and Vee deployment | 3 | Navigate to a Polygon deployment area, then place the vehicles in a Vee with final headings. `maximize_coverage` spreads the deployment; it is not a sweep. | Connected route/free space at the inline geometry and geofence, a road-capable graph for strict `road_usage=1`, and vehicles that can meet the requested speed. |
| ICD 2.1 — goods pickup | 4 | Allocate MultiPoint pickup locations, route each vehicle, and record the pickup payload state at task completion. | Four cargo-capable vehicles and connected routes to every point. |
| ICD 2.2 — concealed goods delivery | 4 | Allocate delivery points, use the visibility/road cost preferences, and record dropoff at completion. | Four cargo-capable vehicles whose declared constraints support the requested limits. |
| ICD 3.1 — screen mission area | 4 | Deploy vehicles in the requested standoff band around the mission-area Polygon with threat-relative headings. | Four camera-capable vehicles and connected free space around the inline mission area. |
| ICD 3.2 — closest-vehicle CASEVAC pickup | 4 candidates | Allocate the casualty point to the closest selected candidate, orient relative to the threat, then record pickup. | Every selected candidate must advertise `casualty_transport` under the current preflight; reduce the selected list to eligible candidates if needed. The world needs a route to the inline pickup. |
| ICD 3.3 — CASEVAC to safe location | 1 | Route the chosen casualty vehicle to the safe point under requested mobility/cost limits, then record dropoff. | A casualty-transport vehicle already representing the intended carrier, a safe destination, and a profile supporting every requested limit. |
| ICD 4 — ordered communication relay | 4 | Place vehicles in listed order along a LineString while honoring endpoint tolerance and maximum separation. | Four radio-relay-capable vehicles, connected access to placements, and a line short enough for `(vehicle_count - 1) * maximum_separation + 2 * endpoint_tolerance`. |
| ICD 5 — multi-vehicle reconnaissance sweep | 4 | Coverage behavior over a Polygon: generate risk-aware lawnmower lanes and divide them among vehicles. | Four camera-capable vehicles, a valid coverage Polygon, connected access to it, and a positive `coverage_width_m` for every selected vehicle unless explicit swaths are supplied. |
| ICD 6 — patrol roads inside mission area | 4 | Coverage behavior plus `road_usage=1`: patrol eligible active-world road edges inside the Polygon. | A Polygon containing a non-empty connected road subgraph and connected routes from vehicle starts. No sensor swath is needed. |
| ICD 7 — threat-relative ballistic protection line | 6 | Deploy a line at the requested standoff from the protected point and orient it relative to the threat. | Six ballistic-protection-capable vehicles and connected deployment space around the inline protected/threat geometry. |

Examples with historical 1991 time windows remain intentionally faithful to
the ICD input and therefore run immediately today. Replace those values with
future timezone-qualified ISO 8601 timestamps when testing scheduling.

## What The Runtime Enforces

The canonical boundary accepts legacy spellings and normalizes them before
validation. Init then binds the mission to the active world, validates vehicle
and feature membership, required capabilities, comparable numeric vehicle
limits, and simple communication-relay span. Polygon coverage takes lane width
from `objective.coverage_swath_widths`, or from each selected active-world
vehicle's `constraints.coverage_width_m` in the backend-bound compatibility
copy.

The real planner produces waypoint tasks. The edge runtime honors the earliest
start, adjusts final-leg speed toward the arrival target, waits for the arrival
window to open, applies supported motion limits in the autonomy simulator,
sets a requested final heading, and reports pickup/dropoff payload state.

## Current Limits

- The templates are independent missions. CASEVAC phases are not an atomic
  four-step workflow, and selecting the intended carrier between phases remains
  an operator responsibility.
- Capability matching proves declared profile labels, not physical sensor or
  payload simulation.
- Line-of-sight targets and propagation are carried into task metadata; no
  occlusion/radio model proves them.
- Vehicle formation is a final placement semantic, not a controller that keeps
  formation during transit.
- `arrival_time.latest` and `mission_end_time` are carried but are not enforced
  as failure deadlines.
- Path allocation is not collision-aware multi-agent planning and does not
  dynamically replan around moving agents.
- Optimization values influence graph edge cost or filtering where supported;
  they do not guarantee a globally optimal real-world energy, visibility, or
  terrain outcome.
- The simulator records payload state but does not model mass transfer,
  casualty health, radio quality, camera observations, or ballistic effects.

Success therefore means that the mission passes preflight, produces non-empty
waypoint tasks, executes those paths in the editable simulation, and exposes
the expected final placement/task semantics. It does not imply that every
physical-world effect named by the ICD has a high-fidelity simulator.
