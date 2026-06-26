import {
  Check,
  Copy,
  Database,
  Gauge,
  MapPinned,
  Plus,
  RadioTower,
  Route,
  Save,
  SlidersHorizontal,
  Target,
  Trash2,
  Users,
} from "lucide-react";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import type { ImportedOsmRoads, OsmRoadImportRequest } from "./api";
import { Badge } from "./components/ui/badge";
import { Button } from "./components/ui/button";
import { Tabs } from "./components/ui/tabs";
import type { Agent, LonLat, MapFeature } from "./types";

type ScenarioAgentSource = "legacy_connected" | "scenario_only";

type ScenarioAgent = Agent & {
  source: ScenarioAgentSource;
};

type ScenarioRecord = {
  scenario_id: string;
  name: string;
  map: string;
  notes: string;
  feature_ids: string[];
  selected_agent_id: string;
  agents: ScenarioAgent[];
  created_at: string;
  updated_at: string;
};

type ScenarioLibrary = {
  active_scenario_id: string;
  scenarios: ScenarioRecord[];
};

type ScenarioLabProps = {
  agents: Agent[];
  mapFeatures: MapFeature[];
  selectedFeatureId?: string;
  onScenarioAgentsChange: (agents: Agent[]) => void;
  onSelectFeature: (featureId: string) => void;
  onImportOsmRoads: (request: OsmRoadImportRequest) => Promise<ImportedOsmRoads>;
};

const STORAGE_KEY = "c2_imugs2_scenario_library";
const LEGACY_AGENT_ID = "f9992bb3-9871-451f-90a0-9207eb9fe6c5";
const DEFAULT_BBOX: [number, number, number, number] = [4.3885, 50.8428, 4.3972, 50.8467];

