/* Isolated one-time reader for the retired browser-local scenario payload. */

import {
  createVehicleModel,
  createWorld,
  getVehicleModels,
  updateWorld,
  type VehicleModelRecord,
  type WorldCatalogEntry,
} from "./api";

const LEGACY_SCENARIO_LIBRARY_KEY = "c2_imugs2_scenario_library";
const LEGACY_VEHICLE_MODELS_KEY = "c2_imugs2_vehicle_models";

type LegacyScenario = {
  scenario_id?: string;
  name?: string;
  map?: string;
  notes?: string;
  feature_ids?: string[];
  agents?: Record<string, unknown>[];
  map_view?: { center?: number[]; zoom?: number };
};

export async function migrateLegacyBrowserData(existing: WorldCatalogEntry[]): Promise<boolean> {
  if (typeof window === "undefined") return false;
  const scenarioText = window.localStorage.getItem(LEGACY_SCENARIO_LIBRARY_KEY);
  const modelText = window.localStorage.getItem(LEGACY_VEHICLE_MODELS_KEY);
  if (!scenarioText && !modelText) return false;

  const legacyScenarios = parseScenarios(scenarioText);
  const legacyModels = parseModels(modelText);
  const workingWorlds = [...existing];
  const consumedWorldIds = new Set<string>();
  for (const scenario of legacyScenarios) {
    const expectedWorldId = String(scenario.scenario_id || "").replace(/^scenario-/, "world-");
    const expected = workingWorlds.find((world) => world.world_id === expectedWorldId);
    const definition = {
      name: String(scenario.name || "Imported browser world"),
      map: String(scenario.map || "rma"),
      notes: String(scenario.notes || ""),
      feature_ids: Array.isArray(scenario.feature_ids) ? scenario.feature_ids : [],
      selected_agent_id: "",
      agents: (Array.isArray(scenario.agents) ? scenario.agents : []) as WorldCatalogEntry["agents"],
      road_imports: [],
      map_view: normalizeMapView(scenario.map_view),
      runtime_active: false,
      runtime_status: "saved",
    };
    if (expected && sameImportedWorld(expected, definition)) {
      consumedWorldIds.add(expected.world_id);
    } else if (expected?.revision === 1) {
      const saved = await updateWorld(expected.world_id, { ...definition, revision: expected.revision });
      consumedWorldIds.add(saved.world_id);
      const index = workingWorlds.findIndex((world) => world.world_id === saved.world_id);
      if (index >= 0) workingWorlds[index] = saved;
      else workingWorlds.push(saved);
    } else {
      const imported = { ...definition, name: `${definition.name} copy` };
      const acknowledged = workingWorlds.find(
        (world) => !consumedWorldIds.has(world.world_id) && sameImportedWorld(world, imported),
      );
      if (acknowledged) {
        consumedWorldIds.add(acknowledged.world_id);
      } else {
        const saved = await createWorld(imported);
        consumedWorldIds.add(saved.world_id);
        workingWorlds.push(saved);
      }
    }
  }

  const workingModels = [...(await getVehicleModels()).vehicle_models];
  const consumedModelIds = new Set<string>();
  for (const raw of legacyModels) {
    const imported = {
      label: String(raw.label || raw.vehicle_type || "Imported vehicle model"),
      vehicle_type: String(raw.vehicle_type || "UGV"),
      constraints: typeof raw.constraints === "object" && raw.constraints ? raw.constraints : {},
      capabilities: Array.isArray(raw.capabilities) ? raw.capabilities.filter((item): item is string => typeof item === "string") : [],
      default_name: typeof raw.default_name === "string" ? raw.default_name : undefined,
    };
    const acknowledged = workingModels.find(
      (model) => !consumedModelIds.has(model.model_id) && sameImportedVehicleModel(model, imported),
    );
    if (acknowledged) {
      consumedModelIds.add(acknowledged.model_id);
    } else {
      const saved = await createVehicleModel(imported);
      consumedModelIds.add(saved.model_id);
      workingModels.push(saved);
    }
  }

  window.localStorage.removeItem(LEGACY_SCENARIO_LIBRARY_KEY);
  window.localStorage.removeItem(LEGACY_VEHICLE_MODELS_KEY);
  return true;
}

function sameImportedWorld(
  existing: WorldCatalogEntry,
  imported: Omit<WorldCatalogEntry, "world_id" | "revision" | "created_at" | "updated_at">,
): boolean {
  return existing.name === imported.name
    && existing.map === imported.map
    && String(existing.notes || "") === String(imported.notes || "")
    && JSON.stringify(existing.feature_ids ?? []) === JSON.stringify(imported.feature_ids)
    && JSON.stringify(existing.agents ?? []) === JSON.stringify(imported.agents)
    && JSON.stringify(existing.map_view ?? null) === JSON.stringify(imported.map_view);
}

function sameImportedVehicleModel(
  existing: VehicleModelRecord,
  imported: Parameters<typeof createVehicleModel>[0],
): boolean {
  return existing.label === imported.label
    && existing.vehicle_type === imported.vehicle_type
    && JSON.stringify(existing.constraints ?? {}) === JSON.stringify(imported.constraints ?? {})
    && JSON.stringify(existing.capabilities ?? []) === JSON.stringify(imported.capabilities ?? [])
    && String(existing.default_name || "") === String(imported.default_name || "");
}

function parseScenarios(text: string | null): LegacyScenario[] {
  if (!text) return [];
  try {
    const value = JSON.parse(text) as { scenarios?: LegacyScenario[] };
    return Array.isArray(value.scenarios) ? value.scenarios : [];
  } catch {
    return [];
  }
}

function parseModels(text: string | null): Record<string, unknown>[] {
  if (!text) return [];
  try {
    const value = JSON.parse(text) as unknown;
    return Array.isArray(value) ? value.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object") : [];
  } catch {
    return [];
  }
}

function normalizeMapView(value: LegacyScenario["map_view"]) {
  if (!value || !Array.isArray(value.center) || value.center.length !== 2) return null;
  const center = value.center.map(Number);
  const zoom = Number(value.zoom);
  return center.every(Number.isFinite) && Number.isFinite(zoom)
    ? { center: [center[0], center[1]] as [number, number], zoom }
    : null;
}
