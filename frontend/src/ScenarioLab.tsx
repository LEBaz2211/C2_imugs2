import {
  Check,
  Copy,
  Gauge,
  MapPin,
  MapPinned,
  Play,
  Plus,
  RadioTower,
  Route,
  Save,
  SlidersHorizontal,
  Target,
  Trash2,
  Users,
} from "lucide-react";
import type { Feature, FeatureCollection } from "geojson";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import type { OsmRoadImportRequest, QueriedOsmRoads, ScenarioCatalogEntry, ScenarioLaunchRequest, ScenarioLaunchResult } from "./api";
import { Badge } from "./components/ui/badge";
import { Button } from "./components/ui/button";
import { Tabs } from "./components/ui/tabs";
import type { Agent, LonLat, MapFeature } from "./types";

type ScenarioAgent = Agent;

export type ScenarioAgentPlacement = {
  scenarioId: string;
  agentId: string;
  point: LonLat;
  nonce: number;
};

type VehicleModel = {
  id: string;
  label: string;
  vehicle_type: string;
  constraints: Agent["constraints"];
  default_name?: string;
  builtin?: boolean;
};

export type ScenarioRoadImport = {
  import_id: string;
  name: string;
  bbox: [number, number, number, number];
  feature_count: number;
  geojson: FeatureCollection;
  created_at: string;
};

export type ScenarioMapView = {
  center: LonLat;
  zoom: number;
};

export type ScenarioRecord = {
  scenario_id: string;
  name: string;
  map: string;
  notes: string;
  feature_ids: string[];
  selected_agent_id: string;
  agents: ScenarioAgent[];
  road_imports: ScenarioRoadImport[];
  map_view?: ScenarioMapView;
  created_at: string;
  updated_at: string;
  runtime_active?: boolean;
  runtime_status?: string;
  runtime_version?: string;
  map_collection?: string;
};

type ScenarioLibrary = {
  active_scenario_id: string;
  scenarios: ScenarioRecord[];
};

export type ScenarioContext = {
  scenario_id: string;
  name: string;
  map: string;
  notes: string;
  agents: Agent[];
  feature_ids: string[];
  road_imports: ScenarioRoadImport[];
  roads: FeatureCollection;
  map_view?: ScenarioMapView;
};

export type ScenarioContextLibrary = {
  active_scenario_id: string;
  scenarios: ScenarioContext[];
};

type ScenarioLabProps = {
  mapFeatures: MapFeature[];
  selectedFeatureId?: string;
  pendingFeatureToAdd?: { featureId: string; nonce: number };
  pendingAgentPlacement?: ScenarioAgentPlacement;
  currentMapView?: ScenarioMapView;
  activeScenarioId?: string;
  catalogScenarios?: ScenarioCatalogEntry[];
  placingAgentId?: string;
  onScenarioAgentsChange: (agents: Agent[]) => void;
  onActiveScenarioFeaturesChange: (featureIds: string[]) => void;
  onScenarioRoadsChange: (roads?: FeatureCollection) => void;
  onScenarioLibraryChange: (library: ScenarioContextLibrary) => void;
  onSelectFeature: (featureId: string) => void;
  onImportOsmRoads: (request: OsmRoadImportRequest) => Promise<QueriedOsmRoads>;
  onLaunchScenario: (request: ScenarioLaunchRequest) => Promise<ScenarioLaunchResult>;
  onScenarioContextReset: () => void;
  onBeginPlaceAgent: (agentId: string) => void;
  onCancelPlaceAgent: () => void;
};

const STORAGE_KEY = "c2_imugs2_scenario_library";
const VEHICLE_MODEL_STORAGE_KEY = "c2_imugs2_vehicle_models";
const LEGACY_AGENT_ID = "f9992bb3-9871-451f-90a0-9207eb9fe6c5";
const DEFAULT_BBOX: [number, number, number, number] = [4.3885, 50.8428, 4.3972, 50.8467];
const EMPTY_ROAD_IMPORTS: ScenarioRoadImport[] = [];
const DEFAULT_VEHICLE_MODELS: VehicleModel[] = [
  {
    id: "themis-fr",
    label: "Themis Fr",
    vehicle_type: "UGV",
    default_name: "Themis Fr",
    constraints: { max_speed: 4.5, max_acceleration: 8, max_weight: 16, max_tilt_angle: 1.8 },
    builtin: true,
  },
  {
    id: "ugv-standard",
    label: "UGV standard",
    vehicle_type: "UGV",
    constraints: { max_speed: 4, max_acceleration: 8, max_weight: 16, max_tilt_angle: 1.8 },
    builtin: true,
  },
  {
    id: "ugv-scout",
    label: "UGV scout",
    vehicle_type: "UGV",
    constraints: { max_speed: 6, max_acceleration: 10, max_weight: 10, max_tilt_angle: 1.6 },
    builtin: true,
  },
  {
    id: "ugv-heavy",
    label: "UGV heavy",
    vehicle_type: "UGV",
    constraints: { max_speed: 2.5, max_acceleration: 5, max_weight: 40, max_tilt_angle: 1.2 },
    builtin: true,
  },
];