export function ScenarioLab({
  agents,
  mapFeatures,
  selectedFeatureId,
  onScenarioAgentsChange,
  onSelectFeature,
  onImportOsmRoads,
}: ScenarioLabProps) {
  const [library, setLibrary] = useState<ScenarioLibrary>(() => loadScenarioLibrary(agents));
  const [tab, setTab] = useState("situation");
  const activeScenario = library.scenarios.find((scenario) => scenario.scenario_id === library.active_scenario_id) ?? library.scenarios[0];
  const selectedFeature = mapFeatures.find((feature) => feature.feature_id === selectedFeatureId);
  const scenarioFeatures = useMemo(
    () => activeScenario.feature_ids.flatMap((featureId) => mapFeatures.find((feature) => feature.feature_id === featureId) ?? []),
    [activeScenario.feature_ids, mapFeatures],
  );
  const selectedAgent = activeScenario.agents.find((agent) => agent.agent_id === activeScenario.selected_agent_id) ?? activeScenario.agents[0];

  useEffect(() => {
    saveScenarioLibrary(library);
    onScenarioAgentsChange(activeScenario.agents.map(toAgent));
  }, [activeScenario.agents, library, onScenarioAgentsChange]);

  function updateActiveScenario(patch: Partial<ScenarioRecord>) {
    setLibrary((current) => {
      const updatedAt = new Date().toISOString();
      return {
        ...current,
        scenarios: current.scenarios.map((scenario) =>
          scenario.scenario_id === activeScenario.scenario_id ? { ...scenario, ...patch, updated_at: updatedAt } : scenario,
        ),
      };
    });
  }

  function updateAgent(agentId: string, patch: Partial<ScenarioAgent>) {
    updateActiveScenario({
      selected_agent_id: activeScenario.selected_agent_id === agentId ? patch.agent_id ?? agentId : activeScenario.selected_agent_id,
      agents: activeScenario.agents.map((agent) => (agent.agent_id === agentId ? { ...agent, ...patch, capabilities: [] } : agent)),
    });
  }

  function createScenario() {
    const scenario = defaultScenario(agents);
    setLibrary((current) => ({
      active_scenario_id: scenario.scenario_id,
      scenarios: [...current.scenarios, scenario],
    }));
  }

  function duplicateScenario() {
    const now = new Date().toISOString();
    const copy = {
      ...activeScenario,
      scenario_id: randomId("scenario"),
      name: `${activeScenario.name} copy`,
      created_at: now,
      updated_at: now,
    };
    setLibrary((current) => ({
      active_scenario_id: copy.scenario_id,
      scenarios: [...current.scenarios, copy],
    }));
  }

  function deleteScenario() {
    if (library.scenarios.length <= 1) return;
    setLibrary((current) => {
      const scenarios = current.scenarios.filter((scenario) => scenario.scenario_id !== activeScenario.scenario_id);
      return {
        active_scenario_id: scenarios[0]?.scenario_id ?? "",
        scenarios,
      };
    });
  }

  function resetVehiclesFromRuntime() {
    const runtimeAgents = agents.length ? agents.map((agent) => scenarioAgentFromAgent(agent)) : [createScenarioAgent("Themis Fr", LEGACY_AGENT_ID, "legacy_connected")];
    updateActiveScenario({
      selected_agent_id: runtimeAgents[0]?.agent_id ?? "",
      agents: runtimeAgents,
    });
  }

  function addSelectedFeature() {
    if (!selectedFeature || activeScenario.feature_ids.includes(selectedFeature.feature_id)) return;
    updateActiveScenario({ feature_ids: [...activeScenario.feature_ids, selectedFeature.feature_id] });
  }

  function removeFeature(featureId: string) {
    updateActiveScenario({ feature_ids: activeScenario.feature_ids.filter((id) => id !== featureId) });
  }

  function addAgent() {
    const agent = createScenarioAgent(`Vehicle ${activeScenario.agents.length + 1}`);
    updateActiveScenario({
      selected_agent_id: agent.agent_id,
      agents: [...activeScenario.agents, agent],
    });
  }

  function cloneAgent(agent: ScenarioAgent) {
    const copy = {
      ...agent,
      agent_id: randomId("scenario-agent"),
      name: `${agent.name || agent.agent_id} copy`,
      source: "scenario_only" as const,
      capabilities: [],
    };
    updateActiveScenario({
      selected_agent_id: copy.agent_id,
      agents: [...activeScenario.agents, copy],
    });
  }

  function removeAgent(agentId: string) {
    const agents = activeScenario.agents.filter((agent) => agent.agent_id !== agentId);
    updateActiveScenario({
      selected_agent_id: activeScenario.selected_agent_id === agentId ? agents[0]?.agent_id ?? "" : activeScenario.selected_agent_id,
      agents,
    });
  }

  async function importRoads(request: OsmRoadImportRequest) {
    const result = await onImportOsmRoads(request);
    const importedIds = result.features
      .map((feature) => feature.properties?.feature_id ?? feature.id)
      .filter((featureId): featureId is string => typeof featureId === "string");
    updateActiveScenario({ feature_ids: unique([...activeScenario.feature_ids, ...importedIds]) });
    return result;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4 rounded-md border border-border bg-panel p-4">
        <div className="min-w-0">
          <LabTitle icon={<SlidersHorizontal className="h-4 w-4" />} label="Scenario Lab" />
          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span>{activeScenario.name}</span>
            <span>{activeScenario.agents.length} vehicles</span>
            <span>{scenarioFeatures.length} assets</span>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <select
            className="h-8 max-w-56 rounded-md border border-border bg-background px-2 text-xs outline-none focus:ring-2 focus:ring-ring"
            value={activeScenario.scenario_id}
            onChange={(event) => setLibrary((current) => ({ ...current, active_scenario_id: event.target.value }))}
          >
            {library.scenarios.map((scenario) => (
              <option key={scenario.scenario_id} value={scenario.scenario_id}>
                {scenario.name}
              </option>
            ))}
          </select>
          <Button size="icon" variant="outline" onClick={createScenario} title="New scenario">
            <Plus className="h-4 w-4" />
          </Button>
          <Button size="icon" variant="outline" onClick={duplicateScenario} title="Duplicate scenario">
            <Copy className="h-4 w-4" />
          </Button>
          <Button size="icon" variant="ghost" disabled={library.scenarios.length <= 1} onClick={deleteScenario} title="Delete scenario">
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <Tabs
        value={tab}
        onValueChange={setTab}
        items={[
          { value: "situation", label: "Situation" },
          { value: "vehicles", label: "Vehicles" },
          { value: "roads", label: "Roads" },
        ]}
      />

      {tab === "situation" && (
        <SituationPanel
          scenario={activeScenario}
          selectedFeature={selectedFeature}
          scenarioFeatures={scenarioFeatures}
          onUpdateScenario={updateActiveScenario}
          onAddSelectedFeature={addSelectedFeature}
          onRemoveFeature={removeFeature}
          onSelectFeature={onSelectFeature}
        />
      )}

      {tab === "vehicles" && (
        <VehiclePanel
          agents={activeScenario.agents}
          selectedAgent={selectedAgent}
          onSelectAgent={(agentId) => updateActiveScenario({ selected_agent_id: agentId })}
          onAddAgent={addAgent}
          onCloneAgent={cloneAgent}
          onRemoveAgent={removeAgent}
          onUpdateAgent={updateAgent}
          onResetRuntime={resetVehiclesFromRuntime}
        />
      )}

      {tab === "roads" && (
        <RoadImportPanel
          selectedFeature={selectedFeature}
          scenarioFeatures={scenarioFeatures}
          onImportRoads={importRoads}
        />
      )}
    </div>
  );
}

