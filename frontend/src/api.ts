import type { Agent, LonLat, MapFeature, MissionConfig } from "./types";
import type { FeatureCollection } from "geojson";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export type RuntimeBootstrap = {
  agents: Agent[];
  map_features: MapFeature[];
  geojson: FeatureCollection;
  osm_roads?: FeatureCollection;
};

export type CreatedMapFeature = {
  feature: FeatureCollection["features"][number];
  map_feature: MapFeature;
  geojson: FeatureCollection;
  map_features: MapFeature[];
};

export type DeletedMapFeature = {
  deleted_feature_id: string;
  geojson: FeatureCollection;
  map_features: MapFeature[];
};

export type UpdatedMapFeature = CreatedMapFeature;

export type OsmRoadImportRequest = {
  bbox: [number, number, number, number];
  polygon?: LonLat[];
  max_features?: number;
};

export type QueriedOsmRoads = {
  feature_count: number;
  source_way_count?: number;
  bbox: [number, number, number, number];
  polygon?: LonLat[];
  clipped_to_polygon?: boolean;
  features: FeatureCollection["features"];
  geojson: FeatureCollection;
  map: string;
  persisted: false;
};

export type ScenarioLaunchRequest = {
  scenario_id: string;
  name: string;
  map: string;
  notes?: string;
  agents: Agent[];
  feature_ids: string[];
  road_imports?: unknown[];
};

export type ScenarioCatalogEntry = {
  scenario_id: string;
  name: string;
  map: string;
  notes: string;
  agents: Agent[];
  feature_ids: string[];
  selected_agent_id: string;
  road_imports: {
    import_id: string;
    name: string;
    bbox: [number, number, number, number];
    feature_count: number;
    geojson: FeatureCollection;
    created_at: string;
  }[];
  version: string;
  map_collection: string;
  feature_count: number;
  road_count: number;
  runtime_active: boolean;
  runtime_status: string;
  created_at: string;
  updated_at: string;
};

export type ScenarioLaunchResult = {
  status: "inactive" | "activating" | "ready" | "failed" | string;
  ready: boolean;
  message: string;
  docker_started?: boolean;
  scenario_id?: string;
  name?: string;
  version?: string;
  map_collection?: string;
  feature_count?: number;
  road_count?: number;
  agents?: Agent[];
  containers?: {
    agent_id: string;
    name: string;
    topic_prefix: string;
    container_name: string;
  }[];
  compose_file?: string;
  host_command?: string;
  started_containers?: string[];
  docker_error?: string;
};

export type MissionState = {
  mission_id: string;
  status?: number | string | null;
  status_name?: string;
  requested_status?: number;
  requested_status_name?: string;
  command_phase?: string;
  planner_status?: string;
  path_status?: string;
  initialized_at?: string;
  updated_at?: string;
  planned_paths?: Record<string, LonLat[]>;
  config?: MissionConfig;
  adapter_adjustments?: {
    type: string;
    field?: string;
    before?: unknown;
    after?: unknown;
    distance_meters?: number;
    message?: string;
  }[];
  legacy_rest?: { ok: boolean; status_code: number; body: string };
};

export type MissionExample = {
  id: string;
  name: string;
  behavior: number;
  vehicles: string[];
  config: MissionConfig;
};

export type DiagnosticsState = {
  checks: { id: string; status: "ok" | "error"; message: string }[];
  ros?: {
    nodes: string[];
    topics: string[];
    services: string[];
  };
  missions?: MissionState[];
  planner_state?: unknown;
};

export type PlanningDiagnostics = {
  mission_id?: string | null;
  checks: { id: string; status: "ok" | "error"; message: string }[];
  summary?: Record<string, unknown>;
  interpretation?: string[];
  scenario_analysis?: PlanningScenarioAnalysis;
  adapter?: unknown;
  legacy_mongo?: unknown;
};

export type PlanningScenarioAnalysis = {
  status: string;
  inputs?: {
    agent_id?: string;
    start?: LonLat;
    objective?: LonLat;
    map?: string;
    coordinate_order?: string;
  };
  model?: Record<string, unknown>;
  graph_summaries?: Record<string, unknown>;
  scenarios?: PlanningScenario[];
  notes?: string[];
};

export type PlanningScenario = {
  id: string;
  label: string;
  status: string;
  parameters?: Record<string, unknown>;
  metrics?: Record<string, unknown>;
  selected_nodes?: Record<string, unknown>;
  route?: LonLat[];
  segments?: unknown[];
  notes?: string[];
};