export function ScenarioLab({
  mapFeatures,
  selectedFeatureId,
  pendingFeatureToAdd,
  pendingAgentPlacement,
  currentMapView,
  activeScenarioId,
  catalogScenarios = [],
  placingAgentId,
  onScenarioAgentsChange,
  onActiveScenarioFeaturesChange,
  onScenarioRoadsChange,
  onScenarioLibraryChange,
  onSelectFeature,
  onImportOsmRoads,
  onLaunchScenario,
  onScenarioContextReset,
  onBeginPlaceAgent,
  onCancelPlaceAgent,
}: ScenarioLabProps) {
  const [library, setLibrary] = useState<ScenarioLibrary>(() => loadScenarioLibrary());
  const [tab, setTab] = useState("situation");
  const [appliedPendingFeatureNonce, setAppliedPendingFeatureNonce] = useState<number | undefined>();
  const [appliedPlacementNonce, setAppliedPlacementNonce] = useState<number | undefined>();
  const [launchBusy, setLaunchBusy] = useState(false);
  const [launchResult, setLaunchResult] = useState<ScenarioLaunchResult | undefined>();
  const [launchError, setLaunchError] = useState("");
  const activeScenario = library.scenarios.find((scenario) => scenario.scenario_id === library.active_scenario_id) ?? library.scenarios[0];
  const selectedFeature = mapFeatures.find((feature) => feature.feature_id === selectedFeatureId);
  const activeRoadImports = activeScenario.road_imports ?? EMPTY_ROAD_IMPORTS;
  const featureById = useMemo(() => new Map(mapFeatures.map((feature) => [feature.feature_id, feature])), [mapFeatures]);
  const scenarioFeatureIds = useMemo(
    () => activeScenario.feature_ids.filter((featureId) => !isScenarioLabImportedRoad(featureById.get(featureId))),
    [activeScenario.feature_ids, featureById],
  );
  const scenarioFeatures = useMemo(
    () => scenarioFeatureIds.flatMap((featureId) => featureById.get(featureId) ?? []),
    [featureById, scenarioFeatureIds],
  );
  const scenarioRoads = useMemo(() => roadImportsToFeatureCollection(activeRoadImports), [activeRoadImports]);
  const selectedAgent = activeScenario.agents.find((agent) => agent.agent_id === activeScenario.selected_agent_id) ?? activeScenario.agents[0];

  useEffect(() => {
    saveScenarioLibrary(library);
    onScenarioLibraryChange(scenarioContextLibraryFromLibrary(library));
    onScenarioAgentsChange(activeScenario.agents.map(toAgent));
  }, [activeScenario.agents, library, onScenarioAgentsChange, onScenarioLibraryChange]);

  useEffect(() => {
    if (!catalogScenarios.length) return;
    setLibrary((current) => mergeScenarioCatalog(current, catalogScenarios));
  }, [catalogScenarios]);

  useEffect(() => {
    if (!activeScenarioId || activeScenarioId === library.active_scenario_id) return;
    if (!library.scenarios.some((scenario) => scenario.scenario_id === activeScenarioId)) return;
    setLibrary((current) => ({ ...current, active_scenario_id: activeScenarioId }));
  }, [activeScenarioId, library.active_scenario_id, library.scenarios]);

  useEffect(() => {
    onActiveScenarioFeaturesChange(scenarioFeatureIds);
  }, [activeScenario.scenario_id, onActiveScenarioFeaturesChange, scenarioFeatureIds]);

  useEffect(() => {
    onScenarioRoadsChange(scenarioRoads);
  }, [activeScenario.scenario_id, onScenarioRoadsChange, scenarioRoads]);

  useEffect(() => {
    const importedRoads = activeScenario.feature_ids.flatMap((featureId) => {
      const feature = featureById.get(featureId);
      return isScenarioLabImportedRoad(feature) ? [feature] : [];
    });
    if (!importedRoads.length) return;
    updateActiveScenario({
      feature_ids: activeScenario.feature_ids.filter((featureId) => !isScenarioLabImportedRoad(featureById.get(featureId))),
      road_imports: [...activeRoadImports, roadImportFromMapFeatures(importedRoads)],
    });
  }, [activeScenario.scenario_id, activeScenario.feature_ids.join("|"), featureById]);

  useEffect(() => {
    if (!pendingFeatureToAdd || pendingFeatureToAdd.nonce === appliedPendingFeatureNonce) return;
    setAppliedPendingFeatureNonce(pendingFeatureToAdd.nonce);
    addFeatureIdsToActiveScenario([pendingFeatureToAdd.featureId]);
  }, [pendingFeatureToAdd?.nonce, activeScenario.scenario_id]);

  useEffect(() => {
    if (!pendingAgentPlacement || pendingAgentPlacement.nonce === appliedPlacementNonce) return;
    if (pendingAgentPlacement.scenarioId !== activeScenario.scenario_id) return;
    setAppliedPlacementNonce(pendingAgentPlacement.nonce);
    updateAgent(pendingAgentPlacement.agentId, { current_location: pendingAgentPlacement.point });
  }, [pendingAgentPlacement?.nonce, activeScenario.scenario_id]);

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
    onScenarioContextReset();
    setLibrary((current) => {
      const scenario = defaultScenario(nextBlankScenarioName(current.scenarios));
      return {
        active_scenario_id: scenario.scenario_id,
        scenarios: [...current.scenarios, scenario],
      };
    });
  }

  function duplicateScenario() {
    onScenarioContextReset();
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
    onScenarioContextReset();
    setLibrary((current) => {
      const scenarios = current.scenarios.filter((scenario) => scenario.scenario_id !== activeScenario.scenario_id);
      return {
        active_scenario_id: scenarios[0]?.scenario_id ?? "",
        scenarios,
      };
    });
  }

  function addSelectedFeature() {
    if (!selectedFeature || activeScenario.feature_ids.includes(selectedFeature.feature_id)) return;
    addFeatureIdsToActiveScenario([selectedFeature.feature_id]);
  }

  function addFeatureIdsToActiveScenario(featureIds: string[]) {
    const next = unique([...activeScenario.feature_ids, ...featureIds]);
    if (next.length === activeScenario.feature_ids.length) return;
    updateActiveScenario({ feature_ids: next });
  }

  function removeFeature(featureId: string) {
    updateActiveScenario({ feature_ids: activeScenario.feature_ids.filter((id) => id !== featureId) });
  }

  function clearScenarioContents() {
    onScenarioContextReset();
    updateActiveScenario({
      feature_ids: [],
      agents: [],
      selected_agent_id: "",
      road_imports: [],
    });
  }

  function saveCurrentMapView() {
    if (!currentMapView) return;
    updateActiveScenario({ map_view: currentMapView });
  }

  function addAgent(model: VehicleModel = DEFAULT_VEHICLE_MODELS[0]) {
    const agent = createScenarioAgent(nextAgentName(activeScenario.agents, model), undefined, model);
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
    appendRoadImport(activeScenario.scenario_id, roadImportFromQuery(result));
    return result;
  }

  function appendRoadImport(scenarioId: string, roadImport: ScenarioRoadImport) {
    setLibrary((current) => {
      const updatedAt = new Date().toISOString();
      return {
        ...current,
        scenarios: current.scenarios.map((scenario) =>
          scenario.scenario_id === scenarioId
            ? { ...scenario, road_imports: [...(scenario.road_imports ?? []), roadImport], updated_at: updatedAt }
            : scenario,
        ),
      };
    });
  }

  async function launchActiveScenario() {
    setLaunchBusy(true);
    setLaunchError("");
    setLaunchResult(undefined);
    try {
      const result = await onLaunchScenario({
        scenario_id: activeScenario.scenario_id,
        name: activeScenario.name,
        map: activeScenario.map,
        notes: activeScenario.notes,
        agents: activeScenario.agents.map(toAgent),
        feature_ids: scenarioFeatureIds,
        road_imports: activeRoadImports,
      });
      setLaunchResult(result);
    } catch (err) {
      setLaunchError(err instanceof Error ? err.message : String(err));
    } finally {
      setLaunchBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-4 rounded-md border border-border bg-panel p-4">
        <div className="min-w-0">
          <LabTitle icon={<SlidersHorizontal className="h-4 w-4" />} label="Scenario Lab" />
          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span>{activeScenario.name}</span>
            <span>{activeScenario.agents.length} vehicles</span>
            <span>{scenarioFeatures.length} assets</span>
            <span>{activeRoadImports.length} road sections</span>
          </div>
        </div>
        <div className="flex min-w-0 shrink-0 flex-wrap items-center justify-end gap-2">
          <select
            className="h-8 max-w-56 min-w-0 rounded-md border border-border bg-background px-2 text-xs outline-none focus:ring-2 focus:ring-ring"
            value={activeScenario.scenario_id}
            onChange={(event) => {
              onScenarioContextReset();
              setLibrary((current) => ({ ...current, active_scenario_id: event.target.value }));
            }}
          >
            {library.scenarios.map((scenario) => (
              <option key={scenario.scenario_id} value={scenario.scenario_id}>
                {scenario.name}{scenario.runtime_active ? " (active)" : ""}
              </option>
            ))}
          </select>
          <Button size="icon" variant="outline" onClick={createScenario} title="New scenario">
            <Plus className="h-4 w-4" />
          </Button>
          <Button size="sm" disabled={launchBusy || activeScenario.agents.length === 0} onClick={launchActiveScenario} title="Freeze the scenario map, switch the planner, and verify its ROS vehicles">
            <Play className="h-4 w-4" />
            {launchBusy ? "Activating" : "Activate"}
          </Button>
          <Button size="icon" variant="outline" onClick={duplicateScenario} title="Duplicate scenario">
            <Copy className="h-4 w-4" />
          </Button>
          <Button size="icon" variant="ghost" disabled={library.scenarios.length <= 1} onClick={deleteScenario} title="Delete scenario">
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {(launchResult || launchError) && (
        <div className={`rounded-md border px-3 py-2 text-xs ${launchError ? "border-red-200 bg-red-50 text-red-900" : "border-border bg-panel text-muted-foreground"}`}>
          {launchError ? (
            launchError
          ) : (
            <span>
              <span className="font-semibold text-foreground">{launchResult?.ready ? "Ready" : launchResult?.status}</span>{" "}
              {launchResult?.message}
              {launchResult?.host_command && !launchResult.docker_started ? <span className="ml-1 font-mono">{launchResult.host_command}</span> : null}
            </span>
          )}
        </div>
      )}

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
          currentMapView={currentMapView}
          onSaveCurrentMapView={saveCurrentMapView}
          onClearScenarioContents={clearScenarioContents}
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
          placingAgentId={placingAgentId}
          onBeginPlaceAgent={onBeginPlaceAgent}
          onCancelPlaceAgent={onCancelPlaceAgent}
        />
      )}

      {tab === "roads" && (
        <RoadImportPanel
          key={activeScenario.scenario_id}
          selectedFeature={selectedFeature}
          scenarioFeatures={scenarioFeatures}
          roadImports={activeRoadImports}
          onImportRoads={importRoads}
          onRemoveRoadImport={(importId) => updateActiveScenario({ road_imports: activeRoadImports.filter((item) => item.import_id !== importId) })}
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
  currentMapView,
  onSaveCurrentMapView,
  onClearScenarioContents,
}: {
  scenario: ScenarioRecord;
  selectedFeature?: MapFeature;
  scenarioFeatures: MapFeature[];
  onUpdateScenario: (patch: Partial<ScenarioRecord>) => void;
  onAddSelectedFeature: () => void;
  onRemoveFeature: (featureId: string) => void;
  onSelectFeature: (featureId: string) => void;
  currentMapView?: ScenarioMapView;
  onSaveCurrentMapView: () => void;
  onClearScenarioContents: () => void;
}) {
  const grouped = groupByFeatureType(scenarioFeatures);
  const hasContents = scenario.feature_ids.length > 0 || scenario.agents.length > 0 || (scenario.road_imports ?? []).length > 0;
  return (
    <div className="space-y-4">
      <div className="rounded-md border border-border bg-panel p-4">
        <div className="flex items-center justify-between gap-3">
          <LabTitle icon={<Save className="h-4 w-4" />} label="Scenario" />
          <Button size="sm" variant="outline" disabled={!hasContents} onClick={onClearScenarioContents} title="Remove all vehicles, assets, and road sections from this scenario">
            <Trash2 className="h-4 w-4" />
            Clear
          </Button>
        </div>
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
        <div className="mt-3 rounded-sm border border-border bg-background p-3 text-xs">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="min-w-0">
              <div className="font-semibold">Opening Map View</div>
              <div className="mt-1 text-muted-foreground">
                {scenario.map_view
                  ? `${scenario.map_view.center[0].toFixed(6)}, ${scenario.map_view.center[1].toFixed(6)} · z${scenario.map_view.zoom}`
                  : "No saved opening view"}
              </div>
            </div>
            <Button size="sm" variant="outline" disabled={!currentMapView} onClick={onSaveCurrentMapView} title="Use the current map center and zoom when this scenario opens">
              <MapPinned className="h-4 w-4" />
              Set View
            </Button>
          </div>
        </div>
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
        <Button
          size="icon"
          variant="ghost"
          onClick={(event) => {
            event.stopPropagation();
            onRemoveFeature(feature.feature_id);
          }}
          title="Remove from scenario"
        >
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
  placingAgentId,
  onBeginPlaceAgent,
  onCancelPlaceAgent,
}: {
  agents: ScenarioAgent[];
  selectedAgent?: ScenarioAgent;
  onSelectAgent: (agentId: string) => void;
  onAddAgent: (model?: VehicleModel) => void;
  onCloneAgent: (agent: ScenarioAgent) => void;
  onRemoveAgent: (agentId: string) => void;
  onUpdateAgent: (agentId: string, patch: Partial<ScenarioAgent>) => void;
  placingAgentId?: string;
  onBeginPlaceAgent: (agentId: string) => void;
  onCancelPlaceAgent: () => void;
}) {
  const [vehicleModels, setVehicleModels] = useState<VehicleModel[]>(() => loadVehicleModels());
  const [selectedModelId, setSelectedModelId] = useState(DEFAULT_VEHICLE_MODELS[0].id);
  const selectedModel = vehicleModels.find((model) => model.id === selectedModelId) ?? vehicleModels[0] ?? DEFAULT_VEHICLE_MODELS[0];

  useEffect(() => {
    if (vehicleModels.some((model) => model.id === selectedModelId)) return;
    setSelectedModelId(vehicleModels[0]?.id ?? DEFAULT_VEHICLE_MODELS[0].id);
  }, [selectedModelId, vehicleModels]);

  function saveSelectedAgentAsModel() {
    if (!selectedAgent) return;
    const model: VehicleModel = {
      id: randomId("vehicle-model"),
      label: uniqueVehicleModelName(`${selectedAgent.name || selectedAgent.vehicle_type || "Vehicle"} model`, vehicleModels),
      vehicle_type: selectedAgent.vehicle_type || "UGV",
      constraints: { ...selectedAgent.constraints },
    };
    setVehicleModels((current) => {
      const customModels = [...current.filter((item) => !item.builtin), model];
      saveCustomVehicleModels(customModels);
      return [...DEFAULT_VEHICLE_MODELS, ...customModels];
    });
    setSelectedModelId(model.id);
  }

  function deleteSelectedModel() {
    if (selectedModel.builtin) return;
    setVehicleModels((current) => {
      const customModels = current.filter((item) => !item.builtin && item.id !== selectedModel.id);
      saveCustomVehicleModels(customModels);
      return [...DEFAULT_VEHICLE_MODELS, ...customModels];
    });
    setSelectedModelId(DEFAULT_VEHICLE_MODELS[0].id);
  }

  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-[260px_minmax(0,1fr)]">
      <div className="min-w-0 space-y-2">
        <div className="flex items-center justify-between">
          <LabTitle icon={<Users className="h-4 w-4" />} label="Vehicles" />
          <div className="flex gap-1">
            <Button size="icon" variant="outline" onClick={() => onAddAgent(selectedModel)} title="Add vehicle">
              <Plus className="h-4 w-4" />
            </Button>
          </div>
        </div>
        <div className="rounded-md border border-border bg-panel p-2 text-xs">
          <div className="flex gap-2">
            <select className="h-8 min-w-0 flex-1 rounded-md border border-border bg-background px-2 outline-none focus:ring-2 focus:ring-ring" value={selectedModelId} onChange={(event) => setSelectedModelId(event.target.value)}>
              {vehicleModels.map((model) => (
                <option key={model.id} value={model.id}>{model.label}</option>
              ))}
            </select>
            <Button size="sm" variant="outline" onClick={() => onAddAgent(selectedModel)}>
              <Plus className="h-4 w-4" />
              Add
            </Button>
          </div>
          <div className="mt-2 flex flex-wrap gap-1 text-muted-foreground">
            <Badge>{selectedModel.vehicle_type}</Badge>
            <Badge>{selectedModel.constraints.max_speed ?? 0} m/s</Badge>
            <Badge>{selectedModel.constraints.max_weight ?? 0} kg</Badge>
            {selectedModel.builtin ? <Badge>built-in</Badge> : <Badge tone="ok">custom</Badge>}
          </div>
          <div className="mt-2 flex flex-wrap gap-2">
            <Button size="sm" variant="outline" disabled={!selectedAgent} onClick={saveSelectedAgentAsModel}>
              <Save className="h-4 w-4" />
              Save Model
            </Button>
            <Button size="icon" variant="ghost" disabled={selectedModel.builtin} onClick={deleteSelectedModel} title="Delete custom model">
              <Trash2 className="h-4 w-4" />
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
              <Badge>{agent.vehicle_type}</Badge>
            </div>
            <div className="mt-1 truncate text-xs text-muted-foreground">{agent.agent_id}</div>
            <div className="mt-2 flex flex-wrap gap-1">
              <Badge>{agent.status}</Badge>
              {typeof agent.constraints.max_speed === "number" && <Badge>{agent.constraints.max_speed.toFixed(1)} m/s</Badge>}
            </div>
          </button>
        ))}
      </div>

      {selectedAgent ? (
        <AgentEditor
          agent={selectedAgent}
          onClone={() => onCloneAgent(selectedAgent)}
          onRemove={() => onRemoveAgent(selectedAgent.agent_id)}
          onUpdate={(patch) => onUpdateAgent(selectedAgent.agent_id, patch)}
          placing={placingAgentId === selectedAgent.agent_id}
          onBeginPlace={() => onBeginPlaceAgent(selectedAgent.agent_id)}
          onCancelPlace={onCancelPlaceAgent}
        />
      ) : (
        <div className="rounded-md border border-border bg-panel p-4 text-sm text-muted-foreground">No vehicle selected.</div>
      )}
    </div>
  );
}

