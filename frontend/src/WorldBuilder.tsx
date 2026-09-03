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
import { useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from "react";
import {
  ApiError,
  createVehicleModel,
  createWorld,
  deleteVehicleModel,
  deleteWorld,
  deleteWorldRoadImport,
  getVehicleModels,
  queryWorldRoadImport,
  updateWorld,
  type OsmRoadImportRequest,
  type QueriedOsmRoads,
  type VehicleModelRecord,
  type WorldCatalogEntry,
  type WorldLaunchRequest,
  type WorldLaunchResult,
} from "./api";
import { Badge } from "./components/ui/badge";
import { Button } from "./components/ui/button";
import { Tabs } from "./components/ui/tabs";
import type { Agent, LonLat, MapFeature } from "./types";

type WorldAgent = Agent;

export type WorldAgentPlacement = {
  worldId: string;
  agentId: string;
  point: LonLat;
  nonce: number;
};

export type WorldFeatureDeletion = {
  worldId: string;
  featureId: string;
  nonce: number;
};

type VehicleModel = {
  id: string;
  label: string;
  vehicle_type: string;
  constraints: Agent["constraints"];
  capabilities: string[];
  default_name?: string;
  builtin?: boolean;
  revision?: number;
};

export type WorldRoadImport = {
  import_id: string;
  name: string;
  bbox: [number, number, number, number];
  feature_count: number;
  geojson: FeatureCollection;
  created_at: string;
};

export type WorldMapView = {
  center: LonLat;
  zoom: number;
};

export type WorldRecord = {
  world_id: string;
  name: string;
  map: string;
  notes: string;
  feature_ids: string[];
  selected_agent_id: string;
  agents: WorldAgent[];
  road_imports: WorldRoadImport[];
  map_view?: WorldMapView;
  revision: number;
  created_at: string;
  updated_at: string;
  runtime_active?: boolean;
  runtime_status?: string;
  runtime_version?: string;
  map_collection?: string;
};

type WorldLibrary = {
  active_world_id: string;
  worlds: WorldRecord[];
};

export type WorldContext = {
  world_id: string;
  name: string;
  map: string;
  notes: string;
  agents: Agent[];
  feature_ids: string[];
  road_imports: WorldRoadImport[];
  roads: FeatureCollection;
  map_view?: WorldMapView;
};

export type WorldContextLibrary = {
  active_world_id: string;
  worlds: WorldContext[];
};

type WorldBuilderProps = {
  mapFeatures: MapFeature[];
  mapFeaturesReady: boolean;
  selectedFeatureId?: string;
  pendingFeatureToAdd?: { featureId: string; worldId: string; nonce: number };
  pendingFeatureToDelete?: WorldFeatureDeletion;
  pendingAgentPlacement?: WorldAgentPlacement;
  currentMapView?: WorldMapView;
  catalogWorlds?: WorldCatalogEntry[];
  placingAgentId?: string;
  onWorldAgentsChange: (agents: Agent[]) => void;
  onActiveWorldFeaturesChange: (featureIds: string[]) => void;
  onWorldRoadsChange: (roads?: FeatureCollection) => void;
  onWorldLibraryChange: (library: WorldContextLibrary) => void;
  onSelectFeature: (featureId: string) => void;
  onDeleteAuthoringFeature: (
    worldId: string,
    mapName: string,
    featureId: string,
    revision: number,
  ) => Promise<WorldCatalogEntry | undefined>;
  onLaunchWorld: (worldId: string, request: WorldLaunchRequest) => Promise<WorldLaunchResult>;
  onWorldContextReset: () => void;
  onBeginPlaceAgent: (agentId: string) => void;
  onCancelPlaceAgent: () => void;
};

const LEGACY_AGENT_ID = "f9992bb3-9871-451f-90a0-9207eb9fe6c5";
const DEFAULT_BBOX: [number, number, number, number] = [4.3885, 50.8428, 4.3972, 50.8467];
const EMPTY_ROAD_IMPORTS: WorldRoadImport[] = [];
const DEFAULT_VEHICLE_MODELS: VehicleModel[] = [
  {
    id: "themis-fr",
    label: "Themis Fr",
    vehicle_type: "UGV",
    default_name: "Themis Fr",
    constraints: { max_speed: 4.5, max_acceleration: 8, max_deceleration: 8, max_jerk: 10, max_straight_slope: 30, max_side_slope: 10, max_weight: 16, max_tilt_angle: 1.8, coverage_width_m: 6 },
    capabilities: ["camera", "radio_relay", "cargo", "casualty_transport", "ballistic_protection"],
    builtin: true,
  },
  {
    id: "ugv-standard",
    label: "UGV standard",
    vehicle_type: "UGV",
    constraints: { max_speed: 4, max_acceleration: 8, max_deceleration: 8, max_jerk: 10, max_straight_slope: 30, max_side_slope: 10, max_weight: 16, max_tilt_angle: 1.8, coverage_width_m: 6 },
    capabilities: ["camera", "radio_relay", "cargo"],
    builtin: true,
  },
  {
    id: "ugv-scout",
    label: "UGV scout",
    vehicle_type: "UGV",
    constraints: { max_speed: 10, max_acceleration: 10, max_deceleration: 10, max_jerk: 12, max_straight_slope: 35, max_side_slope: 15, max_weight: 10, max_tilt_angle: 1.6, coverage_width_m: 6 },
    capabilities: ["camera", "radio_relay"],
    builtin: true,
  },
  {
    id: "ugv-heavy",
    label: "UGV heavy",
    vehicle_type: "UGV",
    constraints: { max_speed: 2.5, max_acceleration: 5, max_deceleration: 5, max_jerk: 5, max_straight_slope: 25, max_side_slope: 10, max_weight: 40, max_tilt_angle: 1.2, coverage_width_m: 6 },
    capabilities: ["camera", "cargo", "casualty_transport", "ballistic_protection"],
    builtin: true,
  },
];

export function WorldBuilder({
  mapFeatures,
  mapFeaturesReady,
  selectedFeatureId,
  pendingFeatureToAdd,
  pendingFeatureToDelete,
  pendingAgentPlacement,
  currentMapView,
  catalogWorlds = [],
  placingAgentId,
  onWorldAgentsChange,
  onActiveWorldFeaturesChange,
  onWorldRoadsChange,
  onWorldLibraryChange,
  onSelectFeature,
  onDeleteAuthoringFeature,
  onLaunchWorld,
  onWorldContextReset,
  onBeginPlaceAgent,
  onCancelPlaceAgent,
}: WorldBuilderProps) {
  const [library, setLibrary] = useState<WorldLibrary>({ active_world_id: "", worlds: [] });
  const [tab, setTab] = useState("situation");
  const [appliedPendingFeatureNonce, setAppliedPendingFeatureNonce] = useState<number | undefined>();
  const [appliedPlacementNonce, setAppliedPlacementNonce] = useState<number | undefined>();
  const appliedFeatureDeletionNonceRef = useRef<number | undefined>();
  const [launchBusy, setLaunchBusy] = useState(false);
  const [launchResult, setLaunchResult] = useState<WorldLaunchResult | undefined>();
  const [launchError, setLaunchError] = useState("");
  const [saveStatus, setSaveStatus] = useState<"saved" | "dirty" | "saving" | "conflict" | "error">("saved");
  const [saveError, setSaveError] = useState("");
  const [conflictWorld, setConflictWorld] = useState<WorldRecord | undefined>();
  const acknowledgedRef = useRef(new Map<string, string>());
  const revisionRef = useRef(new Map<string, number>());
  const pendingSaveRef = useRef<WorldRecord | undefined>();
  const saveInFlightRef = useRef(false);
  const emptyWorld = useMemo(() => defaultWorld(), []);
  const activeWorld = library.worlds.find((world) => world.world_id === library.active_world_id) ?? library.worlds[0] ?? emptyWorld;
  const selectedFeature = mapFeatures.find((feature) => feature.feature_id === selectedFeatureId);
  const activeRoadImports = activeWorld.road_imports ?? EMPTY_ROAD_IMPORTS;
  const featureById = useMemo(() => new Map(mapFeatures.map((feature) => [feature.feature_id, feature])), [mapFeatures]);
  const missingWorldFeatureIds = useMemo(
    () => activeWorld.feature_ids.filter((featureId) => !featureById.has(featureId)),
    [activeWorld.feature_ids, featureById],
  );
  const worldFeatureIds = useMemo(
    () => activeWorld.feature_ids.filter((featureId) => featureById.has(featureId) && !isWorldBuilderImportedRoad(featureById.get(featureId))),
    [activeWorld.feature_ids, featureById],
  );
  const worldFeatures = useMemo(
    () => worldFeatureIds.flatMap((featureId) => featureById.get(featureId) ?? []),
    [featureById, worldFeatureIds],
  );
  const availableWorldFeatures = useMemo(
    () => mapFeatures.filter((feature) => !activeWorld.feature_ids.includes(feature.feature_id) && !isWorldBuilderImportedRoad(feature)),
    [activeWorld.feature_ids, mapFeatures],
  );
  const worldRoads = useMemo(() => roadImportsToFeatureCollection(activeRoadImports), [activeRoadImports]);
  const hasRoutingRoads = useMemo(
    () => activeRoadImports.some((roadImport) => roadImport.feature_count > 0)
      || worldFeatures.some((feature) => feature.feature_type === "road" && feature.geometry.type === "LineString"),
    [activeRoadImports, worldFeatures],
  );
  const launchIssue = activeWorld.agents.length === 0
    ? "Add at least one vehicle before launch."
    : !hasRoutingRoads
      ? "Add a road LineString or download an OSM road section inside a polygon before launch."
      : "";
  const activeWorldAcknowledged = Boolean(
    activeWorld.world_id
    && acknowledgedRef.current.get(activeWorld.world_id) === worldFingerprint(activeWorld),
  );
  const selectedAgent = activeWorld.agents.find((agent) => agent.agent_id === activeWorld.selected_agent_id) ?? activeWorld.agents[0];

  useLayoutEffect(() => {
    onWorldLibraryChange(worldContextLibraryFromLibrary(library));
    onWorldAgentsChange(activeWorld.agents.map(toAgent));
  }, [activeWorld.agents, library, onWorldAgentsChange, onWorldLibraryChange]);

  useEffect(() => {
    if (!catalogWorlds.length) return;
    setLibrary((current) => {
      const catalog = catalogWorlds.map(worldRecordFromCatalog);
      if (!current.worlds.length) {
        for (const world of catalog) {
          acknowledgedRef.current.set(world.world_id, worldFingerprint(world));
          revisionRef.current.set(world.world_id, world.revision);
        }
        const preferred = catalog.find((world) => world.runtime_active) ?? catalog[0];
        return { active_world_id: preferred?.world_id ?? "", worlds: catalog };
      }
      const catalogById = new Map(catalog.map((world) => [world.world_id, world]));
      const worlds = current.worlds.map((local) => {
        const server = catalogById.get(local.world_id);
        if (!server) return local;
        catalogById.delete(local.world_id);
        const clean = acknowledgedRef.current.get(local.world_id) === worldFingerprint(local)
          && pendingSaveRef.current?.world_id !== local.world_id;
        if (clean) {
          acknowledgedRef.current.set(server.world_id, worldFingerprint(server));
          revisionRef.current.set(server.world_id, server.revision);
          return server;
        }
        return {
          ...local,
          runtime_active: server.runtime_active,
          runtime_status: server.runtime_status,
          runtime_version: server.runtime_version,
          map_collection: server.map_collection,
        };
      });
      for (const world of catalogById.values()) {
        acknowledgedRef.current.set(world.world_id, worldFingerprint(world));
        revisionRef.current.set(world.world_id, world.revision);
        worlds.push(world);
      }
      const activeWorldId = worlds.some((world) => world.world_id === current.active_world_id)
        ? current.active_world_id
        : (worlds.find((world) => world.runtime_active) ?? worlds[0])?.world_id ?? "";
      return { active_world_id: activeWorldId, worlds };
    });
  }, [catalogWorlds]);

  useEffect(() => {
    if (!activeWorld.world_id || conflictWorld?.world_id === activeWorld.world_id) return;
    const fingerprint = worldFingerprint(activeWorld);
    if (acknowledgedRef.current.get(activeWorld.world_id) === fingerprint) {
      if (!saveInFlightRef.current) setSaveStatus("saved");
      return;
    }
    setSaveStatus("dirty");
    const timer = window.setTimeout(() => {
      pendingSaveRef.current = activeWorld;
      flushSaveQueue().catch(() => undefined);
    }, 450);
    return () => window.clearTimeout(timer);
  }, [activeWorld]);

  async function flushSaveQueue() {
    if (saveInFlightRef.current) return;
    saveInFlightRef.current = true;
    setSaveStatus("saving");
    setSaveError("");
    try {
      while (pendingSaveRef.current) {
        const draft = pendingSaveRef.current;
        pendingSaveRef.current = undefined;
        const saved = await updateWorld(draft.world_id, {
          ...worldDefinitionPayload(draft),
          revision: revisionRef.current.get(draft.world_id) ?? draft.revision,
        });
        const savedRecord = worldRecordFromCatalog(saved);
        acknowledgedRef.current.set(draft.world_id, worldFingerprint(draft));
        revisionRef.current.set(draft.world_id, savedRecord.revision);
        setLibrary((current) => ({
          ...current,
          worlds: current.worlds.map((world) =>
            world.world_id !== draft.world_id
              ? world
              : worldFingerprint(world) === worldFingerprint(draft)
                ? savedRecord
                : { ...world, revision: savedRecord.revision, updated_at: savedRecord.updated_at },
          ),
        }));
      }
      setSaveStatus("saved");
    } catch (error) {
      pendingSaveRef.current = undefined;
      if (error instanceof ApiError && error.status === 409) {
        const detail = error.detail as { current?: WorldCatalogEntry } | undefined;
        setConflictWorld(detail?.current ? worldRecordFromCatalog(detail.current) : undefined);
        setSaveStatus("conflict");
      } else {
        setSaveStatus("error");
      }
      setSaveError(error instanceof Error ? error.message : String(error));
    } finally {
      saveInFlightRef.current = false;
    }
  }

  useLayoutEffect(() => {
    onActiveWorldFeaturesChange(worldFeatureIds);
  }, [activeWorld.world_id, onActiveWorldFeaturesChange, worldFeatureIds]);

  useLayoutEffect(() => {
    onWorldRoadsChange(worldRoads);
  }, [activeWorld.world_id, onWorldRoadsChange, worldRoads]);

  useLayoutEffect(() => {
    if (!mapFeaturesReady || missingWorldFeatureIds.length === 0) return;
    const missing = new Set(missingWorldFeatureIds);
    setLibrary((current) => ({
      ...current,
      worlds: current.worlds.map((world) => {
        const featureIds = world.feature_ids.filter((featureId) => !missing.has(featureId));
        return featureIds.length === world.feature_ids.length
          ? world
          : { ...world, feature_ids: featureIds, updated_at: new Date().toISOString() };
      }),
    }));
  }, [mapFeaturesReady, missingWorldFeatureIds]);

  useEffect(() => {
    const importedRoads = activeWorld.feature_ids.flatMap((featureId) => {
      const feature = featureById.get(featureId);
      return isWorldBuilderImportedRoad(feature) ? [feature] : [];
    });
    if (!importedRoads.length) return;
    updateActiveWorld({
      feature_ids: activeWorld.feature_ids.filter((featureId) => !isWorldBuilderImportedRoad(featureById.get(featureId))),
      road_imports: [...activeRoadImports, roadImportFromMapFeatures(importedRoads)],
    });
  }, [activeWorld.world_id, activeWorld.feature_ids.join("|"), featureById]);

  useLayoutEffect(() => {
    if (!pendingFeatureToAdd || pendingFeatureToAdd.nonce === appliedPendingFeatureNonce) return;
    if (!library.worlds.some((world) => world.world_id === pendingFeatureToAdd.worldId)) return;
    setAppliedPendingFeatureNonce(pendingFeatureToAdd.nonce);
    addFeatureIdsToWorld(pendingFeatureToAdd.worldId, [pendingFeatureToAdd.featureId]);
  }, [appliedPendingFeatureNonce, library.worlds, pendingFeatureToAdd]);

  useEffect(() => {
    if (!pendingFeatureToDelete || pendingFeatureToDelete.nonce === appliedFeatureDeletionNonceRef.current) return;
    if (!library.worlds.some((world) => world.world_id === pendingFeatureToDelete.worldId)) return;
    appliedFeatureDeletionNonceRef.current = pendingFeatureToDelete.nonce;
    deleteAuthoringFeatureFromWorld(pendingFeatureToDelete).catch(() => undefined);
  }, [pendingFeatureToDelete?.nonce]);

  useEffect(() => {
    if (!pendingAgentPlacement || pendingAgentPlacement.nonce === appliedPlacementNonce) return;
    if (pendingAgentPlacement.worldId !== activeWorld.world_id) return;
    setAppliedPlacementNonce(pendingAgentPlacement.nonce);
    updateAgent(pendingAgentPlacement.agentId, { current_location: pendingAgentPlacement.point });
  }, [pendingAgentPlacement?.nonce, activeWorld.world_id]);

  function updateActiveWorld(patch: Partial<WorldRecord>) {
    setLibrary((current) => {
      const updatedAt = new Date().toISOString();
      return {
        ...current,
        worlds: current.worlds.map((world) =>
          world.world_id === activeWorld.world_id ? { ...world, ...patch, updated_at: updatedAt } : world,
        ),
      };
    });
  }

  function updateAgent(agentId: string, patch: Partial<WorldAgent>) {
    updateActiveWorld({
      selected_agent_id: activeWorld.selected_agent_id === agentId ? patch.agent_id ?? agentId : activeWorld.selected_agent_id,
      agents: activeWorld.agents.map((agent) => (agent.agent_id === agentId ? { ...agent, ...patch } : agent)),
    });
  }

  async function createWorldDefinition() {
    onWorldContextReset();
    const saved = worldRecordFromCatalog(await createWorld(worldDefinitionPayload(defaultWorld(nextBlankWorldName(library.worlds)))));
    acknowledgedRef.current.set(saved.world_id, worldFingerprint(saved));
    revisionRef.current.set(saved.world_id, saved.revision);
    setLibrary((current) => ({ active_world_id: saved.world_id, worlds: [...current.worlds, saved] }));
    setSaveStatus("saved");
  }

  async function duplicateWorld() {
    onWorldContextReset();
    const copy = worldRecordFromCatalog(await createWorld({
      ...worldDefinitionPayload(activeWorld),
      name: `${activeWorld.name} copy`,
    }));
    acknowledgedRef.current.set(copy.world_id, worldFingerprint(copy));
    revisionRef.current.set(copy.world_id, copy.revision);
    setLibrary((current) => ({
      active_world_id: copy.world_id,
      worlds: [...current.worlds, copy],
    }));
  }

  async function deleteWorldDefinition() {
    if (!activeWorld.world_id) return;
    onWorldContextReset();
    await deleteWorld(activeWorld.world_id);
    setLibrary((current) => {
      const worlds = current.worlds.filter((world) => world.world_id !== activeWorld.world_id);
      return {
        active_world_id: worlds[0]?.world_id ?? "",
        worlds,
      };
    });
  }

  function reloadServerVersion() {
    if (!conflictWorld) return;
    acknowledgedRef.current.set(conflictWorld.world_id, worldFingerprint(conflictWorld));
    revisionRef.current.set(conflictWorld.world_id, conflictWorld.revision);
    setLibrary((current) => ({
      ...current,
      worlds: current.worlds.map((world) => world.world_id === conflictWorld.world_id ? conflictWorld : world),
    }));
    setConflictWorld(undefined);
    setSaveError("");
    setSaveStatus("saved");
  }

  async function saveConflictAsCopy() {
    const saved = worldRecordFromCatalog(await createWorld({
      ...worldDefinitionPayload(activeWorld),
      name: `${activeWorld.name} copy`,
    }));
    acknowledgedRef.current.set(saved.world_id, worldFingerprint(saved));
    revisionRef.current.set(saved.world_id, saved.revision);
    setLibrary((current) => ({ active_world_id: saved.world_id, worlds: [...current.worlds, saved] }));
    setConflictWorld(undefined);
    setSaveError("");
    setSaveStatus("saved");
  }

  function addSelectedFeature() {
    if (!selectedFeature || activeWorld.feature_ids.includes(selectedFeature.feature_id)) return;
    addFeatureIdsToActiveWorld([selectedFeature.feature_id]);
  }

  function addFeatureIdsToActiveWorld(featureIds: string[]) {
    addFeatureIdsToWorld(activeWorld.world_id, featureIds);
  }

  function addFeatureIdsToWorld(worldId: string, featureIds: string[]) {
    setLibrary((current) => {
      const world = current.worlds.find((item) => item.world_id === worldId);
      if (!world) return current;
      const next = unique([...world.feature_ids, ...featureIds]);
      if (next.length === world.feature_ids.length) return current;
      const updatedAt = new Date().toISOString();
      return {
        ...current,
        worlds: current.worlds.map((item) =>
          item.world_id === worldId ? { ...item, feature_ids: next, updated_at: updatedAt } : item,
        ),
      };
    });
  }

  function removeFeature(featureId: string) {
    updateActiveWorld({ feature_ids: activeWorld.feature_ids.filter((id) => id !== featureId) });
  }

  async function deleteAuthoringFeatureFromWorld(request: WorldFeatureDeletion) {
    const world = library.worlds.find((item) => item.world_id === request.worldId);
    if (!world) return;
    const acknowledged = acknowledgedRef.current.get(world.world_id) === worldFingerprint(world);
    if (!acknowledged || saveStatus !== "saved" || saveInFlightRef.current || pendingSaveRef.current) {
      setSaveError("Wait until the world definition is saved before deleting an attached asset.");
      setSaveStatus("error");
      return;
    }
    setSaveError("");
    setSaveStatus("saving");
    try {
      const saved = await onDeleteAuthoringFeature(
        world.world_id,
        world.map,
        request.featureId,
        revisionRef.current.get(world.world_id) ?? world.revision,
      );
      if (saved) {
        const savedRecord = worldRecordFromCatalog(saved);
        acknowledgedRef.current.set(savedRecord.world_id, worldFingerprint(savedRecord));
        revisionRef.current.set(savedRecord.world_id, savedRecord.revision);
        setLibrary((current) => ({
          ...current,
          worlds: current.worlds.map((item) => item.world_id === savedRecord.world_id ? savedRecord : item),
        }));
      }
      setSaveStatus("saved");
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : String(error));
      setSaveStatus("error");
      throw error;
    }
  }

  function clearWorldContents() {
    onWorldContextReset();
    updateActiveWorld({
      feature_ids: [],
      agents: [],
      selected_agent_id: "",
      road_imports: [],
    });
  }

  function saveCurrentMapView() {
    if (!currentMapView) return;
    updateActiveWorld({ map_view: currentMapView });
  }

  function addAgent(model: VehicleModel = DEFAULT_VEHICLE_MODELS[0]) {
    const agent = createWorldAgent(nextAgentName(activeWorld.agents, model), undefined, model);
    updateActiveWorld({
      selected_agent_id: agent.agent_id,
      agents: [...activeWorld.agents, agent],
    });
  }

  function cloneAgent(agent: WorldAgent) {
    const copy = {
      ...agent,
      agent_id: randomUuid(),
      name: `${agent.name || agent.agent_id} copy`,
      capabilities: [...agent.capabilities],
    };
    updateActiveWorld({
      selected_agent_id: copy.agent_id,
      agents: [...activeWorld.agents, copy],
    });
  }

  function removeAgent(agentId: string) {
    const agents = activeWorld.agents.filter((agent) => agent.agent_id !== agentId);
    updateActiveWorld({
      selected_agent_id: activeWorld.selected_agent_id === agentId ? agents[0]?.agent_id ?? "" : activeWorld.selected_agent_id,
      agents,
    });
  }

  async function importRoads(request: OsmRoadImportRequest) {
    if (!activeWorld.world_id || saveStatus !== "saved" || !activeWorldAcknowledged) {
      throw new Error("Wait for this world definition to be saved before importing roads.");
    }
    const response = await queryWorldRoadImport(activeWorld.world_id, {
      ...request,
      revision: revisionRef.current.get(activeWorld.world_id) ?? activeWorld.revision,
    });
    const saved = worldRecordFromCatalog(response.world);
    acknowledgedRef.current.set(saved.world_id, worldFingerprint(saved));
    revisionRef.current.set(saved.world_id, saved.revision);
    setLibrary((current) => ({
      ...current,
      worlds: current.worlds.map((world) => world.world_id === saved.world_id ? saved : world),
    }));
    return {
      ...response.road_import,
      map: saved.map,
      features: response.road_import.geojson.features,
      persisted: false as const,
    };
  }

  async function removeRoadImport(importId: string) {
    const saved = worldRecordFromCatalog(await deleteWorldRoadImport(
      activeWorld.world_id,
      importId,
      revisionRef.current.get(activeWorld.world_id) ?? activeWorld.revision,
    ));
    acknowledgedRef.current.set(saved.world_id, worldFingerprint(saved));
    revisionRef.current.set(saved.world_id, saved.revision);
    setLibrary((current) => ({
      ...current,
      worlds: current.worlds.map((world) => world.world_id === saved.world_id ? saved : world),
    }));
  }

  async function launchActiveWorld() {
    if (!activeWorldAcknowledged || saveStatus !== "saved" || saveInFlightRef.current || pendingSaveRef.current) {
      setLaunchError("Wait until the current definition revision is saved and acknowledged before launch.");
      return;
    }
    if (launchIssue) {
      setLaunchError(launchIssue);
      return;
    }
    setLaunchBusy(true);
    setLaunchError("");
    setLaunchResult(undefined);
    try {
      const result = await onLaunchWorld(activeWorld.world_id, {
        revision: revisionRef.current.get(activeWorld.world_id) ?? activeWorld.revision,
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
          <LabTitle icon={<SlidersHorizontal className="h-4 w-4" />} label="World Builder" />
          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span>{activeWorld.name}</span>
            <span>{activeWorld.agents.length} vehicles</span>
            <span>{worldFeatures.length} assets</span>
            <span>{activeRoadImports.length} road sections</span>
            <Badge tone={saveStatus === "saved" ? "ok" : saveStatus === "conflict" || saveStatus === "error" ? "error" : "warn"}>
              {saveStatus === "saving" ? "saving" : saveStatus}
            </Badge>
          </div>
        </div>
        <div className="flex min-w-0 shrink-0 flex-wrap items-center justify-end gap-2">
          <select
            className="h-8 max-w-56 min-w-0 rounded-md border border-border bg-background px-2 text-xs outline-none focus:ring-2 focus:ring-ring"
            value={activeWorld.world_id}
            onChange={(event) => {
              setLaunchError("");
              setLaunchResult(undefined);
              setLibrary((current) => ({ ...current, active_world_id: event.target.value }));
            }}
          >
            {library.worlds.map((world) => (
              <option key={world.world_id} value={world.world_id}>
                {world.name}{world.runtime_active ? " (active)" : ""}
              </option>
            ))}
          </select>
          <Button size="icon" variant="outline" onClick={() => createWorldDefinition().catch((error) => setSaveError(String(error)))} title="New world definition">
            <Plus className="h-4 w-4" />
          </Button>
          <Button size="sm" disabled={launchBusy || Boolean(launchIssue) || saveStatus !== "saved" || !activeWorldAcknowledged} onClick={launchActiveWorld} title={launchIssue || (saveStatus !== "saved" || !activeWorldAcknowledged ? "Wait for the acknowledged saved revision" : "Launch this definition as the active world and verify its ROS vehicles")}>
            <Play className="h-4 w-4" />
            {launchBusy ? "Launching" : "Launch"}
          </Button>
          <Button size="icon" variant="outline" disabled={!activeWorld.world_id} onClick={() => duplicateWorld().catch((error) => setSaveError(String(error)))} title="Duplicate world definition">
            <Copy className="h-4 w-4" />
          </Button>
          <Button size="icon" variant="ghost" disabled={!activeWorld.world_id || activeWorld.runtime_active} onClick={() => deleteWorldDefinition().catch((error) => setSaveError(String(error)))} title={activeWorld.runtime_active ? "The active world cannot be deleted" : "Delete world definition"}>
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {(saveError || saveStatus === "conflict") && (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-900">
          <span>{saveStatus === "conflict" ? "The server has a newer world definition revision." : saveError}</span>
          {saveStatus === "conflict" && (
            <div className="flex gap-2">
              <Button size="sm" variant="outline" onClick={reloadServerVersion} disabled={!conflictWorld}>Reload server version</Button>
              <Button size="sm" onClick={() => saveConflictAsCopy().catch((error) => setSaveError(String(error)))}>Save as copy</Button>
            </div>
          )}
        </div>
      )}

      {launchIssue && (
        <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-950">
          <span className="font-semibold">World definition cannot launch yet.</span>{" "}
          {launchIssue} Streets visible in the base map are display tiles and are not frozen planner roads.
        </div>
      )}

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
          world={activeWorld}
          selectedFeature={selectedFeature}
          worldFeatures={worldFeatures}
          availableFeatures={availableWorldFeatures}
          onUpdateWorld={updateActiveWorld}
          onAddSelectedFeature={addSelectedFeature}
          onAddFeature={(featureId) => addFeatureIdsToActiveWorld([featureId])}
          onRemoveFeature={removeFeature}
          onSelectFeature={onSelectFeature}
          currentMapView={currentMapView}
          onSaveCurrentMapView={saveCurrentMapView}
          onClearWorldContents={clearWorldContents}
        />
      )}

      {tab === "vehicles" && (
        <VehiclePanel
          agents={activeWorld.agents}
          selectedAgent={selectedAgent}
          onSelectAgent={(agentId) => updateActiveWorld({ selected_agent_id: agentId })}
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
          key={activeWorld.world_id}
          selectedFeature={selectedFeature}
          worldFeatures={worldFeatures}
          roadImports={activeRoadImports}
          onImportRoads={importRoads}
          onRemoveRoadImport={(importId) => removeRoadImport(importId).catch((error) => setSaveError(String(error)))}
        />
      )}
    </div>
  );
}

function SituationPanel({
  world,
  selectedFeature,
  worldFeatures,
  availableFeatures,
  onUpdateWorld,
  onAddSelectedFeature,
  onAddFeature,
  onRemoveFeature,
  onSelectFeature,
  currentMapView,
  onSaveCurrentMapView,
  onClearWorldContents,
}: {
  world: WorldRecord;
  selectedFeature?: MapFeature;
  worldFeatures: MapFeature[];
  availableFeatures: MapFeature[];
  onUpdateWorld: (patch: Partial<WorldRecord>) => void;
  onAddSelectedFeature: () => void;
  onAddFeature: (featureId: string) => void;
  onRemoveFeature: (featureId: string) => void;
  onSelectFeature: (featureId: string) => void;
  currentMapView?: WorldMapView;
  onSaveCurrentMapView: () => void;
  onClearWorldContents: () => void;
}) {
  const grouped = groupByFeatureType(worldFeatures);
  const hasContents = world.feature_ids.length > 0 || world.agents.length > 0 || (world.road_imports ?? []).length > 0;
  return (
    <div className="space-y-4">
      <div className="rounded-md border border-border bg-panel p-4">
        <div className="flex items-center justify-between gap-3">
          <LabTitle icon={<Save className="h-4 w-4" />} label="World Definition" />
          <Button size="sm" variant="outline" disabled={!hasContents} onClick={onClearWorldContents} title="Remove all vehicles, assets, and road sections from this world definition">
            <Trash2 className="h-4 w-4" />
            Clear
          </Button>
        </div>
        <div className="mt-3 grid grid-cols-2 gap-3">
          <TextField label="Name" value={world.name} onChange={(value) => onUpdateWorld({ name: value })} />
          <TextField label="Map" value={world.map} onChange={(value) => onUpdateWorld({ map: value })} />
        </div>
        <label className="mt-3 block text-xs">
          <span className="font-medium text-muted-foreground">Notes</span>
          <textarea
            className="mt-1 h-20 w-full resize-none rounded-md border border-border bg-background px-2 py-2 outline-none focus:ring-2 focus:ring-ring"
            value={world.notes}
            onChange={(event) => onUpdateWorld({ notes: event.target.value })}
          />
        </label>
        <div className="mt-3 rounded-sm border border-border bg-background p-3 text-xs">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="min-w-0">
              <div className="font-semibold">Opening Map View</div>
              <div className="mt-1 text-muted-foreground">
                {world.map_view
                  ? `${world.map_view.center[0].toFixed(6)}, ${world.map_view.center[1].toFixed(6)} · z${world.map_view.zoom}`
                  : "No saved opening view"}
              </div>
            </div>
            <Button size="sm" variant="outline" disabled={!currentMapView} onClick={onSaveCurrentMapView} title="Use the current map center and zoom when this world definition opens">
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
          <Button size="sm" variant="outline" disabled={world.feature_ids.includes(selectedFeature.feature_id)} onClick={onAddSelectedFeature}>
            <Plus className="h-4 w-4" />
            Add Asset
          </Button>
        </div>
      )}

      <div className="rounded-md border border-border bg-panel p-3">
        <label className="block text-xs font-medium text-muted-foreground" htmlFor="world-existing-asset">
          Attach existing map asset
        </label>
        <select
          id="world-existing-asset"
          className="mt-2 h-9 w-full rounded-md border border-border bg-background px-2 text-xs outline-none focus:ring-2 focus:ring-ring"
          value=""
          disabled={availableFeatures.length === 0}
          onChange={(event) => {
            if (event.target.value) onAddFeature(event.target.value);
          }}
        >
          <option value="">{availableFeatures.length ? "Choose an unassigned asset..." : "All map assets are already attached"}</option>
          {availableFeatures.map((feature) => (
            <option key={feature.feature_id} value={feature.feature_id}>
              {feature.name} ({feature.feature_type})
            </option>
          ))}
        </select>
        <p className="mt-2 text-xs text-muted-foreground">
          Objective points are shown on the map as available authoring references. Add one here to include it in this world definition.
        </p>
      </div>

      <div className="grid grid-cols-3 gap-2">
        {["objective", "road", "workspace", "geofence", "risk"].map((type) => (
          <div key={type} className="rounded-md border border-border bg-panel p-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold capitalize">{type}</span>
              <Badge>{grouped[type]?.length ?? 0}</Badge>
            </div>
            <div className="mt-2 space-y-2">
              {(grouped[type] ?? []).slice(0, 4).map((feature) => (
                <WorldFeatureRow key={feature.feature_id} feature={feature} onSelectFeature={onSelectFeature} onRemoveFeature={onRemoveFeature} />
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="rounded-md border border-border bg-panel p-4">
        <div className="flex items-center justify-between">
          <LabTitle icon={<MapPinned className="h-4 w-4" />} label="World Assets" />
          <Badge>{worldFeatures.length}</Badge>
        </div>
        <div className="mt-3 space-y-2">
          {worldFeatures.length ? (
            worldFeatures.map((feature) => (
              <WorldFeatureRow key={feature.feature_id} feature={feature} onSelectFeature={onSelectFeature} onRemoveFeature={onRemoveFeature} />
            ))
          ) : (
            <div className="rounded-sm border border-border bg-background px-3 py-2 text-xs text-muted-foreground">No world assets selected.</div>
          )}
        </div>
      </div>
    </div>
  );
}

function WorldFeatureRow({
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
          title="Remove from world definition"
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
  agents: WorldAgent[];
  selectedAgent?: WorldAgent;
  onSelectAgent: (agentId: string) => void;
  onAddAgent: (model?: VehicleModel) => void;
  onCloneAgent: (agent: WorldAgent) => void;
  onRemoveAgent: (agentId: string) => void;
  onUpdateAgent: (agentId: string, patch: Partial<WorldAgent>) => void;
  placingAgentId?: string;
  onBeginPlaceAgent: (agentId: string) => void;
  onCancelPlaceAgent: () => void;
}) {
  const [vehicleModels, setVehicleModels] = useState<VehicleModel[]>(DEFAULT_VEHICLE_MODELS);
  const [selectedModelId, setSelectedModelId] = useState(DEFAULT_VEHICLE_MODELS[0].id);
  const selectedModel = vehicleModels.find((model) => model.id === selectedModelId) ?? vehicleModels[0] ?? DEFAULT_VEHICLE_MODELS[0];

  useEffect(() => {
    getVehicleModels()
      .then((payload) => setVehicleModels([
        ...DEFAULT_VEHICLE_MODELS,
        ...payload.vehicle_models.map(vehicleModelFromRecord),
      ]))
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (vehicleModels.some((model) => model.id === selectedModelId)) return;
    setSelectedModelId(vehicleModels[0]?.id ?? DEFAULT_VEHICLE_MODELS[0].id);
  }, [selectedModelId, vehicleModels]);

  async function saveSelectedAgentAsModel() {
    if (!selectedAgent) return;
    const saved = await createVehicleModel({
      label: uniqueVehicleModelName(`${selectedAgent.name || selectedAgent.vehicle_type || "Vehicle"} model`, vehicleModels),
      vehicle_type: selectedAgent.vehicle_type || "UGV",
      constraints: { ...selectedAgent.constraints },
      capabilities: [...selectedAgent.capabilities],
    });
    const model = vehicleModelFromRecord(saved);
    setVehicleModels((current) => [...current, model]);
    setSelectedModelId(model.id);
  }

  async function deleteSelectedModel() {
    if (selectedModel.builtin) return;
    await deleteVehicleModel(selectedModel.id);
    setVehicleModels((current) => current.filter((item) => item.id !== selectedModel.id));
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
            <Badge>{selectedModel.constraints.coverage_width_m ?? 6} m swath</Badge>
            {selectedModel.capabilities.map((capability) => <Badge key={capability}>{capability}</Badge>)}
            {selectedModel.builtin ? <Badge>built-in</Badge> : <Badge tone="ok">custom</Badge>}
          </div>
          <div className="mt-2 flex flex-wrap gap-2">
            <Button size="sm" variant="outline" disabled={!selectedAgent} onClick={() => saveSelectedAgentAsModel().catch(() => undefined)}>
              <Save className="h-4 w-4" />
              Save Model
            </Button>
            <Button size="icon" variant="ghost" disabled={selectedModel.builtin} onClick={() => deleteSelectedModel().catch(() => undefined)} title="Delete custom model">
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
              {typeof agent.constraints.coverage_width_m === "number" && <Badge>{agent.constraints.coverage_width_m.toFixed(1)} m swath</Badge>}
              {agent.capabilities.map((capability) => <Badge key={capability}>{capability}</Badge>)}
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
  agent: WorldAgent;
  onClone: () => void;
  onRemove: () => void;
  onUpdate: (patch: Partial<WorldAgent>) => void;
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
          <div className="md:col-span-2">
            <TextField label="Capabilities (comma separated)" value={agent.capabilities.join(", ")} onChange={(value) => onUpdate({ capabilities: normalizeCapabilityTags(value) })} />
            <div className="mt-1 text-xs text-muted-foreground">Example tags: camera, radio_relay, cargo, casualty_transport, ballistic_protection.</div>
          </div>
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
          <NumberField label="Coverage swath (m)" value={agent.constraints.coverage_width_m} min={0.1} step={0.1} onChange={(value) => updateConstraint("coverage_width_m", value)} />
        </div>
      </div>
    </div>
  );
}

function RoadImportPanel({
  selectedFeature,
  worldFeatures,
  roadImports,
  onImportRoads,
  onRemoveRoadImport,
}: {
  selectedFeature?: MapFeature;
  worldFeatures: MapFeature[];
  roadImports: WorldRoadImport[];
  onImportRoads: (request: OsmRoadImportRequest) => Promise<QueriedOsmRoads>;
  onRemoveRoadImport: (importId: string) => void;
}) {
  const initialPolygon = polygonFromFeature(selectedFeature) ?? polygonFromFeatures(worldFeatures);
  const [polygon, setPolygon] = useState<LonLat[] | undefined>(() => initialPolygon);
  const [bbox, setBbox] = useState<[number, number, number, number]>(() => (initialPolygon ? bboxFromPoints(initialPolygon) : undefined) ?? DEFAULT_BBOX);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<QueriedOsmRoads | undefined>();
  const [error, setError] = useState("");
  const selectedPolygon = polygonFromFeature(selectedFeature);
  const worldPolygon = polygonFromFeatures(worldFeatures);

  function useSelectedBbox() {
    if (!selectedPolygon) return;
    setPolygon(selectedPolygon);
    const next = bboxFromPoints(selectedPolygon);
    if (next) setBbox(next);
  }

  function useWorldBbox() {
    if (!worldPolygon) return;
    setPolygon(worldPolygon);
    const next = bboxFromPoints(worldPolygon);
    if (next) setBbox(next);
  }

  async function submit() {
    if (!polygon) {
      setError("Select a geofence/workspace polygon or add one to the world definition first.");
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
      {!polygon && (
        <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-950">
          <div className="font-semibold">Define the road-download area first.</div>
          Draw a geofence or workspace polygon with the map toolbar, or attach an existing polygon in Situation. Keep it selected, choose <span className="font-medium">From Selected Polygon</span>, then download the roads inside it.
        </div>
      )}
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
          <Button size="sm" variant="outline" disabled={!worldPolygon} onClick={useWorldBbox}>
            <MapPinned className="h-4 w-4" />
            From World Geofence
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
            <InfoBlock label="Section" value="World-local" />
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
                <Button size="icon" variant="ghost" onClick={() => onRemoveRoadImport(roadImport.import_id)} title="Remove road section from world definition">
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

function defaultWorld(name = "Blank world"): WorldRecord {
  const now = new Date().toISOString();
  return {
    world_id: "",
    name,
    map: "rma",
    notes: "",
    feature_ids: [],
    selected_agent_id: "",
    agents: [],
    road_imports: [],
    map_view: undefined,
    revision: 0,
    created_at: now,
    updated_at: now,
  };
}

function normalizeLibrary(stored: WorldLibrary): WorldLibrary {
  const worlds = stored.worlds.map((world) => {
    const featureIds = unique(world.feature_ids ?? []);
    const roadImports = normalizeRoadImports((world as Partial<WorldRecord>).road_imports);
    const rawAgents = world.agents ?? [];
    return {
      ...defaultWorld(),
      ...world,
      agents: isOldRuntimeSeedWorld(world, rawAgents, featureIds, roadImports) ? [] : rawAgents.map((agent) => worldAgentFromAgent(agent)),
      feature_ids: featureIds,
      road_imports: roadImports,
      map_view: normalizeMapView((world as Partial<WorldRecord>).map_view),
    };
  });
  return {
    active_world_id: worlds.some((world) => world.world_id === stored.active_world_id) ? stored.active_world_id : worlds[0]?.world_id ?? "",
    worlds,
  };
}

function mergeWorldCatalog(library: WorldLibrary, catalog: WorldCatalogEntry[]): WorldLibrary {
  const catalogById = new Map(catalog.map((world) => [world.world_id, worldRecordFromCatalog(world)]));
  const worlds = library.worlds.map((local) => {
    const saved = catalogById.get(local.world_id);
    if (!saved) return local;
    catalogById.delete(local.world_id);
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
  worlds.push(...catalogById.values());
  return { ...library, worlds };
}

function worldRecordFromCatalog(world: WorldCatalogEntry): WorldRecord {
  const agents = (world.agents ?? []).map((agent) => worldAgentFromAgent(agent));
  return {
    world_id: world.world_id,
    name: world.name || world.world_id,
    map: world.map || "rma",
    notes: world.notes || "",
    feature_ids: unique(world.feature_ids ?? []),
    selected_agent_id: world.selected_agent_id || agents[0]?.agent_id || "",
    agents,
    road_imports: normalizeRoadImports(world.road_imports),
    map_view: normalizeMapView(world.map_view),
    revision: world.revision,
    created_at: world.created_at || new Date().toISOString(),
    updated_at: world.updated_at || world.created_at || new Date().toISOString(),
    runtime_active: world.runtime_active,
    runtime_status: world.runtime_status,
    map_collection: world.map_collection,
  };
}

function worldDefinitionPayload(world: WorldRecord) {
  return {
    name: world.name,
    map: world.map,
    notes: world.notes,
    feature_ids: unique(world.feature_ids),
    selected_agent_id: world.selected_agent_id,
    agents: world.agents.map(toAgent),
    road_imports: world.road_imports,
    map_view: normalizeMapView(world.map_view) ?? null,
    runtime_active: false,
    runtime_status: "saved",
    map_collection: undefined,
    feature_count: undefined,
    road_count: undefined,
  };
}

function worldFingerprint(world: WorldRecord) {
  const payload = worldDefinitionPayload(world);
  return JSON.stringify({
    name: payload.name,
    map: payload.map,
    notes: payload.notes,
    feature_ids: payload.feature_ids,
    agents: payload.agents,
    map_view: payload.map_view,
  });
}

export function loadWorldContextLibrary(): WorldContextLibrary {
  return { active_world_id: "", worlds: [] };
}

function worldContextLibraryFromLibrary(library: WorldLibrary): WorldContextLibrary {
  return {
    active_world_id: library.active_world_id,
    worlds: library.worlds.map(worldContextFromRecord),
  };
}

function worldContextFromRecord(world: WorldRecord): WorldContext {
  const roadImports = normalizeRoadImports(world.road_imports);
  return {
    world_id: world.world_id,
    name: world.name,
    map: world.map,
    notes: world.notes,
    agents: world.agents.map(toAgent),
    feature_ids: unique(world.feature_ids ?? []),
    road_imports: roadImports,
    roads: roadImportsToFeatureCollection(roadImports),
    map_view: normalizeMapView(world.map_view),
  };
}

function nextBlankWorldName(worlds: WorldRecord[]) {
  const base = "Blank world";
  const used = new Set(worlds.map((world) => world.name));
  if (!used.has(base)) return base;
  for (let index = 2; index < 10_000; index += 1) {
    const name = `${base} ${index}`;
    if (!used.has(name)) return name;
  }
  return `${base} ${worlds.length + 1}`;
}

function nextAgentName(agents: WorldAgent[], model: VehicleModel) {
  const base = model.default_name || model.label || "Vehicle";
  const used = new Set(agents.map((agent) => agent.name));
  if (!used.has(base)) return base;
  for (let index = 2; index < 10_000; index += 1) {
    const name = `${base} ${index}`;
    if (!used.has(name)) return name;
  }
  return `${base} ${agents.length + 1}`;
}

function isOldRuntimeSeedWorld(
  world: Partial<WorldRecord>,
  agents: (WorldAgent & { source?: string })[],
  featureIds: string[],
  roadImports: WorldRoadImport[],
) {
  if (agents.length !== 1 || featureIds.length || roadImports.length) return false;
  const agent = agents[0];
  return agent.agent_id === LEGACY_AGENT_ID && (agent.source === "legacy_connected" || world.name === "New world");
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

function normalizeMapView(value: unknown): WorldMapView | undefined {
  if (!value || typeof value !== "object") return undefined;
  const view = value as Partial<WorldMapView>;
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
    capabilities: normalizeCapabilityTags(item.capabilities),
  };
}

function vehicleModelFromRecord(model: VehicleModelRecord): VehicleModel {
  return {
    id: model.model_id,
    label: model.label,
    vehicle_type: model.vehicle_type,
    constraints: normalizeModelConstraints(model.constraints),
    capabilities: normalizeCapabilityTags(model.capabilities),
    default_name: model.default_name,
    revision: model.revision,
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
    coverage_width_m: positiveNumberOrDefault(source.coverage_width_m, 6),
  };
}

function numberOrUndefined(value: unknown) {
  if (value === undefined || value === null || value === "") return undefined;
  const number = Number(value);
  return Number.isFinite(number) ? number : undefined;
}

function positiveNumberOrDefault(value: unknown, fallback: number) {
  const number = numberOrUndefined(value);
  return number !== undefined && number > 0 ? number : fallback;
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

function normalizeRoadImports(value: unknown): WorldRoadImport[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((item) => {
    if (!item || typeof item !== "object") return [];
    const roadImport = item as Partial<WorldRoadImport>;
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

function roadImportFromQuery(result: QueriedOsmRoads): WorldRoadImport {
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

function roadImportFromMapFeatures(features: MapFeature[]): WorldRoadImport {
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

function roadImportsToFeatureCollection(roadImports: WorldRoadImport[] = []): FeatureCollection {
  return {
    type: "FeatureCollection",
    features: roadImports.flatMap((roadImport) =>
      roadImport.geojson.features.map((feature) => ({
        ...feature,
        properties: {
          ...(feature.properties ?? {}),
          feature_type: "world_osm_road",
          world_road_import_id: roadImport.import_id,
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
      feature_type: "world_osm_road",
      name: feature.name,
      source_tool: "world_builder_osm_section",
    },
    geometry: feature.geometry as Feature["geometry"],
  };
}

function isWorldBuilderImportedRoad(feature?: MapFeature): feature is MapFeature {
  return feature?.feature_type === "road" && feature.properties?.source_tool === "world_builder_osm_import";
}

function worldAgentFromAgent(agent: Agent): WorldAgent {
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
      coverage_width_m: positiveNumberOrDefault(constraints.coverage_width_m, 6),
    },
    capabilities: normalizeCapabilityTags(agent.capabilities),
  };
}

function createWorldAgent(name: string, agentId = randomUuid(), model: VehicleModel = DEFAULT_VEHICLE_MODELS[0]): WorldAgent {
  return worldAgentFromAgent(
    {
      agent_id: agentId,
      name,
      vehicle_type: model.vehicle_type,
      status: "available",
      current_location: [4.392588, 50.844317],
      constraints: { ...model.constraints },
      capabilities: [...model.capabilities],
    },
  );
}

function toAgent(agent: WorldAgent): Agent {
  return {
    agent_id: agent.agent_id,
    name: agent.name,
    vehicle_type: agent.vehicle_type,
    status: agent.status,
    current_location: agent.current_location,
    constraints: agent.constraints,
    capabilities: [...agent.capabilities],
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

function normalizeCapabilityTags(value: unknown): string[] {
  const items = Array.isArray(value) ? value : typeof value === "string" ? value.split(",") : [];
  return unique(items.flatMap((item) => {
    if (typeof item !== "string") return [];
    const capability = item.trim().toLowerCase();
    return capability ? [capability] : [];
  }));
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