function SituationPanel({
  scenario,
  selectedFeature,
  scenarioFeatures,
  onUpdateScenario,
  onAddSelectedFeature,
  onRemoveFeature,
  onSelectFeature,
}: {
  scenario: ScenarioRecord;
  selectedFeature?: MapFeature;
  scenarioFeatures: MapFeature[];
  onUpdateScenario: (patch: Partial<ScenarioRecord>) => void;
  onAddSelectedFeature: () => void;
  onRemoveFeature: (featureId: string) => void;
  onSelectFeature: (featureId: string) => void;
}) {
  const grouped = groupByFeatureType(scenarioFeatures);
  return (
    <div className="space-y-4">
      <div className="rounded-md border border-border bg-panel p-4">
        <LabTitle icon={<Save className="h-4 w-4" />} label="Scenario" />
        <div className="mt-3 grid grid-cols-2 gap-3">
          <TextField label="Name" value={scenario.name} onChange={(value) => onUpdateScenario({ name: value })} />
          <TextField label="Map" value={scenario.map} onChange={(value) => onUpdateScenario({ map: value })} />
        </div>
        <label className="mt-3 block text-xs">
          <span className="font-medium text-muted-foreground">Notes</span>
          <textarea
            className="mt-1 h-20 w-full resize-none rounded-md border border-border bg-background px-2 py-2 outline-none focus:ring-2 focus:ring-ring"
            value={scenario.notes}
            onChange={(event) => onUpdateScenario({ notes: event.target.value })}
          />
        </label>
      </div>

      {selectedFeature && (
        <div className="flex items-center justify-between gap-3 rounded-md border border-border bg-background p-3 text-xs">
          <div className="min-w-0">
            <span className="font-medium">{selectedFeature.name}</span>{" "}
            <span className="text-muted-foreground">({selectedFeature.feature_type}, {selectedFeature.geometry.type})</span>
          </div>
          <Button size="sm" variant="outline" disabled={scenario.feature_ids.includes(selectedFeature.feature_id)} onClick={onAddSelectedFeature}>
            <Plus className="h-4 w-4" />
            Add Asset
          </Button>
        </div>
      )}

      <div className="grid grid-cols-3 gap-2">
        {["objective", "road", "workspace", "geofence", "risk"].map((type) => (
          <div key={type} className="rounded-md border border-border bg-panel p-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold capitalize">{type}</span>
              <Badge>{grouped[type]?.length ?? 0}</Badge>
            </div>
            <div className="mt-2 space-y-2">
              {(grouped[type] ?? []).slice(0, 4).map((feature) => (
                <ScenarioFeatureRow key={feature.feature_id} feature={feature} onSelectFeature={onSelectFeature} onRemoveFeature={onRemoveFeature} />
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="rounded-md border border-border bg-panel p-4">
        <div className="flex items-center justify-between">
          <LabTitle icon={<MapPinned className="h-4 w-4" />} label="Scenario Assets" />
          <Badge>{scenarioFeatures.length}</Badge>
        </div>
        <div className="mt-3 space-y-2">
          {scenarioFeatures.length ? (
            scenarioFeatures.map((feature) => (
              <ScenarioFeatureRow key={feature.feature_id} feature={feature} onSelectFeature={onSelectFeature} onRemoveFeature={onRemoveFeature} />
            ))
          ) : (
            <div className="rounded-sm border border-border bg-background px-3 py-2 text-xs text-muted-foreground">No scenario assets selected.</div>
          )}
        </div>
      </div>
    </div>
  );
}

function ScenarioFeatureRow({
  feature,
  onSelectFeature,
  onRemoveFeature,
}: {
  feature: MapFeature;
  onSelectFeature: (featureId: string) => void;
  onRemoveFeature: (featureId: string) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-2 rounded-sm border border-border bg-background px-2 py-2 text-xs">
      <button className="min-w-0 text-left" onClick={() => onSelectFeature(feature.feature_id)}>
        <div className="truncate font-medium">{feature.name}</div>
        <div className="truncate text-muted-foreground">{feature.feature_id}</div>
      </button>
      <div className="flex shrink-0 items-center gap-1">
        <Badge>{feature.feature_type}</Badge>
        <Button size="icon" variant="ghost" onClick={() => onRemoveFeature(feature.feature_id)} title="Remove from scenario">
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

function VehiclePanel({
  agents,
  selectedAgent,
  onSelectAgent,
  onAddAgent,
  onCloneAgent,
  onRemoveAgent,
  onUpdateAgent,
  onResetRuntime,
}: {
  agents: ScenarioAgent[];
  selectedAgent?: ScenarioAgent;
  onSelectAgent: (agentId: string) => void;
  onAddAgent: () => void;
  onCloneAgent: (agent: ScenarioAgent) => void;
  onRemoveAgent: (agentId: string) => void;
  onUpdateAgent: (agentId: string, patch: Partial<ScenarioAgent>) => void;
  onResetRuntime: () => void;
}) {
  return (
    <div className="grid grid-cols-[260px_1fr] gap-4">
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <LabTitle icon={<Users className="h-4 w-4" />} label="Vehicles" />
          <div className="flex gap-1">
            <Button size="icon" variant="outline" onClick={onResetRuntime} title="Load runtime vehicles">
              <Database className="h-4 w-4" />
            </Button>
            <Button size="icon" variant="outline" onClick={onAddAgent} title="Add vehicle">
              <Plus className="h-4 w-4" />
            </Button>
          </div>
        </div>
        {agents.map((agent) => (
          <button
            key={agent.agent_id}
            className={`w-full rounded-md border bg-panel p-3 text-left outline-none hover:bg-muted focus:ring-2 focus:ring-ring ${selectedAgent?.agent_id === agent.agent_id ? "border-primary shadow-sm" : "border-border"}`}
            onClick={() => onSelectAgent(agent.agent_id)}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="truncate text-sm font-semibold">{agent.name || agent.agent_id}</span>
              <Badge tone={agent.source === "legacy_connected" ? "ok" : "warn"}>{agent.source === "legacy_connected" ? "ROS" : "scenario"}</Badge>
            </div>
            <div className="mt-1 truncate text-xs text-muted-foreground">{agent.agent_id}</div>
            <div className="mt-2 flex flex-wrap gap-1">
              <Badge>{agent.vehicle_type}</Badge>
              <Badge>{agent.status}</Badge>
              {typeof agent.constraints.max_speed === "number" && <Badge>{agent.constraints.max_speed.toFixed(1)} m/s</Badge>}
            </div>
          </button>
        ))}
      </div>

      {selectedAgent ? (
        <AgentEditor
          agent={selectedAgent}
          canRemove={agents.length > 1}
          onClone={() => onCloneAgent(selectedAgent)}
          onRemove={() => onRemoveAgent(selectedAgent.agent_id)}
          onUpdate={(patch) => onUpdateAgent(selectedAgent.agent_id, patch)}
        />
      ) : (
        <div className="rounded-md border border-border bg-panel p-4 text-sm text-muted-foreground">No vehicle selected.</div>
      )}
    </div>
  );
}

function AgentEditor({
  agent,
  canRemove,
  onClone,
  onRemove,
  onUpdate,
}: {
  agent: ScenarioAgent;
  canRemove: boolean;
  onClone: () => void;
  onRemove: () => void;
  onUpdate: (patch: Partial<ScenarioAgent>) => void;
}) {
  function updateConstraint(key: keyof Agent["constraints"], value: number | undefined) {
    onUpdate({ constraints: { ...agent.constraints, [key]: value } });
  }

  return (
    <div className="space-y-4">
      <div className="rounded-md border border-border bg-panel p-4">
        <div className="flex items-center justify-between">
          <LabTitle icon={<RadioTower className="h-4 w-4" />} label="Identity" />
          <div className="flex gap-2">
            <Button size="sm" variant="outline" onClick={onClone}>
              <Copy className="h-4 w-4" />
              Clone
            </Button>
            <Button size="sm" variant="ghost" disabled={!canRemove} onClick={onRemove}>
              <Trash2 className="h-4 w-4" />
              Remove
            </Button>
          </div>
        </div>
        <div className="mt-3 grid grid-cols-2 gap-3">
          <TextField label="Name" value={agent.name} onChange={(value) => onUpdate({ name: value })} />
          <TextField label="Vehicle type" value={agent.vehicle_type} onChange={(value) => onUpdate({ vehicle_type: value })} />
          <TextField label="Agent UUID" value={agent.agent_id} onChange={(value) => onUpdate({ agent_id: value })} />
          <SelectField
            label="Runtime source"
            value={agent.source}
            options={[
              { value: "legacy_connected", label: "Legacy-connected ROS node" },
              { value: "scenario_only", label: "Scenario-only" },
            ]}
            onChange={(value) => onUpdate({ source: value as ScenarioAgentSource })}
          />
          <NumberField label="Longitude" value={agent.current_location[0]} step={0.000001} onChange={(value) => onUpdate({ current_location: [value ?? agent.current_location[0], agent.current_location[1]] })} />
          <NumberField label="Latitude" value={agent.current_location[1]} step={0.000001} onChange={(value) => onUpdate({ current_location: [agent.current_location[0], value ?? agent.current_location[1]] })} />
        </div>
      </div>

      <div className="rounded-md border border-border bg-panel p-4">
        <LabTitle icon={<Gauge className="h-4 w-4" />} label="Constraints" />
        <div className="mt-3 grid grid-cols-4 gap-3">
          <NumberField label="Max speed" value={agent.constraints.max_speed} min={0} step={0.1} onChange={(value) => updateConstraint("max_speed", value)} />
          <NumberField label="Max accel" value={agent.constraints.max_acceleration} min={0} step={0.1} onChange={(value) => updateConstraint("max_acceleration", value)} />
          <NumberField label="Max decel" value={agent.constraints.max_deceleration} min={0} step={0.1} onChange={(value) => updateConstraint("max_deceleration", value)} />
          <NumberField label="Max weight" value={agent.constraints.max_weight} min={0} step={1} onChange={(value) => updateConstraint("max_weight", value)} />
          <NumberField label="Straight slope" value={agent.constraints.max_straight_slope} min={0} step={0.1} onChange={(value) => updateConstraint("max_straight_slope", value)} />
          <NumberField label="Side slope" value={agent.constraints.max_side_slope} min={0} step={0.1} onChange={(value) => updateConstraint("max_side_slope", value)} />
          <NumberField label="Max tilt" value={agent.constraints.max_tilt_angle} min={0} step={0.01} onChange={(value) => updateConstraint("max_tilt_angle", value)} />
        </div>
      </div>
    </div>
  );
}

function RoadImportPanel({
  selectedFeature,
  scenarioFeatures,
  onImportRoads,
}: {
  selectedFeature?: MapFeature;
  scenarioFeatures: MapFeature[];
  onImportRoads: (request: OsmRoadImportRequest) => Promise<ImportedOsmRoads>;
}) {
  const [bbox, setBbox] = useState<[number, number, number, number]>(() => selectedFeature ? bboxFromFeature(selectedFeature) ?? DEFAULT_BBOX : DEFAULT_BBOX);
  const [maxFeatures, setMaxFeatures] = useState(80);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<ImportedOsmRoads | undefined>();
  const [error, setError] = useState("");

  function useSelectedBbox() {
    if (!selectedFeature) return;
    const next = bboxFromFeature(selectedFeature);
    if (next) setBbox(expandBbox(next, 0.00025));
  }

  function useScenarioBbox() {
    const next = bboxFromFeatures(scenarioFeatures);
    if (next) setBbox(expandBbox(next, 0.00025));
  }

  async function submit() {
    setBusy(true);
    setError("");
    setResult(undefined);
    try {
      setResult(await onImportRoads({ bbox, max_features: maxFeatures }));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="rounded-md border border-border bg-panel p-4">
        <div className="flex items-center justify-between">
          <LabTitle icon={<Route className="h-4 w-4" />} label="OSM Road Import" />
          <Badge>{formatBboxSize(bbox)}</Badge>
        </div>
        <div className="mt-3 grid grid-cols-4 gap-3">
          <NumberField label="West" value={bbox[0]} step={0.000001} onChange={(value) => setBbox([value ?? bbox[0], bbox[1], bbox[2], bbox[3]])} />
          <NumberField label="South" value={bbox[1]} step={0.000001} onChange={(value) => setBbox([bbox[0], value ?? bbox[1], bbox[2], bbox[3]])} />
          <NumberField label="East" value={bbox[2]} step={0.000001} onChange={(value) => setBbox([bbox[0], bbox[1], value ?? bbox[2], bbox[3]])} />
          <NumberField label="North" value={bbox[3]} step={0.000001} onChange={(value) => setBbox([bbox[0], bbox[1], bbox[2], value ?? bbox[3]])} />
          <NumberField label="Max roads" value={maxFeatures} min={1} max={300} step={1} onChange={(value) => setMaxFeatures(Math.max(1, Math.min(300, value ?? 80)))} />
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          <Button size="sm" variant="outline" disabled={!selectedFeature} onClick={useSelectedBbox}>
            <Target className="h-4 w-4" />
            From Selection
          </Button>
          <Button size="sm" variant="outline" disabled={!scenarioFeatures.length} onClick={useScenarioBbox}>
            <MapPinned className="h-4 w-4" />
            From Scenario
          </Button>
          <Button size="sm" onClick={submit} disabled={busy}>
            <Check className="h-4 w-4" />
            {busy ? "Importing" : "Import Roads"}
          </Button>
        </div>
      </div>

      {error && <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-900">{error}</div>}
      {result && (
        <div className="rounded-md border border-border bg-panel p-4">
          <div className="flex items-center justify-between">
            <LabTitle icon={<Route className="h-4 w-4" />} label="Import Result" />
            <Badge tone={result.imported_count > 0 ? "ok" : "warn"}>{result.imported_count} imported</Badge>
          </div>
          <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
            <InfoBlock label="Imported" value={String(result.imported_count)} />
            <InfoBlock label="Skipped" value={String(result.skipped_existing)} />
            <InfoBlock label="BBox" value={result.bbox.map((value) => value.toFixed(5)).join(", ")} />
          </div>
        </div>
      )}
    </div>
  );
}

function defaultScenario(runtimeAgents: Agent[]): ScenarioRecord {
  const now = new Date().toISOString();
  const agents = runtimeAgents.length ? runtimeAgents.map((agent) => scenarioAgentFromAgent(agent)) : [createScenarioAgent("Themis Fr", LEGACY_AGENT_ID, "legacy_connected")];
  return {
    scenario_id: randomId("scenario"),
    name: "New scenario",
    map: "rma",
    notes: "",
    feature_ids: [],
    selected_agent_id: agents[0]?.agent_id ?? "",
    agents,
    created_at: now,
    updated_at: now,
  };
}

function loadScenarioLibrary(runtimeAgents: Agent[]): ScenarioLibrary {
  if (typeof window !== "undefined") {
    try {
      const stored = JSON.parse(window.localStorage.getItem(STORAGE_KEY) ?? "null") as ScenarioLibrary | null;
      if (stored?.scenarios?.length) return normalizeLibrary(stored, runtimeAgents);
    } catch {
      // Fall through to default library.
    }
  }
  const scenario = defaultScenario(runtimeAgents);
  return { active_scenario_id: scenario.scenario_id, scenarios: [scenario] };
}

function normalizeLibrary(stored: ScenarioLibrary, runtimeAgents: Agent[]): ScenarioLibrary {
  const scenarios = stored.scenarios.map((scenario) => ({
    ...defaultScenario(runtimeAgents),
    ...scenario,
    agents: scenario.agents.map((agent) => scenarioAgentFromAgent(agent, agent.source)),
    feature_ids: unique(scenario.feature_ids ?? []),
  }));
  return {
    active_scenario_id: scenarios.some((scenario) => scenario.scenario_id === stored.active_scenario_id) ? stored.active_scenario_id : scenarios[0]?.scenario_id ?? "",
    scenarios,
  };
}

function saveScenarioLibrary(library: ScenarioLibrary) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(library));
}

function scenarioAgentFromAgent(agent: Agent, source: ScenarioAgentSource = agent.agent_id === LEGACY_AGENT_ID ? "legacy_connected" : "scenario_only"): ScenarioAgent {
  return {
    agent_id: agent.agent_id,
    name: agent.name,
    vehicle_type: agent.vehicle_type,
    status: agent.status,
    current_location: agent.current_location,
    constraints: {
      max_speed: agent.constraints.max_speed ?? 4,
      max_acceleration: agent.constraints.max_acceleration ?? 0,
      max_deceleration: agent.constraints.max_deceleration ?? 0,
      max_jerk: agent.constraints.max_jerk ?? 0,
      max_straight_slope: agent.constraints.max_straight_slope ?? 0,
      max_side_slope: agent.constraints.max_side_slope ?? 0,
      max_weight: agent.constraints.max_weight ?? 0,
      max_tilt_angle: agent.constraints.max_tilt_angle ?? 0,
    },
    capabilities: [],
    source,
  };
}

function createScenarioAgent(name: string, agentId = randomUuid(), source: ScenarioAgentSource = "scenario_only"): ScenarioAgent {
  return scenarioAgentFromAgent(
    {
      agent_id: agentId,
      name,
      vehicle_type: "UGV",
      status: "available",
      current_location: [4.392588, 50.844317],
      constraints: { max_speed: 4 },
      capabilities: [],
    },
    source,
  );
}

function toAgent(agent: ScenarioAgent): Agent {
  return {
    agent_id: agent.agent_id,
    name: agent.name,
    vehicle_type: agent.vehicle_type,
    status: agent.status,
    current_location: agent.current_location,
    constraints: agent.constraints,
    capabilities: [],
  };
}

function groupByFeatureType(features: MapFeature[]) {
  return features.reduce<Record<string, MapFeature[]>>((groups, feature) => {
    const key = feature.feature_type;
    groups[key] = [...(groups[key] ?? []), feature];
    return groups;
  }, {});
}

function bboxFromFeatures(features: MapFeature[]): [number, number, number, number] | undefined {
  const points = features.flatMap((feature) => flattenPoints(feature.geometry.coordinates));
  return bboxFromPoints(points);
}

function bboxFromFeature(feature: MapFeature): [number, number, number, number] | undefined {
  return bboxFromPoints(flattenPoints(feature.geometry.coordinates));
}

function bboxFromPoints(points: LonLat[]): [number, number, number, number] | undefined {
  if (!points.length) return undefined;
  const lons = points.map((point) => point[0]);
  const lats = points.map((point) => point[1]);
  return [Math.min(...lons), Math.min(...lats), Math.max(...lons), Math.max(...lats)];
}

function expandBbox(bbox: [number, number, number, number], margin: number): [number, number, number, number] {
  return [bbox[0] - margin, bbox[1] - margin, bbox[2] + margin, bbox[3] + margin];
}

function flattenPoints(value: unknown): LonLat[] {
  if (!Array.isArray(value)) return [];
  if (typeof value[0] === "number" && typeof value[1] === "number") return [[value[0], value[1]]];
  return value.flatMap((item) => flattenPoints(item));
}

function formatBboxSize(bbox: [number, number, number, number]) {
  const widthM = Math.max(0, bbox[2] - bbox[0]) * 111_000;
  const heightM = Math.max(0, bbox[3] - bbox[1]) * 111_000;
  return `${Math.round(widthM)} x ${Math.round(heightM)} m`;
}

function unique<T>(values: T[]) {
  return [...new Set(values)];
}

function randomUuid() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return randomId("uuid");
}

function randomId(prefix: string) {
  return `${prefix}-${Math.random().toString(16).slice(2, 10)}`;
}

function LabTitle({ icon, label }: { icon: ReactNode; label: string }) {
  return (
    <div className="flex items-center gap-2 text-sm font-semibold">
      <span className="text-primary">{icon}</span>
      <span>{label}</span>
    </div>
  );
}

function TextField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="block text-xs">
      <span className="font-medium text-muted-foreground">{label}</span>
      <input className="mt-1 h-9 w-full rounded-md border border-border bg-background px-2 outline-none focus:ring-2 focus:ring-ring" value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function NumberField({
  label,
  value,
  min,
  max,
  step,
  onChange,
}: {
  label: string;
  value?: number;
  min?: number;
  max?: number;
  step?: number;
  onChange: (value: number | undefined) => void;
}) {
  return (
    <label className="block text-xs">
      <span className="font-medium text-muted-foreground">{label}</span>
      <input
        className="mt-1 h-9 w-full rounded-md border border-border bg-background px-2 outline-none focus:ring-2 focus:ring-ring"
        type="number"
        value={value ?? ""}
        min={min}
        max={max}
        step={step}
        onChange={(event) => onChange(event.target.value === "" ? undefined : Number(event.target.value))}
      />
    </label>
  );
}

function SelectField({ label, value, options, onChange }: { label: string; value: string; options: { value: string; label: string }[]; onChange: (value: string) => void }) {
  return (
    <label className="block text-xs">
      <span className="font-medium text-muted-foreground">{label}</span>
      <select className="mt-1 h-9 w-full rounded-md border border-border bg-background px-2 outline-none focus:ring-2 focus:ring-ring" value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function InfoBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-sm border border-border bg-background p-2">
      <div className="font-semibold">{label}</div>
      <div className="mt-1 text-muted-foreground">{value}</div>
    </div>
  );
}