function AgentEditor({
  agent,
  onClone,
  onRemove,
  onUpdate,
  placing,
  onBeginPlace,
  onCancelPlace,
}: {
  agent: ScenarioAgent;
  onClone: () => void;
  onRemove: () => void;
  onUpdate: (patch: Partial<ScenarioAgent>) => void;
  placing: boolean;
  onBeginPlace: () => void;
  onCancelPlace: () => void;
}) {
  function updateConstraint(key: keyof Agent["constraints"], value: number | undefined) {
    onUpdate({ constraints: { ...agent.constraints, [key]: value } });
  }

  return (
    <div className="min-w-0 space-y-4">
      <div className="min-w-0 overflow-hidden rounded-md border border-border bg-panel p-4">
        <div className="flex items-center justify-between">
          <LabTitle icon={<RadioTower className="h-4 w-4" />} label="Identity" />
          <div className="flex gap-2">
            <Button size="sm" variant="outline" onClick={onClone}>
              <Copy className="h-4 w-4" />
              Clone
            </Button>
            <Button size="sm" variant={placing ? "secondary" : "outline"} onClick={placing ? onCancelPlace : onBeginPlace}>
              <MapPin className="h-4 w-4" />
              {placing ? "Placing" : "Place"}
            </Button>
            <Button size="sm" variant="ghost" onClick={onRemove}>
              <Trash2 className="h-4 w-4" />
              Remove
            </Button>
          </div>
        </div>
        <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
          <TextField label="Name" value={agent.name} onChange={(value) => onUpdate({ name: value })} />
          <TextField label="Vehicle type" value={agent.vehicle_type} onChange={(value) => onUpdate({ vehicle_type: value })} />
          <TextField label="Agent UUID" value={agent.agent_id} onChange={(value) => onUpdate({ agent_id: value })} />
          <NumberField label="Longitude" value={agent.current_location[0]} step={0.000001} onChange={(value) => onUpdate({ current_location: [value ?? agent.current_location[0], agent.current_location[1]] })} />
          <NumberField label="Latitude" value={agent.current_location[1]} step={0.000001} onChange={(value) => onUpdate({ current_location: [agent.current_location[0], value ?? agent.current_location[1]] })} />
        </div>
      </div>

      <div className="min-w-0 overflow-hidden rounded-md border border-border bg-panel p-4">
        <LabTitle icon={<Gauge className="h-4 w-4" />} label="Constraints" />
        <div className="mt-3 grid grid-cols-2 gap-3 2xl:grid-cols-4">
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
  roadImports,
  onImportRoads,
  onRemoveRoadImport,
}: {
  selectedFeature?: MapFeature;
  scenarioFeatures: MapFeature[];
  roadImports: ScenarioRoadImport[];
  onImportRoads: (request: OsmRoadImportRequest) => Promise<QueriedOsmRoads>;
  onRemoveRoadImport: (importId: string) => void;
}) {
  const initialPolygon = polygonFromFeature(selectedFeature) ?? polygonFromFeatures(scenarioFeatures);
  const [polygon, setPolygon] = useState<LonLat[] | undefined>(() => initialPolygon);
  const [bbox, setBbox] = useState<[number, number, number, number]>(() => (initialPolygon ? bboxFromPoints(initialPolygon) : undefined) ?? DEFAULT_BBOX);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<QueriedOsmRoads | undefined>();
  const [error, setError] = useState("");
  const selectedPolygon = polygonFromFeature(selectedFeature);
  const scenarioPolygon = polygonFromFeatures(scenarioFeatures);

  function useSelectedBbox() {
    if (!selectedPolygon) return;
    setPolygon(selectedPolygon);
    const next = bboxFromPoints(selectedPolygon);
    if (next) setBbox(next);
  }

  function useScenarioBbox() {
    if (!scenarioPolygon) return;
    setPolygon(scenarioPolygon);
    const next = bboxFromPoints(scenarioPolygon);
    if (next) setBbox(next);
  }

  async function submit() {
    if (!polygon) {
      setError("Select a geofence/workspace polygon or add one to the scenario first.");
      return;
    }
    setBusy(true);
    setError("");
    setResult(undefined);
    try {
      setResult(await onImportRoads({ bbox, polygon }));
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
          <LabTitle icon={<Route className="h-4 w-4" />} label="Frozen OSM Roads" />
          <Badge>{formatBboxSize(bbox)}</Badge>
        </div>
        <div className="mt-3 grid grid-cols-3 gap-3 text-xs">
          <InfoBlock label="Source" value={polygon ? "Selected polygon" : "No polygon"} />
          <InfoBlock label="Vertices" value={String(polygon?.length ?? 0)} />
          <InfoBlock label="BBox" value={bbox.map((value) => value.toFixed(5)).join(", ")} />
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          <Button size="sm" variant="outline" disabled={!selectedPolygon} onClick={useSelectedBbox}>
            <Target className="h-4 w-4" />
            From Selected Polygon
          </Button>
          <Button size="sm" variant="outline" disabled={!scenarioPolygon} onClick={useScenarioBbox}>
            <MapPinned className="h-4 w-4" />
            From Scenario Geofence
          </Button>
          <Button size="sm" onClick={submit} disabled={busy || !polygon}>
            <Check className="h-4 w-4" />
            {busy ? "Downloading" : "Download Inside Polygon"}
          </Button>
        </div>
      </div>

      {error && <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-900">{error}</div>}
      {result && (
        <div className="rounded-md border border-border bg-panel p-4">
          <div className="flex items-center justify-between">
            <LabTitle icon={<Route className="h-4 w-4" />} label="Import Result" />
            <Badge tone={result.feature_count > 0 ? "ok" : "warn"}>{result.feature_count} ways</Badge>
          </div>
          <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
            <InfoBlock label="Section" value="Scenario local" />
            <InfoBlock label="Ways" value={String(result.feature_count)} />
            <InfoBlock label="BBox" value={result.bbox.map((value) => value.toFixed(5)).join(", ")} />
          </div>
        </div>
      )}

      <div className="rounded-md border border-border bg-panel p-4">
        <div className="flex items-center justify-between">
          <LabTitle icon={<Route className="h-4 w-4" />} label="Road Sections" />
          <Badge>{roadImports.length}</Badge>
        </div>
        <div className="mt-3 space-y-2">
          {roadImports.length ? (
            roadImports.map((roadImport) => (
              <div key={roadImport.import_id} className="flex items-center justify-between gap-3 rounded-sm border border-border bg-background px-3 py-2 text-xs">
                <div className="min-w-0">
                  <div className="truncate font-medium">{roadImport.name}</div>
                  <div className="truncate text-muted-foreground">{roadImport.feature_count} OSM ways</div>
                </div>
                <Button size="icon" variant="ghost" onClick={() => onRemoveRoadImport(roadImport.import_id)} title="Remove road section from scenario">
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))
          ) : (
            <div className="rounded-sm border border-border bg-background px-3 py-2 text-xs text-muted-foreground">No road sections added.</div>
          )}
        </div>
      </div>
    </div>
  );
}

function defaultScenario(name = "Blank scenario"): ScenarioRecord {
  const now = new Date().toISOString();
  return {
    scenario_id: randomId("scenario"),
    name,
    map: "rma",
    notes: "",
    feature_ids: [],
    selected_agent_id: "",
    agents: [],
    road_imports: [],
    map_view: undefined,
    created_at: now,
    updated_at: now,
  };
}

function loadScenarioLibrary(): ScenarioLibrary {
  if (typeof window !== "undefined") {
    try {
      const stored = JSON.parse(window.localStorage.getItem(STORAGE_KEY) ?? "null") as ScenarioLibrary | null;
      if (stored?.scenarios?.length) return normalizeLibrary(stored);
    } catch {
      // Fall through to default library.
    }
  }
  const scenario = defaultScenario();
  return { active_scenario_id: scenario.scenario_id, scenarios: [scenario] };
}

function normalizeLibrary(stored: ScenarioLibrary): ScenarioLibrary {
  const scenarios = stored.scenarios.map((scenario) => {
    const featureIds = unique(scenario.feature_ids ?? []);
    const roadImports = normalizeRoadImports((scenario as Partial<ScenarioRecord>).road_imports);
    const rawAgents = scenario.agents ?? [];
    return {
      ...defaultScenario(),
      ...scenario,
      agents: isOldRuntimeSeedScenario(scenario, rawAgents, featureIds, roadImports) ? [] : rawAgents.map((agent) => scenarioAgentFromAgent(agent)),
      feature_ids: featureIds,
      road_imports: roadImports,
      map_view: normalizeMapView((scenario as Partial<ScenarioRecord>).map_view),
    };
  });
  return {
    active_scenario_id: scenarios.some((scenario) => scenario.scenario_id === stored.active_scenario_id) ? stored.active_scenario_id : scenarios[0]?.scenario_id ?? "",
    scenarios,
  };
}

function mergeScenarioCatalog(library: ScenarioLibrary, catalog: ScenarioCatalogEntry[]): ScenarioLibrary {
  const catalogById = new Map(catalog.map((scenario) => [scenario.scenario_id, scenarioRecordFromCatalog(scenario)]));
  const scenarios = library.scenarios.map((local) => {
    const saved = catalogById.get(local.scenario_id);
    if (!saved) return local;
    catalogById.delete(local.scenario_id);
    return {
      ...saved,
      ...local,
      agents: local.agents.length ? local.agents : saved.agents,
      selected_agent_id: local.selected_agent_id || saved.selected_agent_id,
      feature_ids: local.feature_ids.length ? local.feature_ids : saved.feature_ids,
      road_imports: local.road_imports.length ? local.road_imports : saved.road_imports,
      runtime_active: saved.runtime_active,
      runtime_status: saved.runtime_status,
      runtime_version: saved.runtime_version,
      map_collection: saved.map_collection,
    };
  });
  scenarios.push(...catalogById.values());
  return { ...library, scenarios };
}

function scenarioRecordFromCatalog(scenario: ScenarioCatalogEntry): ScenarioRecord {
  const agents = (scenario.agents ?? []).map((agent) => scenarioAgentFromAgent(agent));
  return {
    scenario_id: scenario.scenario_id,
    name: scenario.name || scenario.scenario_id,
    map: scenario.map || "rma",
    notes: scenario.notes || "",
    feature_ids: unique(scenario.feature_ids ?? []),
    selected_agent_id: scenario.selected_agent_id || agents[0]?.agent_id || "",
    agents,
    road_imports: normalizeRoadImports(scenario.road_imports),
    created_at: scenario.created_at || new Date().toISOString(),
    updated_at: scenario.updated_at || scenario.created_at || new Date().toISOString(),
    runtime_active: scenario.runtime_active,
    runtime_status: scenario.runtime_status,
    runtime_version: scenario.version,
    map_collection: scenario.map_collection,
  };
}

export function loadScenarioContextLibrary(): ScenarioContextLibrary {
  return scenarioContextLibraryFromLibrary(loadScenarioLibrary());
}

export function saveActiveScenarioId(scenarioId: string): ScenarioContextLibrary {
  const library = loadScenarioLibrary();
  const activeScenarioId = library.scenarios.some((scenario) => scenario.scenario_id === scenarioId) ? scenarioId : library.active_scenario_id;
  const next = { ...library, active_scenario_id: activeScenarioId };
  saveScenarioLibrary(next);
  return scenarioContextLibraryFromLibrary(next);
}

function scenarioContextLibraryFromLibrary(library: ScenarioLibrary): ScenarioContextLibrary {
  return {
    active_scenario_id: library.active_scenario_id,
    scenarios: library.scenarios.map(scenarioContextFromRecord),
  };
}

function scenarioContextFromRecord(scenario: ScenarioRecord): ScenarioContext {
  const roadImports = normalizeRoadImports(scenario.road_imports);
  return {
    scenario_id: scenario.scenario_id,
    name: scenario.name,
    map: scenario.map,
    notes: scenario.notes,
    agents: scenario.agents.map(toAgent),
    feature_ids: unique(scenario.feature_ids ?? []),
    road_imports: roadImports,
    roads: roadImportsToFeatureCollection(roadImports),
    map_view: normalizeMapView(scenario.map_view),
  };
}

function nextBlankScenarioName(scenarios: ScenarioRecord[]) {
  const base = "Blank scenario";
  const used = new Set(scenarios.map((scenario) => scenario.name));
  if (!used.has(base)) return base;
  for (let index = 2; index < 10_000; index += 1) {
    const name = `${base} ${index}`;
    if (!used.has(name)) return name;
  }
  return `${base} ${scenarios.length + 1}`;
}

function nextAgentName(agents: ScenarioAgent[], model: VehicleModel) {
  const base = model.default_name || model.label || "Vehicle";
  const used = new Set(agents.map((agent) => agent.name));
  if (!used.has(base)) return base;
  for (let index = 2; index < 10_000; index += 1) {
    const name = `${base} ${index}`;
    if (!used.has(name)) return name;
  }
  return `${base} ${agents.length + 1}`;
}

function isOldRuntimeSeedScenario(
  scenario: Partial<ScenarioRecord>,
  agents: (ScenarioAgent & { source?: string })[],
  featureIds: string[],
  roadImports: ScenarioRoadImport[],
) {
  if (agents.length !== 1 || featureIds.length || roadImports.length) return false;
  const agent = agents[0];
  return agent.agent_id === LEGACY_AGENT_ID && (agent.source === "legacy_connected" || scenario.name === "New scenario");
}

function saveScenarioLibrary(library: ScenarioLibrary) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(library));
}

