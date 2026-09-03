import { beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  createVehicleModel: vi.fn(),
  createWorld: vi.fn(),
  getVehicleModels: vi.fn(),
  updateWorld: vi.fn(),
}));

vi.mock("./api", () => api);

import { migrateLegacyBrowserData } from "./legacyWorldMigration";

const WORLD_KEY = "c2_imugs2_scenario_library";
const MODEL_KEY = "c2_imugs2_vehicle_models";

function installStorage(initial: Record<string, string>) {
  const values = new Map(Object.entries(initial));
  vi.stubGlobal("window", {
    localStorage: {
      getItem: (key: string) => values.get(key) ?? null,
      removeItem: (key: string) => values.delete(key),
    },
  });
  return values;
}

function world(overrides: Record<string, unknown> = {}) {
  return {
    world_id: "world-server",
    name: "Patrol copy",
    map: "rma",
    notes: "",
    feature_ids: ["road-a"],
    selected_agent_id: "",
    agents: [],
    road_imports: [],
    map_view: null,
    revision: 2,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("retired browser payload migration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.getVehicleModels.mockResolvedValue({ vehicle_models: [] });
  });

  it("preserves a conflicting edited server definition as a copy", async () => {
    const storage = installStorage({
      [WORLD_KEY]: JSON.stringify({
        scenarios: [{ scenario_id: "scenario-a", name: "Patrol", map: "rma", feature_ids: ["road-a"], agents: [] }],
      }),
    });
    api.createWorld.mockResolvedValue(world());

    await migrateLegacyBrowserData([world({ world_id: "world-a", name: "Edited server world", revision: 4 })] as never);

    expect(api.updateWorld).not.toHaveBeenCalled();
    expect(api.createWorld).toHaveBeenCalledWith(expect.objectContaining({ name: "Patrol copy" }));
    expect(storage.has(WORLD_KEY)).toBe(false);
  });

  it("recognizes already acknowledged worlds and vehicle models when retrying", async () => {
    const storage = installStorage({
      [WORLD_KEY]: JSON.stringify({ scenarios: [{ name: "Patrol", map: "rma", feature_ids: ["road-a"], agents: [] }] }),
      [MODEL_KEY]: JSON.stringify([{ label: "Scout", vehicle_type: "UGV", constraints: {}, capabilities: ["camera"] }]),
    });
    api.getVehicleModels.mockResolvedValue({
      vehicle_models: [{
        model_id: "model-a",
        label: "Scout",
        vehicle_type: "UGV",
        constraints: {},
        capabilities: ["camera"],
        default_name: "",
        revision: 1,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      }],
    });

    await migrateLegacyBrowserData([world()] as never);

    expect(api.createWorld).not.toHaveBeenCalled();
    expect(api.createVehicleModel).not.toHaveBeenCalled();
    expect(storage.size).toBe(0);
  });

  it("keeps retired keys until every server write is acknowledged", async () => {
    const storage = installStorage({
      [WORLD_KEY]: JSON.stringify({ scenarios: [{ name: "Patrol", map: "rma", feature_ids: ["road-a"], agents: [] }] }),
    });
    api.createWorld.mockRejectedValue(new Error("storage unavailable"));

    await expect(migrateLegacyBrowserData([])).rejects.toThrow("storage unavailable");

    expect(storage.has(WORLD_KEY)).toBe(true);
  });
});