export type ContractSourceRef = {
  path: string;
  line: number;
};

export type ContractField = {
  section?: string;
  type?: string;
  name: string;
};

export type ContractNode = {
  id: string;
  label: string;
  kind: string;
  layer: string;
  description?: string;
  source_refs?: ContractSourceRef[];
  fields?: ContractField[];
  runtime_status?: string;
  details?: Record<string, unknown>;
};

export type ContractEdge = {
  id: string;
  source: string;
  target: string;
  label: string;
  kind: string;
  layer: string;
  protocol?: string;
  direction?: string;
  contract?: string;
  method?: string;
  source_refs?: ContractSourceRef[];
  fields?: ContractField[];
  notes?: string[];
};

export type ContractScenarioStage = {
  id: string;
  label: string;
  component: string;
  inputs?: string[];
  outputs?: string[];
  source_refs?: ContractSourceRef[];
  notes?: string[];
};

export type ContractScenario = {
  id: string;
  label: string;
  summary: string;
  stages: ContractScenarioStage[];
  risks?: string[];
};

export type ContractEvidenceRef = ContractSourceRef & {
  symbol?: string;
  claim?: string;
  verification?: "source" | "runtime" | "documented" | "inferred";
};

export type ContractAtlasZone = {
  id: string;
  label: string;
  eyebrow: string;
  description: string;
  tone: string;
  order: number;
};

export type ContractAtlasComponent = {
  id: string;
  label: string;
  short_label?: string;
  zone: string;
  kind: string;
  description: string;
  runtime_name?: string;
  container?: string;
  responsibilities: string[];
  tags: string[];
  source_refs: ContractEvidenceRef[];
  runtime_status?: "visible" | "not_seen" | "not_checked" | "dynamic";
};

export type ContractAtlasInteraction = {
  id: string;
  source: string;
  target: string;
  label: string;
  channel: string;
  protocol: string;
  interface?: string;
  contract?: string;
  direction?: string;
  description: string;
  phases: string[];
  fields?: ContractField[];
  request_fields?: ContractField[];
  response_fields?: ContractField[];
  source_refs: ContractEvidenceRef[];
  notes: string[];
  runtime_status?: "visible" | "not_seen" | "not_checked" | "dynamic";
};

export type ContractAtlasWorkflowStep = {
  id: string;
  number: number;
  title: string;
  summary: string;
  phase: string;
  actor_ids: string[];
  interaction_ids: string[];
  input?: unknown;
  output?: unknown;
  transformations: string[];
  source_refs: ContractEvidenceRef[];
  notes: string[];
};

export type ContractAtlasWorkflow = {
  id: string;
  label: string;
  summary: string;
  example: Record<string, unknown>;
  steps: ContractAtlasWorkflowStep[];
};

export type ContractAtlas = {
  title: string;
  scope: string;
  verification: {
    status: string;
    method: string;
    source_evidence_count: number;
    runtime_status: string;
    caveats: string[];
  };
  zones: ContractAtlasZone[];
  components: ContractAtlasComponent[];
  interactions: ContractAtlasInteraction[];
  workflow: ContractAtlasWorkflow;
  contract_gaps: {
    id: string;
    severity: string;
    title: string;
    description: string;
    source_refs: ContractEvidenceRef[];
  }[];
};

export type ContractGraph = {
  generated_at: string;
  source_digest: string;
  source_file_count: number;
  summary: {
    nodes: number;
    edges: number;
    scenarios: number;
    by_layer?: Record<string, number>;
    by_kind?: Record<string, number>;
  };
  catalog?: {
    status: string;
    authoritative_view: string;
    description: string;
    limitations?: string[];
  };
  layers: { id: string; label: string }[];
  nodes: ContractNode[];
  edges: ContractEdge[];
  scenarios: ContractScenario[];
  atlas: ContractAtlas;
  runtime?: {
    ros_nodes?: string[];
    ros_topics?: string[];
    ros_services?: string[];
  };
  adapter_runtime?: Record<string, unknown>;
};

export type AgentUpdateEvent = {
  agent_id: string;
  status?: string;
  current_location?: [number, number] | null;
  tasks?: unknown[];
  raw?: unknown;
};

export type PlannerUpdateEvent = {
  mission_id?: string;
  paths?: Record<string, LonLat[]>;
  source?: string;
  received_at?: string;
  path_summary?: {
    path_count: number;
    waypoint_count: number;
    waypoints_by_agent: Record<string, number>;
  };
  state?: unknown;
  raw?: unknown;
};