function loadVehicleModels(): VehicleModel[] {
  if (typeof window === "undefined") return DEFAULT_VEHICLE_MODELS;
  try {
    const stored = JSON.parse(window.localStorage.getItem(VEHICLE_MODEL_STORAGE_KEY) ?? "[]");
    return [...DEFAULT_VEHICLE_MODELS, ...normalizeCustomVehicleModels(stored)];
  } catch {
    return DEFAULT_VEHICLE_MODELS;
  }
}

function saveCustomVehicleModels(models: VehicleModel[]) {
  if (typeof window === "undefined") return;
  const payload = normalizeCustomVehicleModels(models).map((model) => ({
    id: model.id,
    label: model.label,
    vehicle_type: model.vehicle_type,
    constraints: model.constraints,
  }));
  window.localStorage.setItem(VEHICLE_MODEL_STORAGE_KEY, JSON.stringify(payload));
}

function normalizeCustomVehicleModels(value: unknown): VehicleModel[] {
  if (!Array.isArray(value)) return [];
  const used = new Set(DEFAULT_VEHICLE_MODELS.map((model) => model.id));
  return value.flatMap((item) => {
    const model = normalizeVehicleModel(item, used);
    if (!model) return [];
    used.add(model.id);
    return [model];
  });
}

function normalizeMapView(value: unknown): ScenarioMapView | undefined {
  if (!value || typeof value !== "object") return undefined;
  const view = value as Partial<ScenarioMapView>;
  if (!Array.isArray(view.center) || view.center.length < 2) return undefined;
  const lon = Number(view.center[0]);
  const lat = Number(view.center[1]);
  const zoom = Number(view.zoom);
  if (!Number.isFinite(lon) || !Number.isFinite(lat) || !Number.isFinite(zoom)) return undefined;
  return {
    center: [Number(lon.toFixed(7)), Number(lat.toFixed(7))],
    zoom: Math.max(1, Math.min(22, Math.round(zoom))),
  };
}

