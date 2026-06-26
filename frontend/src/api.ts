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
  max_features?: number;
};

export type ImportedOsmRoads = {
  imported_count: number;
  skipped_existing: number;
  bbox: [number, number, number, number];
  features: FeatureCollection["features"];
  geojson: FeatureCollection;
  map_features: MapFeature[];
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
  layers: { id: string; label: string }[];
  nodes: ContractNode[];
  edges: ContractEdge[];
  scenarios: ContractScenario[];
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

export async function importOsmRoads(request: OsmRoadImportRequest, mapName = "rma"): Promise<ImportedOsmRoads> {
  return postJson(`/api/map/osm-roads/import?map=${encodeURIComponent(mapName)}`, request);
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