export type LegacyResetResult = {
  status: "ok";
  database: string;
  deleted: Record<string, number>;
  preserved: string[];
  restart_required: boolean;
  message: string;
};

export type LegacyTrace = {
  steps: { id: string; status: "ok" | "error"; message: string }[];
  legacy_rest: { ok: boolean; status_code: number; body: string };
  ros: {
    nodes: string[];
    topics: string[];
    services: string[];
  };
  missions: unknown[];
  agent_updates: unknown[];
  planner_state?: unknown;
};

export type ForgottenMission = {
  mission_id: string;
  removed: boolean;
  message: string;
};

export async function getRuntimeBootstrap(mapName = "rma"): Promise<RuntimeBootstrap> {
  return getJson(`/api/runtime/bootstrap?map=${encodeURIComponent(mapName)}`);
}

export async function getOsmRoads(mapName = "rma"): Promise<FeatureCollection> {
  return getJson(`/api/map/osm-roads?map=${encodeURIComponent(mapName)}`);
}

export async function queryOsmRoads(request: OsmRoadImportRequest, mapName = "rma"): Promise<QueriedOsmRoads> {
  return postJson(`/api/map/osm-roads/query?map=${encodeURIComponent(mapName)}`, request);
}

export async function launchScenario(request: ScenarioLaunchRequest): Promise<ScenarioLaunchResult> {
  return postJson("/api/scenarios/activate", request);
}

export async function getActiveScenario(): Promise<ScenarioLaunchResult> {
  return getJson("/api/scenarios/active");
}

export async function getScenarios(): Promise<{ scenarios: ScenarioCatalogEntry[] }> {
  return getJson("/api/scenarios");
}

export async function createMapFeature(feature: FeatureCollection["features"][number], mapName = "rma"): Promise<CreatedMapFeature> {
  return postJson(`/api/map/features?map=${encodeURIComponent(mapName)}`, feature);
}

export async function deleteMapFeature(featureId: string, mapName = "rma"): Promise<DeletedMapFeature> {
  return deleteJson(`/api/map/features/${encodeURIComponent(featureId)}?map=${encodeURIComponent(mapName)}`);
}

export async function updateMapFeature(featureId: string, feature: FeatureCollection["features"][number], mapName = "rma"): Promise<UpdatedMapFeature> {
  return putJson(`/api/map/features/${encodeURIComponent(featureId)}?map=${encodeURIComponent(mapName)}`, feature);
}

export async function getDiagnostics(): Promise<DiagnosticsState> {
  return getJson("/api/diagnostics");
}

export async function getPlanningDiagnostics(missionId?: string): Promise<PlanningDiagnostics> {
  const suffix = missionId ? `?mission_id=${encodeURIComponent(missionId)}` : "";
  return getJson(`/api/planning/diagnostics${suffix}`);
}

export async function getContracts(includeRuntime = true): Promise<ContractGraph> {
  return getJson(`/api/contracts?include_runtime=${includeRuntime ? "true" : "false"}`);
}

export async function getMissionExamples(): Promise<{ examples: MissionExample[] }> {
  return getJson("/api/mission-examples");
}

export async function getLegacyTrace(): Promise<LegacyTrace> {
  return getJson("/api/legacy/trace");
}

export async function resetLegacyRuntime(): Promise<LegacyResetResult> {
  return postJson("/api/testing/reset-legacy-runtime", {});
}

export async function initMission(mission: MissionConfig): Promise<MissionState> {
  return postJson("/api/missions/init", mission);
}

export async function getMissionState(missionId: string): Promise<MissionState> {
  return getJson(`/api/missions/${encodeURIComponent(missionId)}`);
}

export async function approveMission(missionId: string): Promise<MissionState> {
  return postJson(`/api/missions/${missionId}/approve`, {});
}

export async function startMission(missionId: string): Promise<MissionState> {
  return postJson(`/api/missions/${missionId}/start`, {});
}

export async function forgetMission(missionId: string): Promise<ForgottenMission> {
  return deleteJson(`/api/missions/${encodeURIComponent(missionId)}`);
}

export function createEventSource() {
  return new EventSource(`${API_BASE_URL}/api/events`);
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) throw new Error(await response.text());
  return response.json() as Promise<T>;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json() as Promise<T>;
}

async function deleteJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { method: "DELETE" });
  if (!response.ok) throw new Error(await response.text());
  return response.json() as Promise<T>;
}

async function putJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json() as Promise<T>;
}