function normalizeVehicleModel(value: unknown, usedIds: Set<string>): VehicleModel | undefined {
  if (!value || typeof value !== "object") return undefined;
  const item = value as Partial<VehicleModel>;
  const id = String(item.id || randomId("vehicle-model"));
  if (usedIds.has(id)) return undefined;
  const label = String(item.label || item.vehicle_type || "Vehicle model").trim();
  const vehicleType = String(item.vehicle_type || "UGV").trim();
  return {
    id,
    label: label || "Vehicle model",
    vehicle_type: vehicleType || "UGV",
    constraints: normalizeModelConstraints(item.constraints),
  };
}

function normalizeModelConstraints(value: unknown): Agent["constraints"] {
  const source = value && typeof value === "object" ? (value as Record<string, unknown>) : {};
  return {
    max_speed: numberOrUndefined(source.max_speed),
    max_acceleration: numberOrUndefined(source.max_acceleration),
    max_deceleration: numberOrUndefined(source.max_deceleration),
    max_jerk: numberOrUndefined(source.max_jerk),
    max_straight_slope: numberOrUndefined(source.max_straight_slope),
    max_side_slope: numberOrUndefined(source.max_side_slope),
    max_weight: numberOrUndefined(source.max_weight),
    max_tilt_angle: numberOrUndefined(source.max_tilt_angle),
  };
}

function numberOrUndefined(value: unknown) {
  if (value === undefined || value === null || value === "") return undefined;
  const number = Number(value);
  return Number.isFinite(number) ? number : undefined;
}

function uniqueVehicleModelName(base: string, models: VehicleModel[]) {
  const cleanBase = base.trim() || "Vehicle model";
  const used = new Set(models.map((model) => model.label));
  if (!used.has(cleanBase)) return cleanBase;
  for (let index = 2; index < 10_000; index += 1) {
    const candidate = `${cleanBase} ${index}`;
    if (!used.has(candidate)) return candidate;
  }
  return `${cleanBase} ${models.length + 1}`;
}

function normalizeRoadImports(value: unknown): ScenarioRoadImport[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((item) => {
    if (!item || typeof item !== "object") return [];
    const roadImport = item as Partial<ScenarioRoadImport>;
    if (!roadImport.geojson || roadImport.geojson.type !== "FeatureCollection" || !Array.isArray(roadImport.geojson.features)) return [];
    return [
      {
        import_id: String(roadImport.import_id || randomId("road-section")),
        name: String(roadImport.name || "OSM road section"),
        bbox: normalizeBbox(roadImport.bbox) ?? bboxFromFeatureCollection(roadImport.geojson) ?? DEFAULT_BBOX,
        feature_count: Number(roadImport.feature_count ?? roadImport.geojson.features.length),
        geojson: roadImport.geojson,
        created_at: String(roadImport.created_at || new Date().toISOString()),
      },
    ];
  });
}

function roadImportFromQuery(result: QueriedOsmRoads): ScenarioRoadImport {
  const now = new Date().toISOString();
  return {
    import_id: randomId("road-section"),
    name: `OSM road section ${formatBboxLabel(result.bbox)}`,
    bbox: result.bbox,
    feature_count: result.feature_count,
    geojson: result.geojson,
    created_at: now,
  };
}

function roadImportFromMapFeatures(features: MapFeature[]): ScenarioRoadImport {
  const geojson: FeatureCollection = {
    type: "FeatureCollection",
    features: features.map(mapFeatureToGeoJsonFeature),
  };
  const bbox = bboxFromFeatures(features) ?? DEFAULT_BBOX;
  return {
    import_id: randomId("road-section"),
    name: `OSM road section ${formatBboxLabel(bbox)}`,
    bbox,
    feature_count: features.length,
    geojson,
    created_at: new Date().toISOString(),
  };
}

function roadImportsToFeatureCollection(roadImports: ScenarioRoadImport[] = []): FeatureCollection {
  return {
    type: "FeatureCollection",
    features: roadImports.flatMap((roadImport) =>
      roadImport.geojson.features.map((feature) => ({
        ...feature,
        properties: {
          ...(feature.properties ?? {}),
          feature_type: "scenario_osm_road",
          scenario_road_import_id: roadImport.import_id,
        },
      })),
    ),
  };
}

function mapFeatureToGeoJsonFeature(feature: MapFeature): Feature {
  return {
    type: "Feature",
    id: feature.feature_id,
    properties: {
      ...feature.properties,
      feature_id: feature.feature_id,
      feature_type: "scenario_osm_road",
      name: feature.name,
      source_tool: "scenario_lab_osm_section",
    },
    geometry: feature.geometry as Feature["geometry"],
  };
}

function isScenarioLabImportedRoad(feature?: MapFeature): feature is MapFeature {
  return feature?.feature_type === "road" && feature.properties?.source_tool === "scenario_lab_osm_import";
}

function scenarioAgentFromAgent(agent: Agent): ScenarioAgent {
  const constraints = agent.constraints ?? {};
  return {
    agent_id: agent.agent_id,
    name: agent.name,
    vehicle_type: agent.vehicle_type,
    status: agent.status || "available",
    current_location: agent.current_location,
    constraints: {
      max_speed: constraints.max_speed ?? 4,
      max_acceleration: constraints.max_acceleration ?? 0,
      max_deceleration: constraints.max_deceleration ?? 0,
      max_jerk: constraints.max_jerk ?? 0,
      max_straight_slope: constraints.max_straight_slope ?? 0,
      max_side_slope: constraints.max_side_slope ?? 0,
      max_weight: constraints.max_weight ?? 0,
      max_tilt_angle: constraints.max_tilt_angle ?? 0,
    },
    capabilities: [],
  };
}

function createScenarioAgent(name: string, agentId = randomUuid(), model: VehicleModel = DEFAULT_VEHICLE_MODELS[0]): ScenarioAgent {
  return scenarioAgentFromAgent(
    {
      agent_id: agentId,
      name,
      vehicle_type: model.vehicle_type,
      status: "available",
      current_location: [4.392588, 50.844317],
      constraints: { ...model.constraints },
      capabilities: [],
    },
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

function polygonFromFeatures(features: MapFeature[]): LonLat[] | undefined {
  const polygons = features
    .filter((feature) => (feature.feature_type === "geofence" || feature.feature_type === "workspace") && feature.geometry.type === "Polygon")
    .flatMap((feature) => {
      const polygon = polygonFromFeature(feature);
      return polygon ? [polygon] : [];
    });
  if (!polygons.length) return undefined;
  return polygons.reduce((largest, current) => (polygonArea(current) > polygonArea(largest) ? current : largest));
}

function polygonFromFeature(feature?: MapFeature): LonLat[] | undefined {
  if (!feature || feature.geometry.type !== "Polygon" || !Array.isArray(feature.geometry.coordinates)) return undefined;
  const ring = feature.geometry.coordinates[0];
  if (!Array.isArray(ring)) return undefined;
  const points = ring.filter((point): point is LonLat => Array.isArray(point) && typeof point[0] === "number" && typeof point[1] === "number");
  return points.length >= 3 ? points : undefined;
}

function polygonArea(points: LonLat[]) {
  let area = 0;
  for (let index = 0; index < points.length; index += 1) {
    const current = points[index];
    const next = points[(index + 1) % points.length];
    area += current[0] * next[1] - next[0] * current[1];
  }
  return Math.abs(area) / 2;
}

function bboxFromFeatureCollection(collection: FeatureCollection): [number, number, number, number] | undefined {
  const points = collection.features.flatMap((feature) => flattenPoints(geoJsonCoordinates(feature.geometry)));
  return bboxFromPoints(points);
}

function bboxFromFeature(feature: MapFeature): [number, number, number, number] | undefined {
  return bboxFromPoints(flattenPoints(feature.geometry.coordinates));
}

function normalizeBbox(value: unknown): [number, number, number, number] | undefined {
  if (!Array.isArray(value) || value.length !== 4) return undefined;
  const numbers = value.map((item) => Number(item));
  if (numbers.some((item) => !Number.isFinite(item))) return undefined;
  return [numbers[0], numbers[1], numbers[2], numbers[3]];
}

function geoJsonCoordinates(geometry: Feature["geometry"]) {
  return geometry && "coordinates" in geometry ? geometry.coordinates : undefined;
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

function formatBboxLabel(bbox: [number, number, number, number]) {
  return bbox.map((value) => value.toFixed(3)).join(",");
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

function InfoBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-sm border border-border bg-background p-2">
      <div className="font-semibold">{label}</div>
      <div className="mt-1 text-muted-foreground">{value}</div>
    </div>
  );
}
