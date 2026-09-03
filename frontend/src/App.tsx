import { ArrowLeft, Bot, Bug, CheckCircle2, Clock, FileJson, Globe, GripVertical, ListChecks, MapPinned, Play, Plus, RefreshCw, Route, ScanEye, Send, Settings2, ShieldCheck, SlidersHorizontal, Target, Trash2, Workflow, XCircle } from "lucide-react";
import type { Feature, FeatureCollection, Geometry } from "geojson";
import type { KeyboardEvent, PointerEvent as ReactPointerEvent, ReactNode, RefObject } from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  approveMission,
  createLiveFeature,
  createMapFeature,
  createEventSource,
  deleteMapFeature,
  deleteLiveFeature,
  forgetMission as forgetMissionRecord,
  getContracts,
  getActiveWorld,
  getAssistantStatus,
  getDiagnostics,
  getLegacyTrace,
  getMissionState,
  getMissionExamples,
  getOsmRoads,
  getPlanningDiagnostics,
  getRuntimeBootstrap,
  getWorlds,
  initMission,
  launchWorld,
  resetLegacyRuntime,
  resetAssistantConversation,
  sendAssistantMessage,
  startMission,
  updateMapFeature,
  updateLiveFeature,
  type AgentUpdateEvent,
  type AssistantDebugTrace,
  type AssistantMessageResponse,
  type AssistantOperationalPictureOptions,
  type AssistantStatus,
  type ContractGraph,
  type DiagnosticsState,
  type LegacyResetResult,
  type LegacyTrace,
  type MissionExample,
  type MissionState,
  type PlanningDiagnostics,
  type PlanningVariant,
  type PlanningVariantAnalysis,
  type PlannerUpdateEvent,
  type WorldLaunchRequest,
  type WorldLaunchResult,
  type WorldCatalogEntry,
  type WorldBinding,
} from "./api";
import { Badge } from "./components/ui/badge";
import { Button } from "./components/ui/button";
import { Tabs } from "./components/ui/tabs";
import { Textarea } from "./components/ui/textarea";
import { JsonExplorer } from "./components/JsonExplorer";
import { agents as fallbackAgents, mapFeatures as fallbackFeatures, missionExamples as fallbackMissionExamples } from "./data/demo";
import {
  assistantConversationSummaries,
  assistantTranscriptItems,
  deleteAssistantConversation,
  getActiveAssistantConversation,
  readAssistantConversationStore,
  selectAssistantConversation,
  startNewAssistantConversation,
  updateAssistantConversationMessages,
  writeAssistantConversationStore,
  type AssistantConversationStore,
  type AssistantConversationSummary,
  type AssistantTranscriptItem,
} from "./assistantHistory";
import { editJsonForKey, jsonCursorPosition } from "./jsonEditor";
import { createTaskPlan, normalizeMission, relocateMissionInlineGeometry, validateMission } from "./mission";
import { migrateLegacyBrowserData } from "./legacyWorldMigration";
import { AssistantContextPage, normalizeExcludePaths } from "./AssistantContextPage";
import { ContractExplorer } from "./ContractExplorer";
import { MapView, type DraftMapFeature } from "./MapView";
import { WorldBuilder, loadWorldContextLibrary, type WorldAgentPlacement, type WorldContextLibrary, type WorldFeatureDeletion, type WorldMapView } from "./WorldBuilder";
import { WorldPicker } from "./WorldPicker";
import type { Agent, MapFeature, MissionConfig } from "./types";
import {
  deploymentIdentity,
  mapFeaturesFromGeojson,
  projectActiveDeploymentGeojson,
  projectDefinitionGeojson,
  projectDefinitionMapFeatures,
  sameActiveWorldProjection,
  sameWorldBinding,
  worldBindingFromActiveWorld,
} from "./worldIsolation";

const LEGACY_AGENT_ID = "f9992bb3-9871-451f-90a0-9207eb9fe6c5";
const HIDDEN_MISSIONS_STORAGE_KEY = "c2_imugs2_hidden_missions";
const ASSISTANT_MISSION_DRAFTS_STORAGE_KEY = "c2_imugs2_assistant_mission_drafts_v1";
const ASSISTANT_CONTEXT_FILTER_STORAGE_KEY = "c2_imugs2_assistant_context_filter_v1";
const ALL_ASSISTANT_CONTEXT_SECTIONS = ["agents", "missions", "plans", "health", "warnings"] as const;
const RIGHT_PANE_WIDTHS_STORAGE_KEY = "c2_imugs2_right_pane_widths";
const DEFAULT_RIGHT_PANE_WIDTHS = { c2: 540, world: 860 } as const;
const MIN_RIGHT_PANE_WIDTHS = { c2: 380, world: 520 } as const;
const MIN_MAP_WIDTH = 360;
const RESIZE_HANDLE_WIDTH = 8;

type ResizableWorkspace = keyof typeof DEFAULT_RIGHT_PANE_WIDTHS;
type Workspace = "c2" | "world" | "contracts" | "context";

function readAssistantContextExcludePaths(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const stored = JSON.parse(window.localStorage.getItem(ASSISTANT_CONTEXT_FILTER_STORAGE_KEY) ?? "[]") as unknown;
    if (!Array.isArray(stored)) return [];
    return normalizeExcludePaths(stored.filter((path): path is string => typeof path === "string" && path.trim().length > 0));
  } catch {
    return [];
  }
}

function operatorMissionConfigs(
  missions: { mission_id: string; config?: MissionConfig }[],
): MissionConfig[] {
  return missions
    .filter((mission) => mission.config)
    .map((mission) => mission.config as MissionConfig)
    .slice(0, 64);
}

function agentGroupCenter(agents: Agent[]): [number, number] | undefined {
  const locations = agents.map((agent) => agent.current_location).filter((point) => (
    Array.isArray(point)
    && point.length === 2
    && point.every((value) => typeof value === "number" && Number.isFinite(value))
  ));
  if (!locations.length) return undefined;
  return [
    locations.reduce((sum, point) => sum + point[0], 0) / locations.length,
    locations.reduce((sum, point) => sum + point[1], 0) / locations.length,
  ];
}

function riskSafeRoadAnchor(snapshot: FeatureCollection | undefined, preferred?: [number, number]): [number, number] | undefined {
  if (!snapshot || !preferred) return undefined;
  const risks = snapshot.features.flatMap((feature) => {
    if (feature.properties?.feature_type !== "risk" || feature.geometry.type !== "Polygon") return [];
    return [feature.geometry.coordinates];
  });
  const candidates = snapshot.features.flatMap((feature) => {
    if (feature.geometry.type !== "LineString") return [];
    return feature.geometry.coordinates.filter((point): point is [number, number] => {
      if (!isCoordinatePair(point)) return false;
      return !risks.some((polygon) => pointInPolygon(point, polygon));
    });
  });
  return candidates.reduce<[number, number] | undefined>((nearest, point) => {
    if (!nearest) return point;
    return approximateDistanceSquared(point, preferred) < approximateDistanceSquared(nearest, preferred) ? point : nearest;
  }, undefined);
}

function isCoordinatePair(point: number[]): point is [number, number] {
  return point.length === 2 && point.every((value) => Number.isFinite(value));
}

function pointInPolygon(point: [number, number], rings: number[][][]): boolean {
  if (!rings.length || !pointInRing(point, rings[0])) return false;
  return !rings.slice(1).some((ring) => pointInRing(point, ring));
}

function pointInRing(point: [number, number], ring: number[][]): boolean {
  let inside = false;
  for (let index = 0, previous = ring.length - 1; index < ring.length; previous = index, index += 1) {
    const currentPoint = ring[index];
    const previousPoint = ring[previous];
    if (!currentPoint || !previousPoint) continue;
    const crosses = (currentPoint[1] > point[1]) !== (previousPoint[1] > point[1]);
    if (crosses && point[0] < ((previousPoint[0] - currentPoint[0]) * (point[1] - currentPoint[1])) / (previousPoint[1] - currentPoint[1]) + currentPoint[0]) {
      inside = !inside;
    }
  }
  return inside;
}

function approximateDistanceSquared(left: [number, number], right: [number, number]) {
  const latitudeScale = Math.cos((right[1] * Math.PI) / 180);
  const dx = (left[0] - right[0]) * latitudeScale;
  const dy = left[1] - right[1];
  return dx * dx + dy * dy;
}

function buildAssistantOperationalPictureOptions(
  excludePaths: string[],
  missions: { mission_id: string; config?: MissionConfig }[],
): AssistantOperationalPictureOptions {
  return {
    sections: [...ALL_ASSISTANT_CONTEXT_SECTIONS],
    operator_missions: operatorMissionConfigs(missions),
    exclude_paths: excludePaths,
  };
}

function advancedUiGateEnabled() {
  if (typeof window === "undefined") return false;
  return new URLSearchParams(window.location.search).get("debug") === "1";
}

function assistantProposalConfig(response?: AssistantMessageResponse): MissionConfig | undefined {
  if (!response?.mission_proposal || response.mission_proposal_validation?.valid !== true) return undefined;
  try {
    return normalizeMission(response.mission_proposal);
  } catch {
    return undefined;
  }
}

function assistantProposalConfigs(messages: AssistantTranscriptItem[]) {
  const configs: Record<string, MissionConfig> = {};
  for (const item of messages) {
    const config = assistantProposalConfig(item.response);
    if (config) configs[config.mission_id] = config;
  }
  return configs;
}

function missionConfigsEquivalent(left?: MissionConfig, right?: MissionConfig) {
  if (!left || !right) return false;
  return JSON.stringify(stableJsonValue(normalizeMission(left))) === JSON.stringify(stableJsonValue(normalizeMission(right)));
}

function stableJsonValue(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(stableJsonValue);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>)
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([key, item]) => [key, stableJsonValue(item)]),
    );
  }
  return value;
}

function readAssistantMissionDrafts() {
  if (typeof window === "undefined") return {} as Record<string, MissionConfig>;
  try {
    const stored = JSON.parse(window.localStorage.getItem(ASSISTANT_MISSION_DRAFTS_STORAGE_KEY) ?? "{}") as Record<string, unknown>;
    const configs: Record<string, MissionConfig> = {};
    for (const value of Object.values(stored)) {
      try {
        const config = normalizeMission(value);
        configs[config.mission_id] = config;
      } catch {
        // Ignore stale entries that no longer satisfy the mission contract.
      }
    }
    return configs;
  } catch {
    return {} as Record<string, MissionConfig>;
  }
}

function writeAssistantMissionDraft(config: MissionConfig) {
  if (typeof window === "undefined") return;
  try {
    const configs = readAssistantMissionDrafts();
    configs[config.mission_id] = config;
    window.localStorage.setItem(ASSISTANT_MISSION_DRAFTS_STORAGE_KEY, JSON.stringify(configs));
  } catch {
    // Browser persistence is best-effort; the in-memory mission remains usable.
  }
}

function removeAssistantMissionDraft(missionId: string) {
  if (typeof window === "undefined") return;
  try {
    const configs = readAssistantMissionDrafts();
    if (!configs[missionId]) return;
    delete configs[missionId];
    window.localStorage.setItem(ASSISTANT_MISSION_DRAFTS_STORAGE_KEY, JSON.stringify(configs));
  } catch {
    // Browser persistence is best-effort; hidden IDs still suppress the card.
  }
}

function readRightPaneWidths(): Record<ResizableWorkspace, number> {
  if (typeof window === "undefined") return { ...DEFAULT_RIGHT_PANE_WIDTHS };
  try {
    const saved = JSON.parse(window.localStorage.getItem(RIGHT_PANE_WIDTHS_STORAGE_KEY) ?? "{}") as Partial<Record<ResizableWorkspace, unknown>>;
    return {
      c2: typeof saved.c2 === "number" && Number.isFinite(saved.c2) ? Math.max(MIN_RIGHT_PANE_WIDTHS.c2, saved.c2) : DEFAULT_RIGHT_PANE_WIDTHS.c2,
      world: typeof saved.world === "number" && Number.isFinite(saved.world) ? Math.max(MIN_RIGHT_PANE_WIDTHS.world, saved.world) : DEFAULT_RIGHT_PANE_WIDTHS.world,
    };
  } catch {
    return { ...DEFAULT_RIGHT_PANE_WIDTHS };
  }
}

function loadInitialWorldState() {
  const library = loadWorldContextLibrary();
  return {
    library,
    activeId: library.active_world_id || undefined,
  };
}

function readHiddenMissionIds() {
  if (typeof window === "undefined") return new Set<string>();
  try {
    const payload = JSON.parse(window.localStorage.getItem(HIDDEN_MISSIONS_STORAGE_KEY) ?? "[]");
    return new Set(Array.isArray(payload) ? payload.filter((value): value is string => typeof value === "string") : []);
  } catch {
    return new Set<string>();
  }
}

function writeHiddenMissionIds(ids: Set<string>) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(HIDDEN_MISSIONS_STORAGE_KEY, JSON.stringify([...ids]));
}

function isUserMapFeature(feature: MapFeature) {
  return ["user", "authoring", "live_overlay"].includes(String(feature.properties?.source ?? ""));
}

function geoJsonCoordinates(geometry: Geometry | null | undefined) {
  return geometry && "coordinates" in geometry ? geometry.coordinates : undefined;
}

function flattenCoordinatePoints(value: unknown): [number, number][] {
  if (!Array.isArray(value)) return [];
  if (typeof value[0] === "number" && typeof value[1] === "number") return [[value[0], value[1]]];
  return value.flatMap((item) => flattenCoordinatePoints(item));
}

function mapViewKey(worldId: string, view: WorldMapView) {
  return `${worldId}:${view.center[0].toFixed(7)},${view.center[1].toFixed(7)},${view.zoom}`;
}

function geometryLiteralFromFeature(feature: MapFeature) {
  return {
    geometry_type: feature.geometry.type,
    coordinates: feature.geometry.coordinates,
  };
}

function missionGeometryRefFromFeature(feature: MapFeature) {
  if (isUserMapFeature(feature)) {
    return { geometry: geometryLiteralFromFeature(feature) };
  }
  return { feature_id: feature.feature_id };
}

function mergeMissionState(current: Record<string, MissionState>, update: MissionState, replace = false) {
  const next = { ...current };
  if (update.command_target === true) {
    for (const [missionId, state] of Object.entries(next)) {
      if (missionId !== update.mission_id && state.command_target === true) {
        next[missionId] = { ...state, command_target: false };
      }
    }
  }
  next[update.mission_id] = replace ? update : { ...next[update.mission_id], ...update };
  return next;
}

export default function App() {
  const [assistantConversationStore, setAssistantConversationStore] = useState<AssistantConversationStore>(
    () => readAssistantConversationStore(),
  );
  const [agents, setAgents] = useState<Agent[]>(fallbackAgents);
  const [agentTelemetry, setAgentTelemetry] = useState<Record<string, AgentUpdateEvent>>({});
  const [mapFeatures, setMapFeatures] = useState<MapFeature[]>(fallbackFeatures);
  const [mapFeaturesReady, setMapFeaturesReady] = useState(false);
  const [geojson, setGeojson] = useState<FeatureCollection | undefined>();
  const [osmRoads, setOsmRoads] = useState<FeatureCollection | undefined>();
  const [examples, setExamples] = useState<MissionExample[]>(fallbackMissionExamples);
  const [mission, setMission] = useState<MissionConfig | undefined>();
  const [missionText, setMissionText] = useState("");
  const [missionState, setMissionState] = useState<MissionState | undefined>();
  const [missionConfigs, setMissionConfigs] = useState<Record<string, MissionConfig>>(() => ({
    ...assistantProposalConfigs(assistantTranscriptItems(assistantConversationStore)),
    // The dedicated draft is the operator's latest working copy; the
    // transcript envelope is only the original model proposal.
    ...readAssistantMissionDrafts(),
  }));
  const [missionStates, setMissionStates] = useState<Record<string, MissionState>>({});
  const [missionWorldBindings, setMissionWorldBindings] = useState<Record<string, WorldBinding>>({});
  const [hiddenMissionIds, setHiddenMissionIds] = useState<Set<string>>(() => readHiddenMissionIds());
  const [showNewMission, setShowNewMission] = useState(false);
  const [diagnostics, setDiagnostics] = useState<DiagnosticsState | undefined>();
  const [legacyTrace, setLegacyTrace] = useState<LegacyTrace | undefined>();
  const [contractGraph, setContractGraph] = useState<ContractGraph | undefined>();
  const [contractsBusy, setContractsBusy] = useState(false);
  const [contractsError, setContractsError] = useState("");
  const [planningDiagnostics, setPlanningDiagnostics] = useState<PlanningDiagnostics | undefined>();
  const [planningDiagnosticsBusy, setPlanningDiagnosticsBusy] = useState(false);
  const [selectedPlanningVariantId, setSelectedPlanningVariantId] = useState<string | undefined>();
  const [legacyResetResult, setLegacyResetResult] = useState<LegacyResetResult | undefined>();
  const [legacyResetBusy, setLegacyResetBusy] = useState(false);
  const [plannerState, setPlannerState] = useState<PlannerUpdateEvent | undefined>();
  const [apiError, setApiError] = useState("");
  const [commandFeedback, setCommandFeedback] = useState<{ tone: "default" | "ok" | "warn" | "error"; message: string } | undefined>();
  const [busyCommand, setBusyCommand] = useState<"init" | "approve" | "start" | undefined>();
  const [busyCommandMissionId, setBusyCommandMissionId] = useState<string | undefined>();
  const [initRequestedAt, setInitRequestedAt] = useState<number | undefined>();
  const [tab, setTab] = useState("mission");
  const [workspace, setWorkspace] = useState<Workspace>("c2");
  const [selectedFeatureId, setSelectedFeatureId] = useState<string | undefined>();
  const [worldAgents, setWorldAgents] = useState<Agent[]>([]);
  const [worldFeatureIds, setWorldFeatureIds] = useState<string[]>([]);
  const [worldRoads, setWorldRoads] = useState<FeatureCollection | undefined>();
  const [worldState, setWorldState] = useState<{ library: WorldContextLibrary; activeId?: string }>(() => loadInitialWorldState());
  const [activeWorldRuntime, setActiveWorldRuntime] = useState<WorldLaunchResult | undefined>();
  const [worldCatalog, setWorldCatalog] = useState<WorldCatalogEntry[]>([]);
  const [pendingWorldFeatureToAdd, setPendingWorldFeatureToAdd] = useState<{ featureId: string; worldId: string; nonce: number } | undefined>();
  const [pendingWorldFeatureToDelete, setPendingWorldFeatureToDelete] = useState<WorldFeatureDeletion | undefined>();
  const [pendingWorldAgentPlacement, setPendingWorldAgentPlacement] = useState<WorldAgentPlacement | undefined>();
  const [placingWorldAgentId, setPlacingWorldAgentId] = useState<string | undefined>();
  const [mapFocus, setMapFocus] = useState<{ featureIds: string[]; nonce: number } | undefined>();
  const [mapFocusPoints, setMapFocusPoints] = useState<{ points: [number, number][]; nonce: number } | undefined>();
  const [currentMapView, setCurrentMapView] = useState<WorldMapView | undefined>();
  const [mapViewFocus, setMapViewFocus] = useState<{ view: WorldMapView; nonce: number } | undefined>();
  const [mapDraftResetNonce, setMapDraftResetNonce] = useState(0);
  const [assistantOpen, setAssistantOpen] = useState(false);
  const [assistantPrompt, setAssistantPrompt] = useState("");
  const [assistantStatus, setAssistantStatus] = useState<AssistantStatus | undefined>();
  const [assistantStatusBusy, setAssistantStatusBusy] = useState(false);
  const [assistantBusy, setAssistantBusy] = useState(false);
  const [assistantError, setAssistantError] = useState("");
  const [assistantDebugEnabled, setAssistantDebugEnabled] = useState(false);
  const [assistantContextExcludePaths, setAssistantContextExcludePaths] = useState<string[]>(
    () => readAssistantContextExcludePaths(),
  );
  const [advancedUiAvailable] = useState(() => advancedUiGateEnabled());
  const [rightPaneWidths, setRightPaneWidths] = useState<Record<ResizableWorkspace, number>>(() => readRightPaneWidths());
  const activeMissionIdRef = useRef<string | undefined>();
  const draftMissionIdRef = useRef<string | undefined>();
  const focusedWorldViewRef = useRef<string | undefined>();
  const pendingAgentUpdatesRef = useRef(new Map<string, AgentUpdateEvent>());
  const agentUpdateFrameRef = useRef<number | undefined>();
  const focusedRuntimeViewRef = useRef<string | undefined>();
  const missionJsonRef = useRef<HTMLTextAreaElement | null>(null);
  const rightPaneRef = useRef<HTMLElement | null>(null);
  const paneScrollRef = useRef<HTMLElement | null>(null);
  const [jsonFocus, setJsonFocus] = useState<{ needle: string; label: string; nonce: number } | undefined>();
  const activeAssistantConversation = getActiveAssistantConversation(assistantConversationStore);
  const assistantConversationId = activeAssistantConversation.conversationId;
  const assistantMessages = activeAssistantConversation.messages;
  const assistantConversationHistory = assistantConversationSummaries(assistantConversationStore);
  const applyActiveWorldRuntime = useCallback((next: WorldLaunchResult) => {
    setActiveWorldRuntime((current) => sameActiveWorldProjection(current, next) ? current : next);
  }, []);

  useEffect(() => {
    window.localStorage.setItem(RIGHT_PANE_WIDTHS_STORAGE_KEY, JSON.stringify(rightPaneWidths));
  }, [rightPaneWidths]);

  useEffect(() => {
    window.localStorage.setItem(ASSISTANT_CONTEXT_FILTER_STORAGE_KEY, JSON.stringify(assistantContextExcludePaths));
  }, [assistantContextExcludePaths]);

  useEffect(() => {
    const result = writeAssistantConversationStore(assistantConversationStore);
    if (result.persisted && (result.debugTracesStripped || result.evictedConversationIds.length > 0)) {
      setAssistantConversationStore(result.store);
    }
  }, [assistantConversationStore]);

  useEffect(() => {
    if (tab === "plan") {
      setTab("mission");
      return;
    }
    if (advancedUiAvailable) return;
    if (workspace === "contracts") setWorkspace("c2");
    if (tab === "diagnostics") setTab("mission");
  }, [advancedUiAvailable, tab, workspace]);

  useEffect(() => {
    if (!assistantOpen || assistantStatus) return;
    refreshAssistantStatus().catch(() => undefined);
  }, [assistantOpen]);

  useEffect(() => {
    if (!jsonFocus || !missionText.trim()) return;
    const handle = window.setTimeout(() => {
      const textarea = missionJsonRef.current;
      if (!textarea) return;
      const index = missionText.indexOf(jsonFocus.needle);
      if (index < 0) return;
      textarea.focus();
      textarea.setSelectionRange(index, index + jsonFocus.needle.length);
      const line = missionText.slice(0, index).split("\n").length - 1;
      textarea.scrollTop = Math.max(0, line * 20 - textarea.clientHeight / 3);
      textarea.classList.add("ring-2", "ring-primary");
      window.setTimeout(() => textarea.classList.remove("ring-2", "ring-primary"), 1400);
    }, 40);
    return () => window.clearTimeout(handle);
  }, [jsonFocus, missionText]);

  useEffect(() => {
    getRuntimeBootstrap()
      .then((bootstrap) => {
        setAgents(bootstrap.agents);
        setMapFeatures(bootstrap.map_features);
        setMapFeaturesReady(true);
        setGeojson(bootstrap.geojson);
        if (bootstrap.osm_roads) setOsmRoads(bootstrap.osm_roads);
      })
      .catch((error) => setApiError(`Backend bootstrap unavailable, using fallback data. ${String(error)}`));

    getOsmRoads().then(setOsmRoads).catch(() => undefined);
    getActiveWorld().then(applyActiveWorldRuntime).catch(() => undefined);
    getWorlds()
      .then(async (payload) => {
        if (await migrateLegacyBrowserData(payload.worlds)) {
          setWorldCatalog((await getWorlds()).worlds);
        } else {
          setWorldCatalog(payload.worlds);
        }
      })
      .catch(() => undefined);
    getMissionExamples()
      .then((payload) => {
        setExamples(payload.examples.length ? payload.examples : fallbackMissionExamples);
      })
      .catch(() => setExamples(fallbackMissionExamples));
    getDiagnostics().then(applyDiagnostics).catch(() => undefined);
    if (advancedUiAvailable) refreshContracts(false);

    const source = createEventSource();
    source.addEventListener("diagnostics.updated", (event) => {
      const update = JSON.parse((event as MessageEvent).data) as DiagnosticsState;
      applyDiagnostics(update);
    });
    source.addEventListener("mission.updated", (event) => {
      const update = JSON.parse((event as MessageEvent).data) as MissionState;
      applyMissionRuntimeUpdate(update);
    });
    source.addEventListener("planner.updated", (event) => {
      const update = JSON.parse((event as MessageEvent).data) as PlannerUpdateEvent;
      const activeMissionId = activeMissionIdRef.current;
      if (!activeMissionId) return;
      if (update.mission_id && activeMissionId && update.mission_id !== activeMissionId) return;
      setPlannerState((current) => {
        if (update.paths) return update;
        if (current?.paths) return { ...current, state: update.state, raw: update.raw };
        return update;
      });
    });
    source.addEventListener("agent.updated", (event) => {
      const update = JSON.parse((event as MessageEvent).data) as AgentUpdateEvent;
      const updateAgentId = normalizeUuidish(update.agent_id);
      pendingAgentUpdatesRef.current.set(updateAgentId, update);
      if (agentUpdateFrameRef.current !== undefined) return;
      agentUpdateFrameRef.current = window.requestAnimationFrame(() => {
        agentUpdateFrameRef.current = undefined;
        const updates = pendingAgentUpdatesRef.current;
        if (!updates.size) return;
        const applied = new Map(updates);
        updates.clear();
        setAgentTelemetry((current) => {
          let changed = false;
          const next = { ...current };
          for (const [agentId, update] of applied) {
            const existing = current[agentId];
            if (existing?.status === update.status && sameLonLat(existing?.current_location, update.current_location)) continue;
            next[agentId] = update;
            changed = true;
          }
          return changed ? next : current;
        });
        setAgents((current) => {
          let changed = false;
          const next = current.map((agent) => {
            const update = applied.get(normalizeUuidish(agent.agent_id));
            if (!update) return agent;
            const status = update.status ?? agent.status;
            const current_location = update.current_location ?? agent.current_location;
            if (status === agent.status && sameLonLat(current_location, agent.current_location)) return agent;
            changed = true;
            return { ...agent, status, current_location };
          });
          return changed ? next : current;
        });
      });
    });
    source.onerror = () => setApiError("Live ROS event stream interrupted; reconnecting...");
    return () => {
      source.close();
      if (agentUpdateFrameRef.current !== undefined) {
        window.cancelAnimationFrame(agentUpdateFrameRef.current);
        agentUpdateFrameRef.current = undefined;
      }
      pendingAgentUpdatesRef.current.clear();
    };
  }, [advancedUiAvailable]);

  useEffect(() => {
    let cancelled = false;
    const refreshWorldReadiness = () => {
      getActiveWorld()
        .then((world) => {
          if (!cancelled) applyActiveWorldRuntime(world);
        })
        .catch(() => undefined);
    };
    const timer = window.setInterval(refreshWorldReadiness, 10_000);
    window.addEventListener("focus", refreshWorldReadiness);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
      window.removeEventListener("focus", refreshWorldReadiness);
    };
  }, [applyActiveWorldRuntime]);

  const activeDeploymentIdentity = deploymentIdentity(activeWorldRuntime);
  const previousDeploymentIdentityRef = useRef<string | undefined>();
  useEffect(() => {
    const previous = previousDeploymentIdentityRef.current;
    previousDeploymentIdentityRef.current = activeDeploymentIdentity;
    if (previous === undefined || previous === activeDeploymentIdentity) return;
    setSelectedFeatureId(undefined);
    setMapFocus(undefined);
    setMapFocusPoints(undefined);
    setMapViewFocus(undefined);
    setPendingWorldAgentPlacement(undefined);
    setPlacingWorldAgentId(undefined);
    setPlannerState(undefined);
    pendingAgentUpdatesRef.current.clear();
    if (agentUpdateFrameRef.current !== undefined) {
      window.cancelAnimationFrame(agentUpdateFrameRef.current);
      agentUpdateFrameRef.current = undefined;
    }
    setAgentTelemetry({});
    activeMissionIdRef.current = undefined;
    draftMissionIdRef.current = undefined;
    setMission(undefined);
    setMissionText("");
    setMissionState(undefined);
    setShowNewMission(false);
    setMapDraftResetNonce(Date.now());
  }, [activeDeploymentIdentity]);

  useEffect(() => {
    const missionId = activeMissionIdRef.current;
    if (!missionId) return;
    const current = missionState?.mission_id === missionId ? missionState : undefined;
    if (!shouldPollMissionState(current)) return;
    const polledMissionId = missionId;
    let cancelled = false;
    async function pollMissionState() {
      try {
        const update = await getMissionState(polledMissionId);
        if (!cancelled) applyMissionRuntimeUpdate(update);
      } catch {
        // The SSE stream may still deliver the update; keep this fallback quiet.
      }
    }
    pollMissionState();
    const timer = window.setInterval(pollMissionState, 3000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [mission?.mission_id, missionState?.mission_id, missionState?.status, missionState?.planner_status, missionState?.path_status]);

  function applyMissionRuntimeUpdate(update: MissionState, source = "mission_feedback") {
    const activeMissionId = activeMissionIdRef.current;
    setMissionStates((current) => mergeMissionState(current, update));
    if (update.world_binding) {
      setMissionWorldBindings((current) => ({ ...current, [update.mission_id]: update.world_binding! }));
    }
    if (activeMissionId && update.mission_id === activeMissionId) {
      setMissionState((current) => ({ ...current, ...update }));
      if (hasPlannedPaths(update.planned_paths)) {
        setPlannerState({
          mission_id: update.mission_id,
          paths: update.planned_paths,
          source,
          received_at: update.updated_at,
        });
      }
      if (missionStatusLabel(update) !== "NONE") setCommandFeedback(undefined);
    }
  }

  function applyDiagnostics(update: DiagnosticsState) {
    setDiagnostics(update);
    const activeMissionId = activeMissionIdRef.current;
    if (update.missions?.length) {
      setMissionStates((current) => {
        let next = current;
        for (const missionUpdate of update.missions ?? []) next = mergeMissionState(next, missionUpdate);
        return next;
      });
      const activeUpdate = activeMissionId ? update.missions.find((item) => item.mission_id === activeMissionId) : undefined;
      if (activeUpdate) applyMissionRuntimeUpdate(activeUpdate, "diagnostics");
    }
    const plannerUpdate = asPlannerUpdate(update.planner_state);
    if (plannerUpdate && activeMissionId && (!plannerUpdate.mission_id || plannerUpdate.mission_id === activeMissionId)) {
      setPlannerState(plannerUpdate);
    }
  }

  const activeWorldContext = useMemo(
    () => worldState.library.worlds.find((world) => world.world_id === worldState.activeId),
    [worldState.activeId, worldState.library.worlds],
  );
  const worldFeatureIdSet = useMemo(() => {
    const featureIds = new Set(worldFeatureIds);
    const pending = pendingWorldFeatureToAdd;
    if (pending && pending.worldId === activeWorldContext?.world_id) {
      featureIds.add(pending.featureId);
    }
    return featureIds;
  }, [activeWorldContext?.world_id, pendingWorldFeatureToAdd, worldFeatureIds]);
  const worldBuilderFeatureIdSet = useMemo(() => {
    return new Set(worldFeatureIdSet);
  }, [worldFeatureIdSet]);
  const worldBuilderMapFeatures = useMemo(
    () => projectDefinitionMapFeatures(mapFeatures, worldBuilderFeatureIdSet),
    [mapFeatures, worldBuilderFeatureIdSet],
  );
  const runtimeWorldCatalogEntry = useMemo(
    () => worldCatalog.find((entry) =>
      entry.runtime_active
      && entry.world_id === activeWorldRuntime?.world_id
      && (!activeWorldRuntime?.map_collection || entry.map_collection === activeWorldRuntime.map_collection)),
    [activeWorldRuntime?.map_collection, activeWorldRuntime?.world_id, worldCatalog],
  );
  const activeRuntimeGeojson = useMemo<FeatureCollection>(
    () => projectActiveDeploymentGeojson(activeWorldRuntime),
    [activeWorldRuntime],
  );
  const runtimeMapFeatures = useMemo(
    () => mapFeaturesFromGeojson(activeRuntimeGeojson),
    [activeRuntimeGeojson],
  );
  const hasRuntimeWorld = Boolean(activeDeploymentIdentity);
  const c2Agents = useMemo(() => {
    if (!activeDeploymentIdentity || !activeWorldRuntime?.world_id) return [];

    const worldAgents = activeWorldRuntime.agents ?? runtimeWorldCatalogEntry?.agents ?? [];
    const liveAgentsById = new Map(agents.map((agent) => [normalizeUuidish(agent.agent_id), agent]));
    return worldAgents.map((agent) => {
      const agentId = normalizeUuidish(agent.agent_id);
      const liveAgent = liveAgentsById.get(agentId);
      const telemetry = agentTelemetry[agentId];
      return {
        ...agent,
        status: telemetry?.status ?? liveAgent?.status ?? agent.status,
        current_location: telemetry?.current_location ?? liveAgent?.current_location ?? agent.current_location,
      };
    });
  }, [activeDeploymentIdentity, activeWorldRuntime, agentTelemetry, agents, runtimeWorldCatalogEntry?.agents]);
  const c2MapFeatures = hasRuntimeWorld ? runtimeMapFeatures : [];

  const validation = useMemo(() => {
    if (!missionText.trim()) return [];
    try {
      return validateMission(normalizeMission(JSON.parse(missionText)), c2Agents, c2MapFeatures);
    } catch (error) {
      return [error instanceof Error ? error.message : "Mission JSON could not be parsed."];
    }
  }, [c2Agents, c2MapFeatures, missionText]);

  const taskPlan = useMemo(() => (mission ? createTaskPlan(mission, c2Agents, c2MapFeatures) : undefined), [c2Agents, c2MapFeatures, mission]);
  const mapMission = workspace === "world" ? undefined : mission;
  const mapTaskPlan = workspace === "world" ? undefined : taskPlan;
  const mapPlannerState = workspace === "world" ? undefined : plannerState;
  const mapUsesWorldContext = workspace === "world" || hasRuntimeWorld;
  const mapAgents = workspace === "world" ? worldAgents : c2Agents;
  const placingWorldAgent = worldAgents.find((agent) => agent.agent_id === placingWorldAgentId);
  const applyWorldAgents = useCallback((nextAgents: Agent[]) => setWorldAgents(nextAgents), []);
  const applyWorldFeatureIds = useCallback((featureIds: string[]) => setWorldFeatureIds(featureIds), []);
  const applyWorldRoads = useCallback((roads?: FeatureCollection) => setWorldRoads(roads), []);
  const applyWorldLibrary = useCallback((library: WorldContextLibrary) => {
    setWorldState((current) => {
      const requestedId = library.active_world_id || current.activeId;
      const activeId = requestedId && library.worlds.some((world) => world.world_id === requestedId)
        ? requestedId
        : library.worlds[0]?.world_id;
      return { library, activeId };
    });
    setPendingWorldFeatureToAdd((pending) => {
      if (!pending) return pending;
      const target = library.worlds.find((world) => world.world_id === pending.worldId);
      return target?.feature_ids.includes(pending.featureId) ? undefined : pending;
    });
  }, []);
  const resetWorldWorkspace = useCallback(() => {
    setSelectedFeatureId(undefined);
    setWorldAgents([]);
    setWorldFeatureIds([]);
    setWorldRoads(undefined);
    setPendingWorldFeatureToAdd(undefined);
    setPendingWorldFeatureToDelete(undefined);
    setPendingWorldAgentPlacement(undefined);
    setPlacingWorldAgentId(undefined);
    setMapFocus(undefined);
    setMapFocusPoints(undefined);
    setMapViewFocus(undefined);
    setMapDraftResetNonce(Date.now());
  }, []);
  const handleWorldContextChange = useCallback((library: WorldContextLibrary) => {
    resetWorldWorkspace();
    applyWorldLibrary(library);
  }, [applyWorldLibrary, resetWorldWorkspace]);
  const mapViewFeatures = useMemo(
    () => (workspace === "world" ? worldBuilderMapFeatures : c2MapFeatures),
    [c2MapFeatures, workspace, worldBuilderMapFeatures],
  );
  const mapViewGeojson = useMemo(
    () => workspace === "world"
      ? projectDefinitionGeojson(geojson, worldBuilderFeatureIdSet)
      : hasRuntimeWorld
        ? activeRuntimeGeojson
        : { type: "FeatureCollection" as const, features: [] },
    [activeRuntimeGeojson, geojson, hasRuntimeWorld, workspace, worldBuilderFeatureIdSet],
  );

  useEffect(() => {
    if (!mapUsesWorldContext || !selectedFeatureId) return;
    if (!mapViewFeatures.some((feature) => feature.feature_id === selectedFeatureId)) setSelectedFeatureId(undefined);
  }, [mapUsesWorldContext, mapViewFeatures, selectedFeatureId]);

  useEffect(() => {
    if (!activeWorldContext) {
      setWorldAgents([]);
      setWorldFeatureIds([]);
      setWorldRoads(undefined);
      return;
    }
    setWorldAgents(activeWorldContext.agents);
    setWorldFeatureIds(activeWorldContext.feature_ids);
    setWorldRoads(activeWorldContext.roads);
  }, [activeWorldContext]);

  useEffect(() => {
    if (workspace !== "world") {
      focusedWorldViewRef.current = undefined;
      return;
    }
    if (!activeWorldContext?.map_view) return;
    const key = mapViewKey(activeWorldContext.world_id, activeWorldContext.map_view);
    if (focusedWorldViewRef.current === key) return;
    focusedWorldViewRef.current = key;
    setMapViewFocus({ view: activeWorldContext.map_view, nonce: Date.now() });
  }, [
    activeWorldContext?.world_id,
    activeWorldContext?.map_view?.center[0],
    activeWorldContext?.map_view?.center[1],
    activeWorldContext?.map_view?.zoom,
    workspace,
  ]);

  const activeRuntimeMapView = activeWorldRuntime?.map_view ?? runtimeWorldCatalogEntry?.map_view;
  useEffect(() => {
    if (workspace !== "c2") {
      focusedRuntimeViewRef.current = undefined;
      return;
    }
    if (!activeDeploymentIdentity || !activeRuntimeMapView) return;
    const key = `${activeDeploymentIdentity}:${mapViewKey(activeWorldRuntime?.world_id ?? "active", activeRuntimeMapView)}`;
    if (focusedRuntimeViewRef.current === key) return;
    focusedRuntimeViewRef.current = key;
    setMapViewFocus({ view: activeRuntimeMapView, nonce: Date.now() });
  }, [
    activeDeploymentIdentity,
    activeRuntimeMapView?.center[0],
    activeRuntimeMapView?.center[1],
    activeRuntimeMapView?.zoom,
    activeWorldRuntime?.world_id,
    workspace,
  ]);

  function beginPlaceWorldAgent(agentId: string) {
    setPlacingWorldAgentId(agentId);
    setCommandFeedback({
      tone: "warn",
      message: "Click the map to set this world-definition vehicle start position.",
    });
  }

  function cancelPlaceWorldAgent() {
    setPlacingWorldAgentId(undefined);
    setCommandFeedback(undefined);
  }

  function placeWorldAgent(point: [number, number]) {
    const worldId = activeWorldContext?.world_id ?? worldState.activeId;
    if (!worldId || !placingWorldAgentId) return;
    setPendingWorldAgentPlacement({
      worldId,
      agentId: placingWorldAgentId,
      point,
      nonce: Date.now(),
    });
    setPlacingWorldAgentId(undefined);
    setMapFocusPoints({ points: [point], nonce: Date.now() });
    setCommandFeedback({
      tone: "ok",
      message: "World-definition vehicle start position updated.",
    });
  }

  function updateMission(next: MissionConfig, focus?: { needle: string; label: string }) {
    activeMissionIdRef.current = undefined;
    setMission(next);
    storeDraftMission(next);
    setMissionState(undefined);
    setPlannerState(undefined);
    setMissionText(JSON.stringify(next, null, 2));
    setJsonFocus(focus ? { ...focus, nonce: Date.now() } : undefined);
    setCommandFeedback(undefined);
    setInitRequestedAt(undefined);
  }

  function updateMissionText(value: string) {
    setMissionText(value);
    activeMissionIdRef.current = undefined;
    setMissionState(undefined);
    setPlannerState(undefined);
    setJsonFocus(undefined);
    setCommandFeedback(undefined);
    setInitRequestedAt(undefined);
    if (!value.trim()) {
      setMission(undefined);
      return;
    }
    try {
      const next = normalizeMission(JSON.parse(value));
      const errors = validateMission(next, c2Agents, c2MapFeatures);
      if (errors.length === 0) {
        setMission(next);
        storeDraftMission(next);
      } else {
        setMission(undefined);
      }
    } catch {
      setMission(undefined);
    }
  }

  function storeDraftMission(next: MissionConfig) {
    const previousDraftId = draftMissionIdRef.current;
    const persistedAssistantDrafts = readAssistantMissionDrafts();
    const isAssistantOwned = Boolean(
      persistedAssistantDrafts[next.mission_id]
      || (previousDraftId && persistedAssistantDrafts[previousDraftId]),
    );
    setMissionConfigs((current) => {
      const updated = { ...current };
      if (previousDraftId && previousDraftId !== next.mission_id && !missionStates[previousDraftId]) delete updated[previousDraftId];
      updated[next.mission_id] = next;
      return updated;
    });
    if (isAssistantOwned) {
      if (previousDraftId && previousDraftId !== next.mission_id) {
        removeAssistantMissionDraft(previousDraftId);
      }
      writeAssistantMissionDraft(next);
    }
    draftMissionIdRef.current = next.mission_id;
    const binding = worldBindingFromActiveWorld(activeWorldRuntime);
    if (binding) {
      setMissionWorldBindings((current) => ({ ...current, [next.mission_id]: binding }));
    }
  }

  function loadExample(example: MissionExample) {
    let next = normalizeMission(structuredClone(example.config));
    next.mission_id = crypto.randomUUID();

    const requiredCapabilities = normalizeCapabilityTags(next.required_capabilities);
    const compatibleAgents = c2Agents.filter((agent) => agentMatchesMissionRequirements(agent, next));
    const requiredVehicleCount = next.vehicles.length;
    let exampleFeedback: { tone: "ok" | "warn"; message: string };
    if (compatibleAgents.length >= requiredVehicleCount) {
      const assignedAgents = compatibleAgents.slice(0, requiredVehicleCount);
      next.vehicles = assignedAgents.map((agent) => agent.agent_id);
      const assignedCenter = agentGroupCenter(assignedAgents);
      const target = example.id.startsWith("icd_")
        ? riskSafeRoadAnchor(activeWorldRuntime?.snapshot, assignedCenter)
          ?? runtimeWorldCatalogEntry?.map_view?.center
          ?? assignedCenter
        : undefined;
      if (target) next = relocateMissionInlineGeometry(next, target, 0.08);
      exampleFeedback = {
        tone: "ok",
        message: `Loaded ${example.name}, mapped its ${requiredVehicleCount} vehicle slot${requiredVehicleCount === 1 ? "" : "s"} to the active world${target ? ", and fitted its inline geometry around a risk-safe world road" : ""}.`,
      };
    } else {
      const capabilityText = requiredCapabilities.length ? ` with ${requiredCapabilities.join(", ")}` : "";
      exampleFeedback = {
        tone: "warn",
        message: `Loaded the template, but the active world needs ${requiredVehicleCount} vehicle${requiredVehicleCount === 1 ? "" : "s"}${capabilityText} matching its declared limits; only ${compatibleAgents.length} currently match. Launch or update the world, then load this example again.`,
      };
    }
    updateMission(next);
    setCommandFeedback(exampleFeedback);
    setMissionState(undefined);
    setPlannerState(undefined);
    setTab("mission");
    setShowNewMission(true);
  }

  function clearMission() {
    activeMissionIdRef.current = undefined;
    draftMissionIdRef.current = undefined;
    setMission(undefined);
    setMissionText("");
    setMissionState(undefined);
    setPlannerState(undefined);
    setCommandFeedback(undefined);
    setInitRequestedAt(undefined);
  }

  function selectMission(missionId: string) {
    const config = missionConfigs[missionId] ?? asMissionConfig(missionStates[missionId]?.config);
    const state = missionStates[missionId];
    activeMissionIdRef.current = state ? missionId : undefined;
    draftMissionIdRef.current = state ? undefined : missionId;
    setShowNewMission(false);
    setMissionState(state);
    setPlannerState(hasPlannedPaths(state?.planned_paths) ? { mission_id: missionId, paths: state?.planned_paths, source: "adapter_state", received_at: state?.updated_at } : undefined);
    setCommandFeedback(undefined);
    setInitRequestedAt(undefined);
    setTab("mission");
    if (!config) {
      setMission(undefined);
      setMissionText("");
      return;
    }
    setMission(config);
    setMissionText(JSON.stringify(config, null, 2));
  }

  function startNewMission() {
    clearMission();
    setShowNewMission(true);
    setTab("mission");
  }

  function closeMissionComposer() {
    clearMission();
    setShowNewMission(false);
    setTab("mission");
  }

  async function forgetMission(missionId: string) {
    try {
      await forgetMissionRecord(missionId);
    } catch {
      // Local removal is still useful if the adapter is restarting.
    }
    setMissionConfigs((current) => {
      const next = { ...current };
      delete next[missionId];
      return next;
    });
    setMissionStates((current) => {
      const next = { ...current };
      delete next[missionId];
      return next;
    });
    setMissionWorldBindings((current) => {
      const next = { ...current };
      delete next[missionId];
      return next;
    });
    setHiddenMissionIds((current) => {
      const next = new Set(current).add(missionId);
      writeHiddenMissionIds(next);
      return next;
    });
    removeAssistantMissionDraft(missionId);
    if (activeMissionIdRef.current === missionId) clearMission();
    setCommandFeedback({ tone: "ok", message: "Mission removed from the adapter/UI list. Legacy ROS runtime is unchanged; use Clean Test DB in Diagnostics for test cleanup." });
  }

  async function createDrawnFeature(draft: DraftMapFeature) {
    const targetWorldId = workspace === "world" ? activeWorldContext?.world_id ?? worldState.activeId : undefined;
    const featureId = crypto.randomUUID();
    const name = draft.name || `${draft.feature_type} ${mapFeatures.length + 1}`;
    const geometry = toGeoJsonGeometry(draft);
    const feature: Feature = {
      type: "Feature" as const,
      id: featureId,
      properties: {
        feature_id: featureId,
        feature_type: draft.feature_type,
        name,
      },
      geometry,
    };

    try {
      if (workspace !== "world") {
        await createLiveFeature(feature);
        setActiveWorldRuntime(await getActiveWorld());
        setMapFocus({ featureIds: [featureId], nonce: Date.now() });
        setCommandFeedback({ tone: "ok", message: `Added deployment overlay '${name}'.` });
        return;
      }
      const result = await createMapFeature(feature);
      setGeojson(result.geojson);
      setMapFeatures(result.map_features);
      setMapFeaturesReady(true);
      setMapFocus({ featureIds: [featureId], nonce: Date.now() });
      setMapFocusPoints(undefined);
      if (targetWorldId) setPendingWorldFeatureToAdd({ featureId, worldId: targetWorldId, nonce: Date.now() });
      setCommandFeedback({ tone: "ok", message: `Added ${draft.feature_type} feature '${name}'.` });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setApiError(message);
      setCommandFeedback({ tone: "error", message: `Feature creation failed: ${message}` });
      return;
    }
  }

  async function updateDrawnFeature(featureId: string, draft: DraftMapFeature) {
    const editableFeatures = workspace === "world" ? mapFeatures : c2MapFeatures;
    const existing = editableFeatures.find((feature) => feature.feature_id === featureId);
    if (!existing) return;
    const name = draft.name || existing.name;
    const geometry = toGeoJsonGeometry(draft);
    const feature: Feature = {
      type: "Feature" as const,
      id: featureId,
      properties: {
        ...existing.properties,
        feature_id: featureId,
        feature_type: draft.feature_type,
        name,
      },
      geometry,
    };

    try {
      if (workspace !== "world") {
        await updateLiveFeature(featureId, feature);
        setActiveWorldRuntime(await getActiveWorld());
        setSelectedFeatureId(featureId);
        setMapFocus({ featureIds: [featureId], nonce: Date.now() });
        setCommandFeedback({ tone: "ok", message: `Updated deployment overlay '${name}'.` });
        return;
      }
      const result = await updateMapFeature(featureId, feature);
      setGeojson(result.geojson);
      setMapFeatures(result.map_features);
      setMapFeaturesReady(true);
      setSelectedFeatureId(featureId);
      setMapFocus({ featureIds: [featureId], nonce: Date.now() });
      setMapFocusPoints(undefined);
      setCommandFeedback({ tone: "ok", message: `Updated asset '${name}'.` });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setApiError(message);
      setCommandFeedback({ tone: "error", message: `Asset update failed: ${message}` });
    }
  }

  function setInlineObjective(name: string, geometryType: string, coordinates: unknown, maximizeCoverage = false) {
    const base = mission ?? emptyMission(`Navigate to ${name}`, c2Agents[0]?.agent_id ?? LEGACY_AGENT_ID);
    updateMission(
      {
        ...base,
        mission_id: crypto.randomUUID(),
        name: `Navigate to ${name}`,
        behavior: 0,
        vehicles: base.vehicles.length ? base.vehicles : [c2Agents[0]?.agent_id ?? LEGACY_AGENT_ID],
        objective: {
          ...base.objective,
          geometries: [
            {
              geometry: {
                geometry_type: geometryType,
                coordinates,
              },
            },
          ],
          maximize_coverage: maximizeCoverage,
        },
      },
      { needle: '"objective"', label: "objective" },
    );
    setMissionState(undefined);
    setPlannerState(undefined);
    setShowNewMission(true);
    setCommandFeedback({ tone: "ok", message: `Mission objective set to '${name}'. Click Init to send a fresh mission to legacy ROS.` });
    setTab("mission");
  }

  function setFeatureAsObjective(feature: MapFeature) {
    if (feature.feature_type !== "objective" || feature.geometry.type !== "Point") {
      setCommandFeedback({ tone: "warn", message: "Only Point assets of type objective can be used as simple navigation objectives." });
      return;
    }
    const geometryType = feature.geometry.type;
    setSelectedFeatureId(feature.feature_id);
    setInlineObjective(feature.name, geometryType, feature.geometry.coordinates, false);
  }

  function addFeatureToMission(feature: MapFeature) {
    const base = mission ?? emptyMission(`Mission with ${feature.name}`, c2Agents[0]?.agent_id ?? LEGACY_AGENT_ID);
    const vehicles = base.vehicles.length ? base.vehicles : [c2Agents[0]?.agent_id ?? LEGACY_AGENT_ID];

    if (feature.feature_type === "objective" && feature.geometry.type === "Point") {
      updateMission(
        {
          ...base,
          mission_id: crypto.randomUUID(),
          name: `Navigate to ${feature.name}`,
          behavior: 0,
          vehicles,
          objective: {
            ...base.objective,
            geometries: [missionGeometryRefFromFeature(feature)],
            maximize_coverage: false,
          },
        },
        { needle: '"objective"', label: "objective" },
      );
      setCommandFeedback({ tone: "ok", message: `Added objective '${feature.name}' to the mission.` });
    } else if ((feature.feature_type === "geofence" || feature.feature_type === "workspace") && feature.geometry.type === "Polygon") {
      const vehicleCoverageSwaths = coverageSwathsForVehicles(vehicles, c2Agents);
      const coverageSwaths = base.objective.coverage_swath_widths?.length
        ? base.objective.coverage_swath_widths
        : vehicleCoverageSwaths?.length
          ? vehicleCoverageSwaths
          : [6];
      updateMission(
        {
          ...base,
          mission_id: crypto.randomUUID(),
          name: `Cover ${feature.name}`,
          behavior: 1,
          vehicles,
          transit: {
            ...base.transit,
            // Keep the editor-facing mission canonical and traceable to the
            // selected asset. The adapter inlines user-created feature refs
            // only in the copy sent across the legacy REST/ROS boundary.
            geofence: { feature_id: feature.feature_id },
          },
          objective: {
            ...base.objective,
            geometries: [{ feature_id: feature.feature_id }],
            maximize_coverage: true,
            coverage_swath_widths: coverageSwaths,
          },
        },
        { needle: '"objective"', label: "coverage geofence" },
      );
      setCommandFeedback({ tone: "ok", message: `Added '${feature.name}' as the coverage geofence and objective.` });
    } else if (feature.feature_type === "road" && feature.geometry.type === "LineString") {
      const transit = base.transit ?? {};
      const roads = Array.isArray(transit["roads"]) ? transit["roads"] : [];
      const missionRoad = missionGeometryRefFromFeature(feature);
      const useAsLinePatrol = base.behavior === 1 && base.objective.geometries.length === 0;
      updateMission(
        {
          ...base,
          mission_id: crypto.randomUUID(),
          name: base.objective.geometries.length ? `${base.name ?? "Mission"} via ${feature.name}` : `Mission with ${feature.name}`,
          behavior: base.behavior,
          vehicles,
          objective: {
            ...base.objective,
            geometries: useAsLinePatrol ? [missionRoad] : base.objective.geometries,
            maximize_coverage: useAsLinePatrol ? true : base.objective.maximize_coverage,
          },
          transit: {
            ...transit,
            optimization: {
              ...((transit["optimization"] ?? transit["optimalization"]) as Record<string, unknown> | undefined),
              road_usage: 1,
            },
            roads: [...roads, missionGeometryRefFromFeature(feature)],
          },
        },
        { needle: '"geometries"', label: "mission road" },
      );
      setCommandFeedback({
        tone: "ok",
        message: useAsLinePatrol
          ? `Added road '${feature.name}' as a COVERAGE line-patrol objective.`
          : `Added road '${feature.name}' as a transit reference. It is routable only when it belongs to the active world's frozen road graph.`,
      });
    } else if (feature.feature_type === "risk" && feature.geometry.type === "Polygon") {
      updateMission(
        {
          ...base,
          mission_id: crypto.randomUUID(),
          vehicles,
          objective: {
            ...base.objective,
            line_of_sight: missionGeometryRefFromFeature(feature),
          },
        },
        { needle: '"line_of_sight"', label: "line_of_sight" },
      );
      setCommandFeedback({ tone: "ok", message: `Added risk area '${feature.name}' as line_of_sight reference.` });
    } else {
      setCommandFeedback({ tone: "warn", message: `'${feature.name}' cannot be mapped to a valid legacy mission field from the toolbar.` });
      return;
    }

    setMissionState(undefined);
    setPlannerState(undefined);
    setShowNewMission(true);
    setTab("mission");
  }

  function selectMapFeature(featureId: string) {
    setSelectedFeatureId(featureId);
  }

  async function removeFeature(feature: MapFeature) {
    setApiError("");
    try {
      if (workspace === "world") {
        const worldId = activeWorldContext?.world_id ?? worldState.activeId;
        if (!worldId) throw new Error("Select a saved world before deleting an authoring asset.");
        setPendingWorldFeatureToDelete({ featureId: feature.feature_id, worldId, nonce: Date.now() });
        setCommandFeedback({ tone: "warn", message: `Removing '${feature.name}' from the world and authoring library...` });
        return;
      }
      await deleteLiveFeature(feature.feature_id);
      setActiveWorldRuntime(await getActiveWorld());
      if (selectedFeatureId === feature.feature_id) setSelectedFeatureId(undefined);
      setCommandFeedback({ tone: "ok", message: `Removed deployment overlay '${feature.name}'.` });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setApiError(message);
      setCommandFeedback({ tone: "error", message: `Remove asset failed: ${message}` });
    }
  }

  async function deleteWorldAuthoringFeature(
    worldId: string,
    mapName: string,
    featureId: string,
    revision: number,
  ): Promise<WorldCatalogEntry | undefined> {
    const featureName = mapFeatures.find((feature) => feature.feature_id === featureId)?.name ?? featureId;
    try {
      const result = await deleteMapFeature(featureId, mapName, { worldId, revision });
      setGeojson(result.geojson);
      setMapFeatures(result.map_features);
      setMapFeaturesReady(true);
      setWorldFeatureIds((current) => current.filter((item) => item !== featureId));
      setSelectedFeatureId((current) => current === featureId ? undefined : current);
      if (result.world) {
        setWorldCatalog((current) => current.map((world) => world.world_id === result.world?.world_id ? result.world : world));
      }
      const missionUsesFeature = mission?.objective.geometries.some((geometryRef) => geometryRef.feature_id === featureId);
      if (missionUsesFeature) clearMission();
      setCommandFeedback({ tone: "ok", message: `Removed asset '${featureName}' from the world and authoring library.` });
      return result.world ?? undefined;
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setApiError(message);
      setCommandFeedback({ tone: "error", message: `Remove asset failed: ${message}` });
      throw error;
    } finally {
      setPendingWorldFeatureToDelete(undefined);
    }
  }

  async function runCommand(command: "init" | "approve" | "start", action: () => Promise<MissionState>, missionId?: string) {
    setApiError("");
    setBusyCommand(command);
    setBusyCommandMissionId(missionId);
    if (command === "init") setInitRequestedAt(Date.now());
    setCommandFeedback({ tone: "warn", message: `${commandLabel(command)} request sent to the adapter...` });
    try {
      const result = await action();
      if (result.world_binding) {
        setMissionWorldBindings((current) => ({ ...current, [result.mission_id]: result.world_binding! }));
      }
      setMissionState(result);
      setMissionStates((current) => mergeMissionState(current, result, command === "init"));
      setCommandFeedback({ tone: "ok", message: commandSuccessMessage(command, result) });
      return result;
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setApiError(message);
      setCommandFeedback({ tone: "error", message: `${commandLabel(command)} failed: ${message}` });
      throw error;
    } finally {
      setBusyCommand(undefined);
      setBusyCommandMissionId(undefined);
    }
  }

  async function sendInitMission() {
    const parsed = normalizeMission(JSON.parse(missionText));
    await initializeMissionConfig(parsed);
  }

  async function initializeMissionConfig(next: MissionConfig) {
    await runCommand("init", async () => {
      activeMissionIdRef.current = next.mission_id;
      setMission(next);
      setMissionState(undefined);
      setPlannerState(undefined);
      const result = await initMission(next);
      const returnedConfig = asMissionConfig(result.config);
      const updated = returnedConfig ? { ...returnedConfig, mission_id: result.mission_id } : { ...next, mission_id: result.mission_id };
      activeMissionIdRef.current = result.mission_id;
      draftMissionIdRef.current = undefined;
      setMission(updated);
      setMissionText(JSON.stringify(updated, null, 2));
      setMissionConfigs((current) => ({ ...current, [result.mission_id]: updated }));
      if (readAssistantMissionDrafts()[result.mission_id]) writeAssistantMissionDraft(updated);
      return result;
    }, next.mission_id);
  }

  async function sendApproveMission() {
    if (!mission) return;
    await runCommand("approve", () => approveMission(mission.mission_id), mission.mission_id);
  }

  async function sendStartMission() {
    if (!mission) return;
    await runCommand("start", () => startMission(mission.mission_id), mission.mission_id);
  }

  async function refreshLegacyTrace() {
    setLegacyTrace(await getLegacyTrace());
  }

  async function refreshPlanningDiagnostics() {
    setApiError("");
    setPlanningDiagnosticsBusy(true);
    try {
      const activeMissionId = activeMissionIdRef.current ?? mission?.mission_id ?? missionState?.mission_id;
      const result = await getPlanningDiagnostics(activeMissionId);
      setPlanningDiagnostics(result);
      setSelectedPlanningVariantId((current) => {
        const variants = result.variant_analysis?.variants ?? [];
        if (current && variants.some((variant) => variant.id === current)) return current;
        return undefined;
      });
      const refreshed = await getDiagnostics();
      applyDiagnostics(refreshed);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setApiError(message);
      setCommandFeedback({ tone: "error", message: `Planning diagnostics failed: ${message}` });
    } finally {
      setPlanningDiagnosticsBusy(false);
    }
  }

  async function launchWorldFromLab(worldId: string, request: WorldLaunchRequest): Promise<WorldLaunchResult> {
    setCommandFeedback({ tone: "warn", message: "Launching this definition as the active world..." });
    const result = await launchWorld(worldId, request);
    setAgentTelemetry({});
    if (result.agents) setAgents(result.agents);
    setActiveWorldRuntime(result);
    getWorlds().then((payload) => setWorldCatalog(payload.worlds)).catch(() => undefined);
    setCommandFeedback({
      tone: result.ready ? "ok" : "warn",
      message: result.message,
    });
    getDiagnostics().then(applyDiagnostics).catch(() => undefined);
    return result;
  }

  async function refreshContracts(showBusy = true) {
    if (showBusy) setContractsBusy(true);
    setContractsError("");
    try {
      const graph = await getContracts(true);
      setContractGraph(graph);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setContractsError(message);
      if (showBusy) setCommandFeedback({ tone: "error", message: `Contract graph refresh failed: ${message}` });
    } finally {
      if (showBusy) setContractsBusy(false);
    }
  }

  async function cleanLegacyRuntimeForExamples() {
    setApiError("");
    setLegacyResetBusy(true);
    setCommandFeedback({ tone: "warn", message: "Cleaning test-only legacy runtime records..." });
    try {
      const result = await resetLegacyRuntime();
      setLegacyResetResult(result);
      setMissionState(undefined);
      setMissionStates({});
      setMissionConfigs({});
      try {
        window.localStorage.removeItem(ASSISTANT_MISSION_DRAFTS_STORAGE_KEY);
      } catch {
        // Local drafts are already cleared from this UI session.
      }
      setHiddenMissionIds(new Set());
      writeHiddenMissionIds(new Set());
      setPlannerState(undefined);
      setCommandFeedback({ tone: "ok", message: result.message });
      await refreshLegacyTrace();
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setApiError(message);
      setCommandFeedback({ tone: "error", message: `Legacy runtime cleanup failed: ${message}` });
    } finally {
      setLegacyResetBusy(false);
    }
  }

  async function refreshAssistantStatus() {
    setAssistantStatusBusy(true);
    setAssistantError("");
    try {
      setAssistantStatus(await getAssistantStatus());
    } catch (error) {
      setAssistantStatus(undefined);
      setAssistantError(error instanceof Error ? error.message : String(error));
    } finally {
      setAssistantStatusBusy(false);
    }
  }

  async function submitAssistantMessage() {
    const message = assistantPrompt.trim();
    if (!message || assistantBusy || !assistantStatus?.configured) return;

    const targetConversationId = assistantConversationId;
    const debugRequested = advancedUiAvailable && assistantDebugEnabled;
    const assistantMessageId = crypto.randomUUID();
    setAssistantError("");
    setAssistantPrompt("");
    setAssistantConversationStore((current) => updateAssistantConversationMessages(
      current,
      targetConversationId,
      (messages) => [
        ...messages,
        { id: crypto.randomUUID(), role: "user", text: message },
        {
          id: assistantMessageId,
          role: "assistant",
          text: "Generating a validated response…",
          debugRequested,
        },
      ],
    ));
    setAssistantBusy(true);
    try {
      const response = await sendAssistantMessage({
        conversation_id: targetConversationId,
        message,
        debug: debugRequested || undefined,
        operational_picture: buildAssistantOperationalPictureOptions(assistantContextExcludePaths, missionList),
      });
      registerAssistantProposal(response, true);
      setAssistantConversationStore((current) => updateAssistantConversationMessages(
        current,
        targetConversationId,
        (messages) => messages.map((item) => item.id === assistantMessageId
          ? { ...item, text: response.answer, response }
          : item),
      ));
    } catch (error) {
      setAssistantError(error instanceof Error ? error.message : String(error));
      setAssistantConversationStore((current) => updateAssistantConversationMessages(
        current,
        targetConversationId,
        (messages) => messages.map((item) => item.id === assistantMessageId
          ? {
              ...item,
              text: "Assistant response failed before a validated answer was returned.",
            }
          : item),
      ));
    } finally {
      setAssistantBusy(false);
    }
  }

  function startAssistantConversation() {
    if (assistantBusy) return;
    setAssistantConversationStore((current) => startNewAssistantConversation(current));
    setAssistantPrompt("");
    setAssistantError("");
  }

  function chooseAssistantConversation(conversationId: string) {
    if (assistantBusy) return;
    setAssistantConversationStore((current) => selectAssistantConversation(current, conversationId));
    setAssistantPrompt("");
    setAssistantError("");
  }

  async function deleteCurrentAssistantConversation() {
    if (assistantBusy) return;
    const targetConversationId = assistantConversationId;
    setAssistantBusy(true);
    setAssistantError("");
    try {
      await resetAssistantConversation(targetConversationId);
      setAssistantConversationStore((current) => deleteAssistantConversation(current, targetConversationId));
      setAssistantPrompt("");
    } catch (error) {
      setAssistantError(error instanceof Error ? error.message : String(error));
    } finally {
      setAssistantBusy(false);
    }
  }

  function registerAssistantProposal(response: AssistantMessageResponse, adoptModelRevision = false) {
    const proposed = assistantProposalConfig(response);
    if (!proposed) return undefined;
    const proposalBinding = response.mission_proposal_validation?.world_binding ?? response.picture_world_binding ?? undefined;
    if (proposalBinding) {
      setMissionWorldBindings((current) => ({ ...current, [proposed.mission_id]: proposalBinding }));
    }
    const state = missionStates[proposed.mission_id];
    // Once a proposal is in the ordinary mission editor, that editor owns the
    // working copy. A newly returned model proposal is an intentional revision;
    // reopening an older conversation card merely reads the latest working copy.
    const config = adoptModelRevision
      ? proposed
      : missionConfigs[proposed.mission_id] ?? asMissionConfig(state?.config) ?? proposed;
    setMissionConfigs((current) => ({
      ...current,
      [config.mission_id]: adoptModelRevision ? config : current[config.mission_id] ?? config,
    }));
    writeAssistantMissionDraft(config);
    if (adoptModelRevision && mission?.mission_id === config.mission_id) {
      activeMissionIdRef.current = undefined;
      draftMissionIdRef.current = config.mission_id;
      setMission(config);
      setMissionText(JSON.stringify(config, null, 2));
      setMissionState(undefined);
      setPlannerState(undefined);
      setInitRequestedAt(undefined);
      setCommandFeedback({
        tone: state ? "warn" : "ok",
        message: state
          ? "The assistant revised this initialized mission. Re-init it to replace the previous plan."
          : "The assistant mission working copy was updated.",
      });
    }
    setHiddenMissionIds((current) => {
      if (!current.has(config.mission_id)) return current;
      const next = new Set(current);
      next.delete(config.mission_id);
      writeHiddenMissionIds(next);
      return next;
    });
    return config;
  }

  function selectAssistantProposal(response: AssistantMessageResponse, openManualUi: boolean) {
    const config = registerAssistantProposal(response);
    if (!config) {
      setAssistantError("The proposed mission could not be loaded as a valid mission configuration.");
      return undefined;
    }
    const state = missionStates[config.mission_id];
    const stateConfig = asMissionConfig(state?.config);
    const revisionPending = Boolean(state && !missionConfigsEquivalent(config, stateConfig));
    activeMissionIdRef.current = state && !revisionPending ? config.mission_id : undefined;
    draftMissionIdRef.current = state && !revisionPending ? undefined : config.mission_id;
    setMission(config);
    setMissionText(JSON.stringify(config, null, 2));
    setMissionState(state);
    setPlannerState(!revisionPending && hasPlannedPaths(state?.planned_paths)
      ? { mission_id: config.mission_id, paths: state?.planned_paths, source: "adapter_state", received_at: state?.updated_at }
      : undefined);
    setShowNewMission(true);
    setWorkspace("c2");
    setTab("mission");
    setMapFocus(undefined);
    setMapFocusPoints(undefined);
    if (openManualUi) setAssistantOpen(false);
    return config;
  }

  function validateAssistantProposal(response: AssistantMessageResponse) {
    const config = selectAssistantProposal(response, false);
    if (!config) return;
    const issues = validateMission(config, c2Agents, c2MapFeatures);
    setCommandFeedback(issues.length === 0
      ? { tone: "ok", message: "Mission validated against the current UI contracts and is now shown on the map." }
      : { tone: "error", message: `Mission validation failed: ${issues.join(" ")}` });
  }

  async function runAssistantMissionCommand(response: AssistantMessageResponse, command: "init" | "approve" | "start") {
    const config = selectAssistantProposal(response, false);
    if (!config) return;
    const issues = validateMission(config, c2Agents, c2MapFeatures);
    if (issues.length > 0) {
      setCommandFeedback({ tone: "error", message: `Mission validation failed: ${issues.join(" ")}` });
      return;
    }
    if (command === "init") {
      if (!activeWorldRuntime?.ready) {
        setCommandFeedback({ tone: "error", message: worldReadinessMessage });
        return;
      }
      await initializeMissionConfig(config);
      return;
    }
    const state = missionStates[config.mission_id];
    const stateConfig = asMissionConfig(state?.config);
    if (state && !missionConfigsEquivalent(config, stateConfig)) {
      setCommandFeedback({ tone: "warn", message: "This mission definition changed after its last Init. Re-init it before Approve or Start." });
      return;
    }
    const status = state ? missionStatusLabel(state) : "DRAFT";
    if (state?.command_target !== true) {
      setCommandFeedback({ tone: "warn", message: "Another mission is the legacy command target. Re-init this mission before Approve or Start." });
      return;
    }
    if (command === "approve" && !["PLANNED", "PLANNED_ALTERNATIVE"].includes(status)) {
      setCommandFeedback({ tone: "warn", message: "Wait for a planned mission before approving it." });
      return;
    }
    if (command === "start" && status !== "ACCEPTED") {
      setCommandFeedback({ tone: "warn", message: "Wait for an accepted mission before starting it." });
      return;
    }
    await runCommand(command, () => command === "approve"
      ? approveMission(config.mission_id)
      : startMission(config.mission_id), config.mission_id);
  }

  const hasMission = Boolean(missionText.trim());
  const hasSelectedMission = hasMission || Boolean(missionState);
  const missionPaneOpen = showNewMission || hasSelectedMission;
  const canSendMission = hasMission && validation.length === 0 && Boolean(activeWorldRuntime?.ready);
  const worldReadinessMessage = activeWorldRuntime?.ready
    ? ""
    : activeWorldRuntime?.status === "stale"
      ? "The active world became stale after backend containers stopped. Open Worlds and launch the definition again."
      : activeWorldRuntime?.error || activeWorldRuntime?.message || "Open Worlds and launch a definition before initializing a mission.";
  const initDisabledReason = !hasMission
    ? "Load or create a valid mission first."
    : validation.length > 0
      ? `Resolve the mission validation issue${validation.length === 1 ? "" : "s"} first.`
      : worldReadinessMessage;
  const currentStatus = missionState ? missionStatusLabel(missionState) : "";
  const missionMatchesState = Boolean(mission && missionState?.mission_id === mission.mission_id);
  const missionMatchesInitializedConfig = missionMatchesState && missionConfigsEquivalent(mission, asMissionConfig(missionState?.config));
  const missionIsCommandTarget = missionState?.command_target === true;
  const canApproveMission = missionMatchesInitializedConfig && missionIsCommandTarget && ["PLANNED", "PLANNED_ALTERNATIVE"].includes(currentStatus);
  const canStartMission = missionMatchesInitializedConfig && missionIsCommandTarget && currentStatus === "ACCEPTED";
  const activeMissionWorldBinding = worldBindingFromActiveWorld(activeWorldRuntime);
  const missionList = useMemo(() => {
    const ids = new Set([...Object.keys(missionConfigs), ...Object.keys(missionStates)]);
    return [...ids]
      .filter((missionId) => !hiddenMissionIds.has(missionId))
      .map((missionId) => ({
        mission_id: missionId,
        config: missionConfigs[missionId] ?? asMissionConfig(missionStates[missionId]?.config),
        state: missionStates[missionId],
        binding: missionStates[missionId]?.world_binding ?? missionWorldBindings[missionId],
      }))
      .filter((item) => sameWorldBinding(item.binding, activeMissionWorldBinding));
  }, [activeMissionWorldBinding, hiddenMissionIds, missionConfigs, missionStates, missionWorldBindings]);
  const assistantOperatorMissions = useMemo(
    () => operatorMissionConfigs(missionList),
    [missionList],
  );
  const selectedPlanningVariant = useMemo(
    () => planningDiagnostics?.variant_analysis?.variants?.find((variant) => variant.id === selectedPlanningVariantId),
    [planningDiagnostics, selectedPlanningVariantId],
  );
  const resizableWorkspace: ResizableWorkspace = workspace === "world" ? "world" : "c2";
  const rightPaneWidth = rightPaneWidths[resizableWorkspace];
  const rightPaneMinWidth = MIN_RIGHT_PANE_WIDTHS[resizableWorkspace];
  const assistantActive = workspace === "c2" && assistantOpen;
  const assistantPaneWidth = 48;
  const workspaceItems = advancedUiAvailable
    ? [
        { value: "c2", label: "C2" },
        { value: "world", label: "World" },
        { value: "context", label: "Context" },
        { value: "contracts", label: "Contracts" },
      ]
    : [
        { value: "c2", label: "C2" },
      ];
  const c2TabItems = advancedUiAvailable
    ? [
        { value: "mission", label: "Mission" },
        { value: "assets", label: "Assets" },
        { value: "diagnostics", label: "Diagnostics" },
      ]
    : [
        { value: "mission", label: "Mission" },
        { value: "assets", label: "Assets" },
      ];
  const c2PaneTitle = tab === "assets" ? "Assets" : tab === "diagnostics" ? "Diagnostics" : "Missions";
  const c2PaneIcon = tab === "assets"
      ? <MapPinned className="h-4 w-4 text-primary" />
      : tab === "diagnostics"
        ? <Bug className="h-4 w-4 text-primary" />
        : <ListChecks className="h-4 w-4 text-primary" />;

  useEffect(() => {
    paneScrollRef.current?.scrollTo({ top: 0, behavior: "auto" });
  }, [assistantActive, mission?.mission_id, showNewMission, tab, workspace]);

  function toggleAssistant() {
    if (assistantActive) {
      setAssistantOpen(false);
      return;
    }
    setWorkspace("c2");
    setAssistantOpen(true);
  }

  function resizeRightPane(width: number) {
    setRightPaneWidths((current) => ({ ...current, [resizableWorkspace]: Math.round(width) }));
  }

  function maxRightPaneWidth() {
    if (typeof window === "undefined") return rightPaneWidth;
    return Math.max(rightPaneMinWidth, window.innerWidth - assistantPaneWidth - MIN_MAP_WIDTH - RESIZE_HANDLE_WIDTH);
  }

  if (workspace === "context") {
    return (
      <main className="flex h-screen min-h-[720px] flex-col overflow-hidden bg-background text-foreground">
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-border px-4">
          <div className="flex min-w-0 items-center gap-2">
            <ScanEye className="h-5 w-5 shrink-0 text-primary" />
            <div className="min-w-0">
              <h2 className="text-sm font-semibold">Assistant Context Filter</h2>
              <p className="text-[10px] text-muted-foreground">Tick only the operational context the assistant should receive.</p>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <Tabs
              value={workspace}
              onValueChange={(value) => setWorkspace(value as Workspace)}
              items={workspaceItems}
            />
            <Badge tone={assistantContextExcludePaths.length > 0 ? "ok" : "default"}>
              {assistantContextExcludePaths.length} removed paths
            </Badge>
          </div>
        </header>
        <AssistantContextPage
          excludePaths={assistantContextExcludePaths}
          operatorMissions={assistantOperatorMissions}
          onChange={setAssistantContextExcludePaths}
        />
      </main>
    );
  }

  if (advancedUiAvailable && workspace === "contracts") {
    return (
      <main className="flex h-screen min-h-[720px] flex-col overflow-hidden bg-[#07111f] text-slate-100">
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-slate-800 bg-[#091522] px-4">
          <div className="flex min-w-0 items-center gap-2">
            <Workflow className="h-5 w-5 shrink-0 text-cyan-400" />
            <div className="min-w-0">
              <h2 className="text-sm font-semibold text-slate-100">System Contract Atlas</h2>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <Tabs
              value={workspace}
              onValueChange={(value) => setWorkspace(value as Workspace)}
              items={workspaceItems}
            />
            <Badge tone={contractsError ? "error" : "ok"}>
              {contractGraph?.atlas ? `${contractGraph.atlas.components.length} systems · ${contractGraph.atlas.interactions.length} contracts` : "atlas"}
            </Badge>
          </div>
        </header>
        <section className="min-h-0 flex-1 overflow-hidden">
          <ContractExplorer graph={contractGraph} busy={contractsBusy} error={contractsError} onRefresh={() => refreshContracts()} />
        </section>
      </main>
    );
  }

  return (
    <main className="flex h-screen min-h-[720px] overflow-hidden bg-background text-foreground">
      <MapView
        agents={mapAgents}
        features={mapViewFeatures}
        geojson={mapViewGeojson}
        osmRoads={mapUsesWorldContext ? undefined : osmRoads}
        worldRoads={workspace === "world" ? worldRoads : undefined}
        mission={mapMission}
        taskPlan={mapTaskPlan}
        plannerState={mapPlannerState}
        planningVariant={selectedPlanningVariant}
        selectedFeatureId={selectedFeatureId}
        focusFeatureIds={mapFocus?.featureIds}
        focusPoints={mapFocusPoints?.points}
        focusNonce={mapFocus?.nonce}
        focusPointsNonce={mapFocusPoints?.nonce}
        focusView={mapViewFocus}
        resetDraftNonce={mapDraftResetNonce}
        placingAgentName={placingWorldAgent?.name || placingWorldAgent?.agent_id}
        onPlaceAgent={placingWorldAgentId ? placeWorldAgent : undefined}
        onViewportChange={setCurrentMapView}
        onCreateFeature={(feature) => createDrawnFeature(feature).catch((error) => setApiError(String(error)))}
        onUpdateFeature={(featureId, feature) => updateDrawnFeature(featureId, feature).catch((error) => setApiError(String(error)))}
        onRemoveFeature={(feature) => removeFeature(feature).catch((error) => setApiError(String(error)))}
        onSetObjective={setFeatureAsObjective}
        onAddFeatureToMission={addFeatureToMission}
        missionComposerActive={showNewMission}
        onSelectFeature={selectMapFeature}
        onClearSelection={() => setSelectedFeatureId(undefined)}
      />

      <VerticalResizeHandle
        paneRef={rightPaneRef}
        width={rightPaneWidth}
        minWidth={rightPaneMinWidth}
        defaultWidth={DEFAULT_RIGHT_PANE_WIDTHS[resizableWorkspace]}
        getMaxWidth={maxRightPaneWidth}
        onResize={resizeRightPane}
      />

      <aside
        ref={rightPaneRef}
        className="flex min-w-0 shrink-0 flex-col bg-background"
        style={{
          width: rightPaneWidth,
          minWidth: rightPaneMinWidth,
          maxWidth: `calc(100vw - ${assistantPaneWidth + MIN_MAP_WIDTH + RESIZE_HANDLE_WIDTH}px)`,
        }}
      >
        <header className="flex h-14 items-center justify-between border-b border-border px-4">
          <div className="flex items-center gap-2">
            {workspace === "world" ? (advancedUiAvailable ? <SlidersHorizontal className="h-5 w-5 text-primary" /> : <Globe className="h-5 w-5 text-primary" />) : assistantActive ? <Bot className="h-5 w-5 text-primary" /> : <FileJson className="h-5 w-5 text-primary" />}
            <div>
              <h2 className="text-sm font-semibold">{workspace === "world" ? (advancedUiAvailable ? "World Builder" : "World Picker") : assistantActive ? "C2 Assistant" : "Mission Definition"}</h2>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Tabs
              value={workspace}
              onValueChange={(value) => setWorkspace(value as Workspace)}
              items={workspaceItems}
            />
            {assistantActive ? (
              <Badge tone={assistantStatus?.configured ? "ok" : "default"}>assistant</Badge>
            ) : workspace === "c2" ? (
              !missionPaneOpen ? <Badge>empty</Badge> : showNewMission && !hasMission ? <Badge>new</Badge> : !hasMission ? <Badge>runtime</Badge> : validation.length === 0 ? <Badge tone="ok">valid</Badge> : <Badge tone="error">{validation.length} issue{validation.length === 1 ? "" : "s"}</Badge>
            ) : (
              advancedUiAvailable
                ? <Badge tone="ok">builder</Badge>
                : <Badge tone={activeWorldRuntime?.ready ? "ok" : "default"}>{activeWorldRuntime?.ready ? "active" : "picker"}</Badge>
            )}
          </div>
        </header>

        {workspace === "c2" && !assistantActive && (
          <PaneNavigation
            title={missionPaneOpen ? mission?.name ?? missionState?.mission_id ?? "New mission" : c2PaneTitle}
            icon={missionPaneOpen ? undefined : c2PaneIcon}
            backLabel={missionPaneOpen ? "Missions" : undefined}
            onBack={missionPaneOpen ? closeMissionComposer : undefined}
            actions={missionPaneOpen
              ? missionState
                ? <Badge tone={missionStateTone(missionState)}>{missionStatusLabel(missionState)}</Badge>
                : <Badge tone={missionText.trim() && validation.length === 0 ? "ok" : "default"}>{missionText.trim() ? "draft" : "new"}</Badge>
              : tab === "mission" ? (
                <Button size="sm" variant="outline" onClick={startNewMission}>
                  <Plus className="h-4 w-4" />
                  New Mission
                </Button>
              ) : undefined}
          />
        )}

        {workspace === "c2" && !assistantActive && (
          <div className="space-y-3 border-b border-border px-4 py-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <Tabs
                value={tab}
                onValueChange={setTab}
                items={c2TabItems}
              />
              <span title={activeWorldRuntime?.error}>
                <Badge tone={activeWorldRuntime?.ready ? "ok" : "warn"}>
                  {activeWorldRuntime?.ready
                    ? `world: ${activeWorldRuntime.name ?? activeWorldRuntime.world_id}`
                    : activeWorldRuntime?.status === "stale"
                      ? "world stale"
                      : "no active world"}
                </Badge>
              </span>
            </div>
            {!activeWorldRuntime?.ready && (
              <div className="flex items-center justify-between gap-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-950">
                <span>{worldReadinessMessage}</span>
                <Button size="sm" variant="outline" className="shrink-0" onClick={() => setWorkspace("world")}>
                  Open Worlds
                </Button>
              </div>
            )}
            {hasSelectedMission && (
              <MissionRuntimeStatus
                mission={mission}
                missionState={missionState}
                plannerState={plannerState}
                agentTelemetry={agentTelemetry}
                busyCommand={busyCommand}
                initRequestedAt={initRequestedAt}
              />
            )}
            <div className="grid grid-cols-3 gap-2">
              <Button size="sm" variant="outline" onClick={() => sendInitMission().catch(() => undefined)} disabled={!canSendMission || Boolean(busyCommand)} title={canSendMission ? "Initialize this mission in the active world" : initDisabledReason}>
                <ShieldCheck className="h-4 w-4" />
                {busyCommand === "init" ? "Initializing" : "Init"}
              </Button>
              <Button size="sm" variant="outline" onClick={() => sendApproveMission().catch(() => undefined)} disabled={!canApproveMission || Boolean(busyCommand)} title={canApproveMission ? "Approve planned mission" : missionState && !missionIsCommandTarget ? "Re-init this mission to make it the legacy command target" : "Wait until the legacy mission status is PLANNED"}>
                <CheckCircle2 className="h-4 w-4" />
                {busyCommand === "approve" ? "Approving" : "Approve"}
              </Button>
              <Button size="sm" onClick={() => sendStartMission().catch(() => undefined)} disabled={!canStartMission || Boolean(busyCommand)} title={canStartMission ? "Start accepted mission" : missionState && !missionIsCommandTarget ? "Re-init this mission to make it the legacy command target" : "Wait until the legacy mission status is ACCEPTED"}>
                <Play className="h-4 w-4" />
                {busyCommand === "start" ? "Starting" : "Start"}
              </Button>
            </div>
            {commandFeedback && (
              <div className="flex items-start gap-2 rounded-md border border-border bg-panel px-3 py-2 text-xs">
                <Badge tone={commandFeedback.tone}>{commandFeedback.tone === "warn" ? "warning" : commandFeedback.tone}</Badge>
                <span className="leading-6">{commandFeedback.message}</span>
              </div>
            )}
            {apiError && <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">{apiError}</div>}
          </div>
        )}

        <section ref={paneScrollRef} className={assistantActive ? "flex min-h-0 flex-1 overflow-hidden" : "min-h-0 flex-1 overflow-auto overflow-x-hidden p-4"}>
          {assistantActive ? (
            <AssistantPanel
              status={assistantStatus}
              statusBusy={assistantStatusBusy}
              busy={assistantBusy}
              error={assistantError}
              conversationId={assistantConversationId}
              conversationHistory={assistantConversationHistory}
              messages={assistantMessages}
              prompt={assistantPrompt}
              missionConfigs={missionConfigs}
              missionStates={missionStates}
              selectedMissionId={mission?.mission_id}
              plannerState={plannerState}
              agentTelemetry={agentTelemetry}
              busyCommand={busyCommand}
              busyCommandMissionId={busyCommandMissionId}
              initRequestedAt={initRequestedAt}
              activeWorldReady={activeWorldRuntime?.ready === true}
              commandFeedback={commandFeedback}
              debugAvailable={advancedUiAvailable}
              debugEnabled={assistantDebugEnabled}
              onPromptChange={setAssistantPrompt}
              onDebugEnabledChange={setAssistantDebugEnabled}
              onOpenContext={() => setWorkspace("context")}
              contextRemovedCount={assistantContextExcludePaths.length}
              onSend={() => submitAssistantMessage().catch(() => undefined)}
              onNewConversation={startAssistantConversation}
              onSelectConversation={chooseAssistantConversation}
              onDeleteConversation={() => deleteCurrentAssistantConversation().catch(() => undefined)}
              onRefreshStatus={() => refreshAssistantStatus().catch(() => undefined)}
              onOpenMission={(response) => {
                const config = selectAssistantProposal(response, true);
                if (config) setCommandFeedback({ tone: "ok", message: "Assistant mission opened in the manual editor and shown on the map." });
              }}
              onValidateMission={validateAssistantProposal}
              onMissionCommand={(response, command) => runAssistantMissionCommand(response, command).catch(() => undefined)}
            />
          ) : workspace === "c2" ? (
            <>
              {tab === "mission" && (
                <MissionPanel
                  examples={examples}
                  mission={mission}
                  missionText={missionText}
                  missionState={missionState}
                  missionList={missionList}
                  taskPlan={taskPlan}
                  showNewMission={showNewMission}
                  validation={validation}
                  onLoadExample={loadExample}
                  onSelectMission={selectMission}
                  onForgetMission={(missionId) => forgetMission(missionId).catch((error) => setApiError(String(error)))}
                  onMissionTextChange={updateMissionText}
                  missionJsonRef={missionJsonRef}
                  jsonFocusLabel={jsonFocus?.label}
                  onClear={clearMission}
                />
              )}

              {tab === "assets" && <AssetsPanel agents={c2Agents} mapFeatures={c2MapFeatures} mission={mission} selectedFeatureId={selectedFeatureId} onSetObjective={setFeatureAsObjective} onRemoveFeature={(feature) => removeFeature(feature).catch((error) => setApiError(String(error)))} />}

              {tab === "diagnostics" && (
                <DiagnosticsPanel
                  diagnostics={diagnostics}
                  legacyTrace={legacyTrace}
                  plannerState={plannerState}
                  planningDiagnostics={planningDiagnostics}
                  planningDiagnosticsBusy={planningDiagnosticsBusy}
                  selectedPlanningVariantId={selectedPlanningVariantId}
                  legacyResetBusy={legacyResetBusy}
                  legacyResetResult={legacyResetResult}
                  onRefreshLegacyTrace={() => refreshLegacyTrace().catch((error) => setApiError(String(error)))}
                  onRefreshPlanningDiagnostics={() => refreshPlanningDiagnostics()}
                  onSelectPlanningVariant={(worldId) => setSelectedPlanningVariantId((current) => (current === worldId ? undefined : worldId))}
                  onCleanLegacyRuntime={() => cleanLegacyRuntimeForExamples()}
                />
              )}
            </>
          ) : (
            advancedUiAvailable ? (
              <WorldBuilder
                mapFeatures={mapFeatures}
                mapFeaturesReady={mapFeaturesReady}
                selectedFeatureId={selectedFeatureId}
                pendingFeatureToAdd={pendingWorldFeatureToAdd}
                pendingFeatureToDelete={pendingWorldFeatureToDelete}
                pendingAgentPlacement={pendingWorldAgentPlacement}
                currentMapView={currentMapView}
                catalogWorlds={worldCatalog}
                placingAgentId={placingWorldAgentId}
                onWorldAgentsChange={applyWorldAgents}
                onActiveWorldFeaturesChange={applyWorldFeatureIds}
                onWorldRoadsChange={applyWorldRoads}
                onWorldLibraryChange={applyWorldLibrary}
                onSelectFeature={selectMapFeature}
                onDeleteAuthoringFeature={deleteWorldAuthoringFeature}
                onLaunchWorld={launchWorldFromLab}
                onWorldContextReset={resetWorldWorkspace}
                onBeginPlaceAgent={beginPlaceWorldAgent}
                onCancelPlaceAgent={cancelPlaceWorldAgent}
              />
            ) : (
              <WorldPicker
                catalogWorlds={worldCatalog}
                activeWorldId={activeWorldRuntime?.world_id}
                onWorldContextChange={handleWorldContextChange}
                onLaunchWorld={launchWorldFromLab}
              />
            )
          )}
        </section>
      </aside>

      <aside className="flex w-12 shrink-0 flex-col border-l border-border bg-panel">
        <button
          className={`flex h-14 w-full items-center justify-center border-b border-border hover:bg-muted ${assistantActive ? "bg-muted" : ""}`}
          onClick={toggleAssistant}
          title={assistantActive ? "Return to manual mission UI" : "Open C2 Assistant"}
          aria-label={assistantActive ? "Return to manual mission UI" : "Open C2 Assistant"}
          aria-pressed={assistantActive}
        >
          {assistantActive ? <ArrowLeft className="h-5 w-5 text-primary" /> : <Bot className="h-5 w-5 text-primary" />}
        </button>
      </aside>
    </main>
  );
}

function AssistantPanel({
  status,
  statusBusy,
  busy,
  error,
  conversationId,
  conversationHistory,
  messages,
  prompt,
  missionConfigs,
  missionStates,
  selectedMissionId,
  plannerState,
  agentTelemetry,
  busyCommand,
  busyCommandMissionId,
  initRequestedAt,
  activeWorldReady,
  commandFeedback,
  debugAvailable,
  debugEnabled,
  contextRemovedCount,
  onPromptChange,
  onDebugEnabledChange,
  onOpenContext,
  onSend,
  onNewConversation,
  onSelectConversation,
  onDeleteConversation,
  onRefreshStatus,
  onOpenMission,
  onValidateMission,
  onMissionCommand,
}: {
  status?: AssistantStatus;
  statusBusy: boolean;
  busy: boolean;
  error: string;
  conversationId: string;
  conversationHistory: AssistantConversationSummary[];
  messages: AssistantTranscriptItem[];
  prompt: string;
  missionConfigs: Record<string, MissionConfig>;
  missionStates: Record<string, MissionState>;
  selectedMissionId?: string;
  plannerState?: PlannerUpdateEvent;
  agentTelemetry: Record<string, AgentUpdateEvent>;
  busyCommand?: "init" | "approve" | "start";
  busyCommandMissionId?: string;
  initRequestedAt?: number;
  activeWorldReady: boolean;
  commandFeedback?: { tone: "default" | "ok" | "warn" | "error"; message: string };
  debugAvailable: boolean;
  debugEnabled: boolean;
  contextRemovedCount: number;
  onPromptChange: (value: string) => void;
  onDebugEnabledChange: (value: boolean) => void;
  onOpenContext: () => void;
  onSend: () => void;
  onNewConversation: () => void;
  onSelectConversation: (conversationId: string) => void;
  onDeleteConversation: () => void;
  onRefreshStatus: () => void;
  onOpenMission: (response: AssistantMessageResponse) => void;
  onValidateMission: (response: AssistantMessageResponse) => void;
  onMissionCommand: (response: AssistantMessageResponse, command: "init" | "approve" | "start") => void;
}) {
  const transcriptEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: busy ? "auto" : "smooth", block: "end" });
  }, [busy, conversationId, messages.length, messages[messages.length - 1]?.text]);

  const configured = status?.configured === true;
  const statusTone = statusBusy ? "default" : configured ? "ok" : "warn";
  const statusLabel = statusBusy ? "checking" : configured ? "ready" : "not configured";

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="shrink-0 space-y-2 border-b border-border p-4">
        <div className="flex items-center gap-1.5">
          <select
            className="h-8 min-w-0 flex-1 rounded-md border border-border bg-background px-2 text-xs outline-none focus:ring-2 focus:ring-ring"
            value={conversationId}
            disabled={busy}
            onChange={(event) => onSelectConversation(event.target.value)}
            aria-label="Assistant conversation history"
            title="Conversation history is stored in this browser; model continuity is best-effort after a backend restart"
          >
            {conversationHistory.map((conversation) => (
              <option key={conversation.conversationId} value={conversation.conversationId}>
                {assistantHistoryOptionLabel(conversation)}
              </option>
            ))}
          </select>
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={busy}
            onClick={onNewConversation}
            title="New conversation"
            aria-label="Start a new assistant conversation"
          >
            <Plus className="h-4 w-4" />
            New
          </Button>
          <Button
            type="button"
            size="icon"
            variant="ghost"
            className="h-8 w-8"
            disabled={busy || (messages.length === 0 && conversationHistory.length === 1)}
            onClick={onDeleteConversation}
            title="Delete this conversation"
            aria-label="Delete this assistant conversation"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
        <div className="flex items-center justify-between gap-2">
          <span title={status ? `${status.model} · ${status.base_url} · ${status.reasoning_effort || "default"} thinking · prompts ${status.prompt_version}` : undefined}>
            <Badge tone={statusTone}>{statusLabel}</Badge>
          </span>
          <div className="flex items-center gap-1">
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={onOpenContext}
              title="Choose exactly which operational context the assistant receives"
            >
              <ScanEye className="h-3.5 w-3.5" />
              Context{contextRemovedCount > 0 ? ` · ${contextRemovedCount} removed` : ""}
            </Button>
            {debugAvailable && (
              <Button
                type="button"
                size="sm"
                variant="outline"
                className={debugEnabled ? "border-primary/40 bg-primary/10 text-primary" : undefined}
                role="switch"
                aria-checked={debugEnabled}
                disabled={busy}
                onClick={() => onDebugEnabledChange(!debugEnabled)}
                title="Include and reveal the safe backend model-input and execution trace for new messages"
              >
                <Bug className="h-3.5 w-3.5" />
                Debug {debugEnabled ? "on" : "off"}
              </Button>
            )}
            {!configured && !statusBusy && (
              <Button type="button" size="sm" variant="outline" onClick={onRefreshStatus}>
                <RefreshCw className="h-3.5 w-3.5" />
                Retry
              </Button>
            )}
          </div>
        </div>
      </div>

      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-3" aria-live="polite">
        {messages.length === 0 && (
          <div className="rounded-md border border-dashed border-border bg-background p-3 text-xs leading-5 text-muted-foreground">
            Ask about operations or request a mission draft.
          </div>
        )}

        {messages.map((item) => {
          const response = item.response;
          const proposal = assistantProposalConfig(response);
          const proposalState = proposal ? missionStates[proposal.mission_id] : undefined;
          const proposalConfig = proposal
            ? missionConfigs[proposal.mission_id] ?? asMissionConfig(proposalState?.config) ?? proposal
            : undefined;
          const proposalSelected = Boolean(proposalConfig && selectedMissionId === proposalConfig.mission_id);
          return (
            <div key={item.id} className={item.role === "user" ? "flex justify-end" : "flex justify-start"}>
              <div
                className={
                  item.role === "user"
                    ? "max-w-[90%] rounded-md border border-primary/30 bg-primary/10 px-3 py-2 text-xs"
                    : "max-w-[96%] space-y-2 rounded-md border border-border bg-background px-3 py-2 text-xs"
                }
                >
                <p className="whitespace-pre-wrap break-words leading-5">{item.text}</p>

                {response && (
                  <>
                    {debugEnabled && (
                      <div className="flex flex-wrap items-center gap-1 text-[11px] text-muted-foreground">
                        <span>picture r{response.picture_revision}</span>
                        <span aria-hidden="true">·</span>
                        <span title={response.picture_observed_at}>{formatAssistantObservedAt(response.picture_observed_at)}</span>
                        <span aria-hidden="true">·</span>
                        <span>prompt {response.prompt_version}</span>
                      </div>
                    )}

                    {response.warnings.length > 0 && (
                      <div className="rounded-md border border-amber-200 bg-amber-50 px-2 py-1.5 text-amber-950">
                        <p className="font-medium">Warnings</p>
                        <ul className="mt-1 list-disc space-y-1 pl-4">
                          {response.warnings.map((warning, index) => <li key={`${item.id}-warning-${index}`}>{warning}</li>)}
                        </ul>
                      </div>
                    )}

                    {response.assumptions.length > 0 && (
                      <details className="rounded-md border border-border bg-muted px-2 py-1.5 text-muted-foreground">
                        <summary className="cursor-pointer font-medium text-foreground">
                          {response.assumptions.length} assumption{response.assumptions.length === 1 ? "" : "s"}
                        </summary>
                        <ul className="mt-1 list-disc space-y-1 pl-4">
                          {response.assumptions.map((assumption, index) => <li key={`${item.id}-assumption-${index}`}>{assumption}</li>)}
                        </ul>
                      </details>
                    )}

                    {response.mission_proposal && (
                      <AssistantMissionCard
                        response={response}
                        config={proposalConfig}
                        state={proposalState}
                        plannerState={proposalSelected ? plannerState : undefined}
                        agentTelemetry={agentTelemetry}
                        busyCommand={busyCommandMissionId === proposalConfig?.mission_id ? busyCommand : undefined}
                        initRequestedAt={proposalSelected ? initRequestedAt : undefined}
                        selected={proposalSelected}
                        activeWorldReady={activeWorldReady}
                        feedback={proposalSelected ? commandFeedback : undefined}
                        onOpen={() => onOpenMission(response)}
                        onValidate={() => onValidateMission(response)}
                        onCommand={(command) => onMissionCommand(response, command)}
                      />
                    )}
                  </>
                )}

                {debugEnabled && item.role === "assistant" && (
                  <AssistantDebugDisclosure
                    debugRequested={item.debugRequested === true}
                    trace={response?.debug_trace}
                  />
                )}
              </div>
            </div>
          );
        })}

        {busy && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <RefreshCw className="h-3.5 w-3.5 animate-spin" />
            Reading context and generating the answer…
          </div>
        )}
        <div ref={transcriptEndRef} />
      </div>

      <form
        className="shrink-0 space-y-2 border-t border-border p-3"
        onSubmit={(event) => {
          event.preventDefault();
          onSend();
        }}
      >
        {error && <div className="rounded-md border border-red-200 bg-red-50 px-2 py-1.5 text-xs text-red-900">{error}</div>}
        {!statusBusy && status && !status.configured && (
          <div className="rounded-md border border-amber-200 bg-amber-50 px-2 py-1.5 text-xs leading-5 text-amber-950">
            The backend has no assistant API key configured. Configure it server-side, then retry status.
          </div>
        )}
        <div className="rounded-md border border-input bg-panel shadow-sm focus-within:ring-2 focus-within:ring-ring">
          <Textarea
            className="max-h-40 min-h-10 resize-none overflow-y-auto border-0 bg-transparent px-3 pt-2.5 pb-1 font-sans text-sm leading-5 shadow-none focus:ring-0"
            value={prompt}
            onChange={(event) => onPromptChange(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
                event.preventDefault();
                if (!event.currentTarget.disabled && prompt.trim()) onSend();
              }
            }}
            placeholder={configured ? "Ask about operations or request a mission…" : "Assistant unavailable"}
            disabled={!configured || busy}
            rows={2}
            aria-label="Message the mission assistant"
          />
          <div className="flex items-center justify-between gap-2 px-2 pb-1.5">
            <span className="select-none pl-1 text-[10px] text-muted-foreground">
              Enter sends · Shift+Enter newline
            </span>
            <Button
              type="submit"
              size="icon"
              className="h-7 w-7 shrink-0"
              disabled={!configured || busy || !prompt.trim()}
              title={busy ? "Working…" : "Send (Enter)"}
              aria-label={busy ? "Working" : "Send message"}
            >
              {busy ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
            </Button>
          </div>
        </div>
      </form>
    </div>
  );
}

function AssistantMissionCard({
  response,
  config,
  state,
  plannerState,
  agentTelemetry,
  busyCommand,
  initRequestedAt,
  selected,
  activeWorldReady,
  feedback,
  onOpen,
  onValidate,
  onCommand,
}: {
  response: AssistantMessageResponse;
  config?: MissionConfig;
  state?: MissionState;
  plannerState?: PlannerUpdateEvent;
  agentTelemetry: Record<string, AgentUpdateEvent>;
  busyCommand?: "init" | "approve" | "start";
  initRequestedAt?: number;
  selected: boolean;
  activeWorldReady: boolean;
  feedback?: { tone: "default" | "ok" | "warn" | "error"; message: string };
  onOpen: () => void;
  onValidate: () => void;
  onCommand: (command: "init" | "approve" | "start") => void;
}) {
  const validation = response.mission_proposal_validation;
  const valid = validation?.valid === true && Boolean(config);
  const status = state ? missionStatusLabel(state) : "DRAFT";
  const isCommandTarget = state?.command_target === true;
  const initializedConfig = asMissionConfig(state?.config);
  const revisionPending = Boolean(state && config && !missionConfigsEquivalent(config, initializedConfig));
  const canApprove = valid && !revisionPending && isCommandTarget && ["PLANNED", "PLANNED_ALTERNATIVE"].includes(status) && !busyCommand;
  const canStart = valid && !revisionPending && isCommandTarget && status === "ACCEPTED" && !busyCommand;
  const canInit = valid && activeWorldReady && !busyCommand;

  return (
    <div className={`space-y-2 rounded-md border bg-muted p-2 ${selected ? "border-primary shadow-sm" : "border-border"}`}>
      <div className="flex items-start justify-between gap-2">
        <button
          type="button"
          className="min-w-0 flex-1 rounded-sm text-left outline-none focus-visible:ring-2 focus-visible:ring-ring"
          onClick={onOpen}
          disabled={!config}
          title={config ? "Open this mission in the manual editor and show it on the map" : "This proposal is not a loadable mission"}
        >
          <div className="truncate font-semibold">{config?.name ?? "Mission proposal"}</div>
          <div className="mt-0.5 break-all font-mono text-[10px] text-muted-foreground">Mission ID: {config?.mission_id ?? "not assigned"}</div>
        </button>
        <Badge tone={valid ? revisionPending ? "warn" : state ? missionStateTone(state) : "ok" : "error"}>
          {valid ? revisionPending ? "Changes pending" : state ? humanizeEnum(status) : "Validated draft" : "Invalid"}
        </Badge>
      </div>

      {config && (
        <div className="flex flex-wrap gap-1">
          <Badge>{behaviorLabel(config.behavior)}</Badge>
          <Badge>{vehicleCountLabel(config)}</Badge>
          <Badge>{objectiveSummary(config)}</Badge>
          <Badge tone="ok">saved in Missions</Badge>
        </div>
      )}

      {validation?.valid === false && validation.issues?.length > 0 && (
        <ul className="list-disc space-y-1 pl-4 text-muted-foreground">
          {validation.issues.map((issue, index) => (
            <li key={`${config?.mission_id ?? "proposal"}-issue-${index}`}>
              {issue.path ? `${issue.path}: ` : ""}{issue.message}
            </li>
          ))}
        </ul>
      )}

      {validation?.valid === true && !activeWorldReady && validation.command_ready === false && validation.command_issues && validation.command_issues.length > 0 && (
        <ul className="list-disc space-y-1 pl-4 text-amber-900">
          {validation.command_issues.map((issue, index) => (
            <li key={`${config?.mission_id ?? "proposal"}-command-issue-${index}`}>{issue.message}</li>
          ))}
        </ul>
      )}

      {valid && (
        <>
          <MissionRuntimeStatus
            mission={config}
            missionState={state}
            plannerState={plannerState}
            agentTelemetry={agentTelemetry}
            busyCommand={busyCommand}
            initRequestedAt={initRequestedAt}
          />
          {revisionPending && (
            <div className="rounded-md border border-amber-200 bg-amber-50 px-2 py-1.5 text-[10px] leading-4 text-amber-950">
              The working copy changed after the last Init. The status and route above belong to the previous definition; Re-init to request a replacement plan.
            </div>
          )}
          {state && !isCommandTarget && (
            <div className="rounded-md border border-amber-200 bg-amber-50 px-2 py-1.5 text-[10px] leading-4 text-amber-950">
              Another mission is the legacy command target. Re-init this mission before Approve or Start.
            </div>
          )}
          <div className="grid grid-cols-2 gap-1.5">
            <Button type="button" size="sm" variant="outline" onClick={onValidate} disabled={Boolean(busyCommand)} title="Revalidate against the current UI contracts and show this mission on the map">
              <CheckCircle2 className="h-3.5 w-3.5" />
              Validate + map
            </Button>
            <Button type="button" size="sm" variant="outline" onClick={onOpen} disabled={Boolean(busyCommand)} title="Open the editable mission in the manual UI">
              <FileJson className="h-3.5 w-3.5" />
              Open
            </Button>
          </div>
          <div className="grid grid-cols-3 gap-1.5">
            <Button type="button" size="sm" variant="outline" onClick={() => onCommand("init")} disabled={!canInit} title={activeWorldReady ? "Initialize this mission and request planning" : "A ready environment is required before Init"}>
              <ShieldCheck className="h-3.5 w-3.5" />
              {busyCommand === "init" ? "Initializing" : state ? "Re-init" : "Init"}
            </Button>
            <Button type="button" size="sm" variant="outline" onClick={() => onCommand("approve")} disabled={!canApprove} title={canApprove ? "Approve this planned mission" : state && !isCommandTarget ? "Re-init this mission to make it the legacy command target" : "Approve unlocks when mission status is PLANNED"}>
              <CheckCircle2 className="h-3.5 w-3.5" />
              {busyCommand === "approve" ? "Approving" : "Approve"}
            </Button>
            <Button type="button" size="sm" onClick={() => onCommand("start")} disabled={!canStart} title={canStart ? "Start this accepted mission" : state && !isCommandTarget ? "Re-init this mission to make it the legacy command target" : "Start unlocks when mission status is ACCEPTED"}>
              <Play className="h-3.5 w-3.5" />
              {busyCommand === "start" ? "Starting" : "Start"}
            </Button>
          </div>
        </>
      )}

      {selected && feedback && (
        <div className={`rounded-md border px-2 py-1.5 text-[11px] leading-4 ${feedback.tone === "error" ? "border-red-200 bg-red-50 text-red-900" : feedback.tone === "warn" ? "border-amber-200 bg-amber-50 text-amber-950" : "border-emerald-200 bg-emerald-50 text-emerald-900"}`}>
          {feedback.message}
        </div>
      )}
    </div>
  );
}

function AssistantDebugDisclosure({
  debugRequested,
  trace,
}: {
  debugRequested: boolean;
  trace?: AssistantDebugTrace | null;
}) {
  if (!debugRequested) {
    return (
      <div className="mt-2 rounded-md border border-dashed border-border bg-muted px-2 py-1.5 text-[11px] text-muted-foreground">
        This turn has no debug capture. Enable Debug before sending a new message.
      </div>
    );
  }

  const modelMessages = firstDebugArray(trace, ["model_messages", "messages", "prompt_messages"]);
  const toolCalls = firstDebugArray(trace, ["tool_calls", "model_tool_calls", "llm_tool_calls"]);
  const traceEvents = firstDebugArray(trace, ["events", "backend_events", "execution_events"]);
  const modelEvents = traceEvents.filter(isModelProviderDebugEvent);
  const backendEvents = traceEvents.filter((event) => !isModelProviderDebugEvent(event) && debugEventType(event) !== "tool_call");
  const modelFinalEvent = traceEvents.find((event) => debugEventType(event) === "model_final");
  const contextUsage = asDebugRecord(trace?.context_usage) ?? asDebugRecord(asDebugRecord(modelFinalEvent)?.context_usage);
  const picture = asDebugRecord(trace?.operational_picture);

  return (
    <div className="mt-2 space-y-2 border-t border-dashed border-border pt-2 text-[11px]">
      <div className="flex flex-wrap items-center justify-between gap-1">
        <span className="font-medium text-foreground">Diagnostic trace</span>
        <Badge tone={trace ? "ok" : "warn"}>{trace ? "captured" : "unavailable"}</Badge>
      </div>

      <AssistantContextUsageBar usage={contextUsage} />

      {trace && (
        <details className="rounded-md border border-border bg-panel">
          <summary className="cursor-pointer px-2 py-1.5 font-medium text-foreground">
            Operational picture sent to model
            {picture && <span className="ml-1.5 font-normal text-muted-foreground">({debugPictureSummary(picture)})</span>}
          </summary>
          <div className="space-y-1.5 border-t border-border p-2">
            {picture ? (
              <>
                <div className="flex flex-wrap items-center gap-1.5">
                  <DebugPictureChip label="map" value={asDebugRecord(asDebugRecord(picture.current_environment)?.map)?.name} />
                  <DebugPictureChip label="revision" value={picture.picture_revision} />
                  <DebugPictureChip label="observed" value={picture.observed_at} />
                  <DebugPictureChip label="readiness" value={asDebugRecord(asDebugRecord(picture.current_environment)?.readiness)?.status} />
                </div>
                <OperationalPictureIdIndex picture={picture} />
                <JsonExplorer value={safeDebugValue(picture)} maxHeightClassName="max-h-64" />
              </>
            ) : (
              <p className="leading-4 text-muted-foreground">No operational-picture capture was returned for this turn.</p>
            )}
          </div>
        </details>
      )}

      <div className="rounded-md border border-border bg-panel p-2">
        <div className="flex items-center justify-between gap-2">
          <span className="font-medium">LLM tool calls</span>
          <Badge tone={toolCalls.length > 0 ? "warn" : "default"}>{toolCalls.length}</Badge>
        </div>
        {toolCalls.length === 0 ? (
          <p className="mt-1 leading-4 text-muted-foreground">
            None. This assistant currently exposes no callable tools to the model.
          </p>
        ) : (
          <div className="mt-2 space-y-1.5">
            {toolCalls.map((toolCall, index) => (
              <DebugTraceCard key={`llm-tool-${index}`} value={toolCall} fallbackLabel={`Tool call ${index + 1}`} />
            ))}
          </div>
        )}
      </div>

      <details className="rounded-md border border-border bg-panel">
        <summary className="cursor-pointer px-2 py-1.5 font-medium text-foreground">
          Exact model input ({modelMessages.length} message{modelMessages.length === 1 ? "" : "s"}; secrets redacted)
        </summary>
        <div className="space-y-1.5 border-t border-border p-2">
          {modelMessages.length === 0 ? (
            <p className="leading-4 text-muted-foreground">No model-input capture was returned.</p>
          ) : modelMessages.map((modelMessage, index) => (
            <DebugTraceCard key={`model-message-${index}`} value={modelMessage} fallbackLabel={`Message ${index + 1}`} />
          ))}
        </div>
      </details>

      {modelEvents.length > 0 && (
        <details className="rounded-md border border-border bg-panel">
          <summary className="cursor-pointer px-2 py-1.5 font-medium text-foreground">
            Model/provider request ({modelEvents.length} event{modelEvents.length === 1 ? "" : "s"})
          </summary>
          <div className="border-t border-border p-2">
            <p className="mb-1.5 leading-4 text-muted-foreground">
              Provider request and result events are diagnostics, not tool calls.
            </p>
            <JsonExplorer value={safeDebugValue(modelEvents)} maxHeightClassName="max-h-64" />
          </div>
        </details>
      )}

      <details className="rounded-md border border-border bg-panel">
        <summary className="cursor-pointer px-2 py-1.5 font-medium text-foreground">
          Backend context and validation ({backendEvents.length} event{backendEvents.length === 1 ? "" : "s"})
        </summary>
        <div className="space-y-1.5 border-t border-border p-2">
          <p className="leading-4 text-muted-foreground">
            These are deterministic backend operations, not tools available to or selected by the LLM.
          </p>
          {backendEvents.length === 0 ? (
            <p className="leading-4 text-muted-foreground">No backend events were returned.</p>
          ) : backendEvents.map((event, index) => (
            <DebugTraceCard key={`backend-event-${index}`} value={event} fallbackLabel={`Backend event ${index + 1}`} />
          ))}
        </div>
      </details>

      {trace && (
        <details className="rounded-md border border-border bg-panel">
          <summary className="cursor-pointer px-2 py-1.5 font-medium text-foreground">Raw safe trace envelope</summary>
          <div className="border-t border-border p-2">
            <JsonExplorer value={safeDebugValue(trace)} />
          </div>
        </details>
      )}
    </div>
  );
}

function AssistantContextUsageBar({ usage }: { usage: Record<string, unknown> | undefined }) {
  const limit = asFiniteNumber(usage?.context_limit);
  if (!usage || !limit || limit <= 0) return null;
  const promptTokens = asFiniteNumber(usage.prompt_tokens);
  const completionTokens = asFiniteNumber(usage.completion_tokens);
  const totalTokens = asFiniteNumber(usage.total_tokens) ?? (promptTokens ?? 0) + (completionTokens ?? 0);
  const usedPercent = asFiniteNumber(usage.context_used_percent) ?? (totalTokens / limit) * 100;
  const barPercent = Math.max(0, Math.min(100, usedPercent));
  const remainingTokens = asFiniteNumber(usage.remaining_tokens) ?? Math.max(limit - totalTokens, 0);
  const formatTokens = (value: number | undefined) => (value === undefined ? "?" : value.toLocaleString());
  return (
    <div className="rounded-md border border-border bg-panel p-2">
      <div className="flex items-center justify-between gap-2">
        <span className="font-medium">Context tokens</span>
        <span
          className={`tabular-nums ${usedPercent >= 90 ? "text-red-700" : "text-muted-foreground"}`}
          title={`${totalTokens.toLocaleString()} of ${limit.toLocaleString()} context tokens used`}
        >
          {usedPercent.toFixed(1)}% of {limit.toLocaleString()}
        </span>
      </div>
      <div
        className="mt-1.5 h-1 w-full overflow-hidden rounded-full bg-muted"
        role="progressbar"
        aria-label="Context window usage"
        aria-valuemin={0}
        aria-valuemax={limit}
        aria-valuenow={totalTokens}
      >
        <div className={`h-full ${usedPercent >= 90 ? "bg-red-500" : "bg-primary"}`} style={{ width: `${barPercent}%` }} />
      </div>
      <p className="mt-1 leading-4 text-muted-foreground tabular-nums">
        prompt {formatTokens(promptTokens)} + completion {formatTokens(completionTokens)} · {formatTokens(remainingTokens)} remaining
      </p>
    </div>
  );
}

function asFiniteNumber(value: unknown): number | undefined {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

function DebugTraceCard({ value, fallbackLabel }: { value: unknown; fallbackLabel: string }) {
  const record = asDebugRecord(value);
  const label = debugLabel(record, fallbackLabel);
  const status = typeof record?.status === "string" ? record.status : undefined;
  return (
    <div className="rounded-md border border-border bg-background p-2">
      <div className="mb-1 flex items-center justify-between gap-2">
        <span className="min-w-0 truncate font-medium text-foreground" title={label}>{label}</span>
        {status && <Badge tone={status.toLowerCase().includes("error") ? "error" : "default"}>{status}</Badge>}
      </div>
      <JsonExplorer value={safeDebugValue(value)} maxHeightClassName="max-h-64" />
    </div>
  );
}

function firstDebugArray(trace: AssistantDebugTrace | null | undefined, keys: string[]): unknown[] {
  if (!trace) return [];
  for (const key of keys) {
    const value = trace[key];
    if (Array.isArray(value)) return value;
  }
  return [];
}

function asDebugRecord(value: unknown): Record<string, unknown> | undefined {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : undefined;
}

function debugLabel(record: Record<string, unknown> | undefined, fallback: string) {
  if (!record) return fallback;
  for (const key of ["name", "role", "type", "event", "operation"]) {
    const value = record[key];
    if (typeof value === "string" && value.trim()) return value;
  }
  return fallback;
}

function debugEventType(value: unknown) {
  const record = asDebugRecord(value);
  for (const key of ["type", "event", "name", "operation"]) {
    const candidate = record?.[key];
    if (typeof candidate === "string" && candidate.trim()) return candidate.trim().toLowerCase();
  }
  return "";
}

function isModelProviderDebugEvent(value: unknown) {
  const type = debugEventType(value);
  return type.startsWith("model_") || type.startsWith("provider_");
}

function debugPictureSummary(picture: Record<string, unknown>): string {
  const environment = asDebugRecord(picture.current_environment);
  const mapName = asDebugRecord(environment?.map)?.name;
  const counts = (["agents", "missions", "plans"] as const).map(
    (section) => `${debugPictureItemCount(picture[section])} ${section}`,
  );
  return [typeof mapName === "string" && mapName ? mapName : undefined, ...counts]
    .filter(Boolean)
    .join(" · ");
}

function debugPictureItemCount(section: unknown): number {
  const items = asDebugRecord(section)?.items;
  return Array.isArray(items) ? items.length : 0;
}

function OperationalPictureIdIndex({ picture }: { picture: Record<string, unknown> }) {
  const environment = asDebugRecord(picture.current_environment);
  const runtimeSections = ([
    ["agents", "Vehicle ID"],
    ["missions", "Mission ID"],
    ["plans", "Mission / plan ID"],
  ] as const).map(([section, idLabel]) => {
    const items = asDebugRecord(picture[section])?.items;
    const ids = Array.isArray(items)
      ? items.map((item) => asDebugRecord(item)?.id).filter((itemId): itemId is string => typeof itemId === "string" && Boolean(itemId))
      : [];
    return { section, idLabel, ids };
  });
  const environmentSections = ([
    ["map_features", "Map feature ID"],
  ] as const).map(([section, idLabel]) => {
    const items = environment?.[section];
    const ids = Array.isArray(items)
      ? items.map((item) => {
          const record = asDebugRecord(item);
          return record?.feature_id ?? record?.id;
        }).filter((itemId): itemId is string => typeof itemId === "string" && Boolean(itemId))
      : [];
    return { section, idLabel, ids };
  });
  const sections = [...runtimeSections, ...environmentSections].filter((section) => section.ids.length > 0);
  if (sections.length === 0) return null;
  return (
    <div className="space-y-1 rounded-md border border-border bg-background p-2">
      <div className="font-medium text-foreground">Included IDs</div>
      {sections.map((section) => (
        <div key={section.section}>
          <div className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">{section.section}</div>
          {section.ids.map((itemId) => (
            <div key={`${section.section}-${itemId}`} className="break-all font-mono text-[10px] text-foreground">
              {section.idLabel}: {itemId}
            </div>
          ))}
        </div>
      ))}
      {sections.some((section) => section.section === "plans") && (
        <p className="leading-4 text-muted-foreground">The current backend does not issue a separate plan ID; a stored plan is keyed by its mission ID.</p>
      )}
    </div>
  );
}

function DebugPictureChip({ label, value }: { label: string; value: unknown }) {
  if (typeof value !== "string" && typeof value !== "number") return null;
  const text = String(value);
  return (
    <span
      className="inline-flex max-w-full items-center gap-1 rounded-md border border-border bg-background px-1.5 py-0.5 tabular-nums"
      title={`${label}: ${text}`}
    >
      <span className="shrink-0 text-muted-foreground">{label}</span>
      <span className="min-w-0 truncate text-foreground">{text}</span>
    </span>
  );
}

function safeDebugJson(value: unknown) {
  const sensitiveKey = /^(authorization|proxy_authorization|api[_-]?key|apikey|x[_-]?api[_-]?key|password|secret)$/i;
  const redactString = (text: string) => text
    .replace(/\bBearer\s+[^\s"']+/gi, "Bearer [REDACTED]")
    .replace(/\bsk-[A-Za-z0-9:_-]{8,}/g, "[REDACTED API KEY]");
  try {
    return JSON.stringify(value, (key, item) => {
      if (sensitiveKey.test(key)) return "[REDACTED]";
      return typeof item === "string" ? redactString(item) : item;
    }, 2) ?? "null";
  } catch {
    return "[Unserializable debug value]";
  }
}

function safeDebugValue(value: unknown): unknown {
  const serialized = safeDebugJson(value);
  try {
    return JSON.parse(serialized) as unknown;
  } catch {
    return serialized;
  }
}

function formatAssistantObservedAt(value: string) {
  const timestamp = new Date(value);
  if (Number.isNaN(timestamp.getTime())) return value;
  return timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function assistantHistoryOptionLabel(conversation: AssistantConversationSummary) {
  const timestamp = new Date(conversation.updatedAt);
  if (Number.isNaN(timestamp.getTime())) return conversation.title;
  const updated = timestamp.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
  return `${conversation.title} · ${updated}`;
}

function VerticalResizeHandle({
  paneRef,
  width,
  minWidth,
  defaultWidth,
  getMaxWidth,
  onResize,
}: {
  paneRef: RefObject<HTMLElement | null>;
  width: number;
  minWidth: number;
  defaultWidth: number;
  getMaxWidth: () => number;
  onResize: (width: number) => void;
}) {
  const [dragging, setDragging] = useState(false);

  function clampWidth(nextWidth: number) {
    return Math.min(getMaxWidth(), Math.max(minWidth, nextWidth));
  }

  function beginResize(event: ReactPointerEvent<HTMLDivElement>) {
    if (event.button !== 0) return;
    event.preventDefault();
    const startX = event.clientX;
    const startWidth = paneRef.current?.getBoundingClientRect().width ?? width;
    const previousCursor = document.body.style.cursor;
    const previousUserSelect = document.body.style.userSelect;
    setDragging(true);
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";

    function move(moveEvent: PointerEvent) {
      onResize(clampWidth(startWidth + startX - moveEvent.clientX));
    }

    function finish() {
      setDragging(false);
      document.body.style.cursor = previousCursor;
      document.body.style.userSelect = previousUserSelect;
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", finish);
      window.removeEventListener("pointercancel", finish);
    }

    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", finish);
    window.addEventListener("pointercancel", finish);
  }

  function resizeWithKeyboard(event: KeyboardEvent<HTMLDivElement>) {
    const step = event.shiftKey ? 64 : 24;
    let nextWidth: number | undefined;
    if (event.key === "ArrowLeft") nextWidth = width + step;
    if (event.key === "ArrowRight") nextWidth = width - step;
    if (event.key === "Home") nextWidth = minWidth;
    if (event.key === "End") nextWidth = getMaxWidth();
    if (nextWidth === undefined) return;
    event.preventDefault();
    onResize(clampWidth(nextWidth));
  }

  return (
    <div
      role="separator"
      aria-label="Resize map and control pane"
      aria-orientation="vertical"
      aria-valuemin={Math.round(minWidth)}
      aria-valuemax={Math.round(getMaxWidth())}
      aria-valuenow={Math.round(width)}
      tabIndex={0}
      className={`group relative z-[500] flex w-2 shrink-0 touch-none cursor-col-resize items-center justify-center border-x border-border outline-none transition-colors hover:bg-primary/10 focus:bg-primary/10 focus:ring-2 focus:ring-inset focus:ring-ring ${dragging ? "bg-primary/15" : "bg-background"}`}
      title="Drag to resize. Double-click to reset."
      onPointerDown={beginResize}
      onKeyDown={resizeWithKeyboard}
      onDoubleClick={() => onResize(clampWidth(defaultWidth))}
    >
      <span className={`flex h-12 w-3 items-center justify-center rounded-full border shadow-sm transition-colors ${dragging ? "border-primary bg-primary text-primary-foreground" : "border-border bg-panel text-muted-foreground group-hover:border-primary group-hover:text-primary"}`}>
        <GripVertical className="h-3.5 w-3.5" />
      </span>
    </div>
  );
}

type RuntimeTone = "default" | "ok" | "warn" | "error";

type RuntimeSignal = {
  label: string;
  value: string;
  detail: string;
  tone: RuntimeTone;
  icon: ReactNode;
};

function MissionRuntimeStatus({
  mission,
  missionState,
  plannerState,
  agentTelemetry,
  busyCommand,
  initRequestedAt,
}: {
  mission?: MissionConfig;
  missionState?: MissionState;
  plannerState?: PlannerUpdateEvent;
  agentTelemetry: Record<string, AgentUpdateEvent>;
  busyCommand?: "init" | "approve" | "start";
  initRequestedAt?: number;
}) {
  const missionSignal = missionRuntimeSignal(missionState, busyCommand);
  const plannerSignal = plannerRuntimeSignal(mission?.mission_id ?? missionState?.mission_id, missionState, plannerState);
  const routeSignal = routeRuntimeSignal(mission?.mission_id ?? missionState?.mission_id, missionState, plannerState);
  const executionSignal = executionRuntimeSignal(mission, missionState, agentTelemetry);
  const signals = [missionSignal, plannerSignal, routeSignal, executionSignal];
  const startedAt = missionState?.initialized_at ? Date.parse(missionState.initialized_at) : initRequestedAt;
  const status = missionState ? missionStatusLabel(missionState) : "DRAFT";
  const isTerminal = ["COMPLETED", "FAILED", "PLANNED_FAILED", "STOPPED", "DELETED"].includes(status);
  const issue = missionIssueSnapshot(missionState);
  const headline = missionRuntimeHeadline(status, routeSignal.value, busyCommand);

  return (
    <div className="rounded-md border border-border bg-panel p-2">
      <div className="flex min-w-0 items-center gap-2">
        <ListChecks className="h-4 w-4 shrink-0 text-primary" />
        <span className="shrink-0 text-xs font-semibold">Runtime</span>
        <span className="min-w-0 flex-1 truncate text-[11px] text-muted-foreground" title={headline}>{headline}</span>
        {startedAt && !isTerminal && <ElapsedClock startedAt={startedAt} />}
      </div>
      <div className="mt-2 grid grid-cols-4 gap-1.5">
        {signals.map((signal) => <RuntimeSignalChip key={signal.label} signal={signal} />)}
      </div>
      {issue && (
        <div className={`mt-1.5 flex items-start gap-2 rounded-md border px-2 py-1.5 text-[11px] ${issue.tone === "error" ? "border-red-200 bg-red-50 text-red-900" : "border-amber-200 bg-amber-50 text-amber-950"}`}>
          <XCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <div className="min-w-0"><span className="font-medium">{issue.label}:</span> {issue.detail}</div>
        </div>
      )}
    </div>
  );
}

function RuntimeSignalChip({ signal }: { signal: RuntimeSignal }) {
  return (
    <div className="flex min-w-0 flex-col gap-1 rounded-md border border-border bg-background px-1.5 py-1" title={`${signal.label}: ${signal.value}. ${signal.detail}`}>
      <div className="flex min-w-0 items-center justify-center gap-1 text-muted-foreground">
        <span className="shrink-0">{signal.icon}</span>
        <span className="truncate text-[10px] font-medium">{signal.label}</span>
      </div>
      <Badge tone={signal.tone} className="w-full justify-center truncate whitespace-nowrap px-1">{signal.value}</Badge>
    </div>
  );
}

function missionRuntimeSignal(state?: MissionState, busyCommand?: "init" | "approve" | "start"): RuntimeSignal {
  if (!state) {
    return {
      label: "Mission",
      value: busyCommand === "init" ? "Submitting" : "Draft",
      detail: busyCommand === "init" ? "Sending INIT through the adapter and legacy REST bridge." : "The mission exists only in the UI and has not been initialized.",
      tone: busyCommand === "init" ? "warn" : "default",
      icon: <ShieldCheck className="h-3.5 w-3.5" />,
    };
  }
  const status = missionStatusLabel(state);
  const confirmed = state.status_source === "mission_feedback" || Boolean(state.feedback);
  const detail = confirmed
    ? "Confirmed by legacy mission feedback."
    : state.status_source === "adapter_acknowledgement"
      ? "Command acknowledged by the adapter; mission feedback may still follow."
      : "Reported by the adapter mission runtime.";
  const tone: RuntimeTone = ["PLANNED_FAILED", "FAILED"].includes(status)
    ? "error"
    : ["NONE", "PAUSED", "PLANNED_ALTERNATIVE"].includes(status)
      ? "warn"
      : ["PLANNED", "ACCEPTED", "STARTED", "COMPLETED"].includes(status)
        ? "ok"
        : "default";
  return { label: "Mission", value: humanizeEnum(status), detail, tone, icon: <ShieldCheck className="h-3.5 w-3.5" /> };
}

function plannerRuntimeSignal(missionId: string | undefined, state?: MissionState, plannerState?: PlannerUpdateEvent): RuntimeSignal {
  const plannerId = plannerRuntimeStateId(missionId, state, plannerState);
  const values: Record<number, Omit<RuntimeSignal, "label" | "icon">> = {
    0: { value: "Initialized", detail: "Planner instance exists and is idle.", tone: "default" },
    1: { value: "Calculating", detail: "The planner is computing a plan.", tone: "warn" },
    2: { value: "Ready", detail: "Planner cache is ready; route receipt is verified separately.", tone: "ok" },
    3: { value: "Disconnected", detail: "Mission manager reports that the planner is disconnected.", tone: "error" },
    4: { value: "Failed", detail: "The planner reported a planning failure.", tone: "error" },
  };
  const fallback = state?.planner_status;
  const snapshot = plannerId !== undefined
    ? values[plannerId] ?? { value: `Unknown (${plannerId})`, detail: "Unrecognized planner state value.", tone: "warn" as const }
    : fallback === "failed"
      ? { value: "Failed", detail: "Failure was inferred from mission feedback; no raw planner state is available.", tone: "error" as const }
      : fallback === "planning"
        ? { value: "Calculating", detail: "Planning is in progress; no raw planner state is available.", tone: "warn" as const }
        : { value: "Not observed", detail: "No planner instance state has been received for this mission.", tone: "default" as const };
  return { label: "Planner", icon: <Workflow className="h-3.5 w-3.5" />, ...snapshot };
}

function routeRuntimeSignal(missionId: string | undefined, state?: MissionState, plannerState?: PlannerUpdateEvent): RuntimeSignal {
  const summary = missionPathSummary(missionId, state, plannerState);
  if (summary) {
    return {
      label: "Route",
      value: `${summary.pathCount} path${summary.pathCount === 1 ? "" : "s"} · ${summary.waypointCount} wp`,
      detail: "Non-empty waypoint tasks were received and can be rendered on the map.",
      tone: "ok",
      icon: <Route className="h-3.5 w-3.5" />,
    };
  }
  const status = state ? missionStatusLabel(state) : "DRAFT";
  if (state?.path_status === "missing" || ["PLANNED", "PLANNED_ALTERNATIVE"].includes(status)) {
    return { label: "Route", value: "Missing", detail: "Mission says planned, but mission feedback contains no waypoint tasks.", tone: "error", icon: <Route className="h-3.5 w-3.5" /> };
  }
  if (plannerRuntimeStateId(missionId, state, plannerState) === 2) {
    return { label: "Route", value: "Awaiting feedback", detail: "Planner is ready, but no waypoint path has reached mission feedback yet.", tone: "warn", icon: <Route className="h-3.5 w-3.5" /> };
  }
  return {
    label: "Route",
    value: state ? "Pending" : "Not requested",
    detail: state ? "Waiting for a non-empty planned path." : "Initialize the mission to request planning.",
    tone: state ? "warn" : "default",
    icon: <Route className="h-3.5 w-3.5" />,
  };
}

function executionRuntimeSignal(mission: MissionConfig | undefined, state: MissionState | undefined, telemetry: Record<string, AgentUpdateEvent>): RuntimeSignal {
  const missionStatus = state ? missionStatusLabel(state) : "DRAFT";
  const agentUpdates = (mission?.vehicles ?? []).map((agentId) => telemetry[normalizeUuidish(agentId)]).filter((update): update is AgentUpdateEvent => Boolean(update));
  const tasks = agentUpdates.flatMap((update) => update.tasks ?? []);
  const taskStates = tasks.map((task) => taskStateId(task.task_state)).filter((value): value is number => value !== undefined);
  const completed = taskStates.filter((value) => value === 3).length;
  const detailSuffix = tasks.length ? `${completed}/${tasks.length} task${tasks.length === 1 ? "" : "s"} completed.` : `${agentUpdates.length}/${mission?.vehicles.length ?? 0} vehicle feedback streams observed.`;
  if (missionStatus === "COMPLETED" || (taskStates.length > 0 && completed === taskStates.length)) {
    return { label: "Execution", value: "Completed", detail: detailSuffix, tone: "ok", icon: <Play className="h-3.5 w-3.5" /> };
  }
  if (taskStates.includes(4)) return { label: "Execution", value: "Aborted", detail: detailSuffix, tone: "error", icon: <Play className="h-3.5 w-3.5" /> };
  if (taskStates.includes(1)) return { label: "Execution", value: "Executing", detail: detailSuffix, tone: "ok", icon: <Play className="h-3.5 w-3.5" /> };
  if (taskStates.includes(2)) return { label: "Execution", value: "Paused", detail: detailSuffix, tone: "warn", icon: <Play className="h-3.5 w-3.5" /> };
  if (taskStates.length > 0 && taskStates.every((value) => value === 0)) return { label: "Execution", value: "Staged", detail: "Tasks are dispatched in STOPPED state and await START.", tone: "ok", icon: <Play className="h-3.5 w-3.5" /> };
  if (taskStates.length > 0 && taskStates.every((value) => value === 5)) return { label: "Execution", value: "Deleted", detail: detailSuffix, tone: "default", icon: <Play className="h-3.5 w-3.5" /> };
  if (missionStatus === "STARTED") return { label: "Execution", value: "Awaiting tasks", detail: "START was acknowledged, but edge task feedback has not reported an executing task.", tone: "warn", icon: <Play className="h-3.5 w-3.5" /> };
  if (missionStatus === "ACCEPTED") return { label: "Execution", value: "Ready to start", detail: "Mission is approved; dispatched task feedback has not been observed yet.", tone: "ok", icon: <Play className="h-3.5 w-3.5" /> };
  return { label: "Execution", value: "Not started", detail: "Execution begins only after the mission is approved and START is requested.", tone: "default", icon: <Play className="h-3.5 w-3.5" /> };
}

function plannerRuntimeStateId(missionId: string | undefined, state?: MissionState, plannerState?: PlannerUpdateEvent) {
  const direct = numericEnumValue(state?.planner_state);
  if (direct !== undefined) return direct;
  if (!plannerState?.state || typeof plannerState.state !== "object") return undefined;
  const planners = (plannerState.state as { planners?: unknown }).planners;
  if (!Array.isArray(planners)) return undefined;
  const planner = planners.find((item) => {
    if (!item || typeof item !== "object") return false;
    const candidateId = (item as { mission_id?: unknown }).mission_id;
    return typeof candidateId === "string" && (!missionId || normalizeUuidish(candidateId) === normalizeUuidish(missionId));
  });
  return planner && typeof planner === "object" ? numericEnumValue((planner as { state?: unknown }).state) : undefined;
}

function missionPathSummary(missionId: string | undefined, state?: MissionState, plannerState?: PlannerUpdateEvent) {
  const statePaths = state?.planned_paths;
  const plannerMatches = !plannerState?.mission_id || !missionId || normalizeUuidish(plannerState.mission_id) === normalizeUuidish(missionId);
  const paths = hasPlannedPaths(statePaths) ? statePaths : plannerMatches ? plannerState?.paths : undefined;
  if (!paths) return undefined;
  const usablePaths = Object.values(paths).filter((path) => Array.isArray(path) && path.length > 0);
  if (!usablePaths.length) return undefined;
  return { pathCount: usablePaths.length, waypointCount: usablePaths.reduce((sum, path) => sum + path.length, 0) };
}

function numericEnumValue(value: unknown) {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim() && Number.isFinite(Number(value))) return Number(value);
  return undefined;
}

function taskStateId(value: unknown) {
  const state = numericEnumValue(value);
  return state !== undefined && state >= 0 && state <= 5 ? state : undefined;
}

function humanizeEnum(value: string) {
  return value.toLowerCase().split("_").map((word) => word ? word[0].toUpperCase() + word.slice(1) : word).join(" ");
}

function missionRuntimeHeadline(status: string, routeStatus: string, busyCommand?: "init" | "approve" | "start") {
  if (busyCommand === "init") return "Submitting the mission to the planning chain.";
  if (busyCommand === "approve") return "Requesting approval of the planned mission.";
  if (busyCommand === "start") return "Requesting task execution.";
  if (["PLANNED_FAILED", "FAILED"].includes(status)) return "The mission requires attention. Open Diagnostics for raw ROS evidence.";
  if (status === "COMPLETED") return "Mission and task execution completed.";
  if (status === "STARTED") return "Mission execution is in progress.";
  if (status === "ACCEPTED") return "The mission is approved and ready to start.";
  if (["PLANNED", "PLANNED_ALTERNATIVE"].includes(status) && routeStatus === "Missing") return "Planning status and route evidence disagree.";
  if (["PLANNED", "PLANNED_ALTERNATIVE"].includes(status)) return "A plan is available for review and approval.";
  if (status === "NONE") return "Initialization was acknowledged; waiting for planning feedback.";
  return "Draft mission has not entered the runtime lifecycle.";
}

const missionIssueDetails: Record<number, { label: string; detail: string }> = {
  10: { label: "Mission ID reused", detail: "The existing mission configuration was overwritten." },
  11: { label: "Vehicle unavailable", detail: "Planning continued with a reduced vehicle set." },
  12: { label: "Unknown configuration data", detail: "Unknown mission keys were ignored." },
  13: { label: "Status unchanged", detail: "The requested mission transition was invalid and ignored." },
  14: { label: "Planner disconnected", detail: "The planner could not be reached; mission status did not change." },
  15: { label: "Edge disconnected", detail: "At least one edge module could not be reached." },
  16: { label: "Autonomy disconnected", detail: "At least one autonomy module could not be reached." },
  20: { label: "Configuration parse failed", detail: "The mission configuration could not be parsed." },
  21: { label: "Configuration incomplete", detail: "The mission lacks data required for planning." },
  22: { label: "Mission compromised", detail: "The mission cannot continue." },
  23: { label: "Planner connection failure", detail: "Planner disconnection caused mission failure." },
  24: { label: "Edge connection failure", detail: "Edge disconnection caused mission failure." },
  25: { label: "Autonomy connection failure", detail: "Autonomy disconnection caused mission failure." },
  30: { label: "Vehicle mismatch", detail: "The requested vehicle set could not fully satisfy the mission." },
  31: { label: "Coverage reduced", detail: "The plan could not provide the requested coverage." },
  32: { label: "Schedule compromised", detail: "Requested mission dates could not be fully satisfied." },
  40: { label: "No planning solution", detail: "No usable solution was found; adjust the mission and initialize again." },
  41: { label: "Planning failed", detail: "The planner process failed." },
};

function missionIssueSnapshot(state?: MissionState) {
  const issue = numericEnumValue(state?.issue ?? state?.feedback?.issue ?? state?.feedback?.Issue);
  if (issue === undefined || issue === 0) return undefined;
  const details = missionIssueDetails[issue] ?? { label: state?.issue_name ? humanizeEnum(state.issue_name) : `Mission issue ${issue}`, detail: "The runtime reported an unrecognized mission issue code." };
  return { ...details, tone: issue >= 20 && issue < 30 || issue >= 40 ? "error" as const : "warn" as const };
}

function hasPlannedPaths(paths?: Record<string, [number, number][]>) {
  return Boolean(paths && Object.values(paths).some((path) => Array.isArray(path) && path.length > 0));
}

function shouldPollMissionState(state?: MissionState) {
  if (!state) return true;
  const status = missionStatusLabel(state);
  return status === "NONE" || state.planner_status === "waiting_for_feedback" || state.path_status === "missing";
}

function formatDuration(totalSeconds: number) {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes === 0) return `${seconds}s`;
  return `${minutes}m ${seconds.toString().padStart(2, "0")}s`;
}

function MissionPanel({
  examples,
  mission,
  missionText,
  missionState,
  missionList,
  taskPlan,
  showNewMission,
  validation,
  onLoadExample,
  onSelectMission,
  onForgetMission,
  onMissionTextChange,
  missionJsonRef,
  jsonFocusLabel,
  onClear,
}: {
  examples: MissionExample[];
  mission?: MissionConfig;
  missionText: string;
  missionState?: MissionState;
  missionList: MissionListItem[];
  taskPlan?: ReturnType<typeof createTaskPlan>;
  showNewMission: boolean;
  validation: string[];
  onLoadExample: (example: MissionExample) => void;
  onSelectMission: (missionId: string) => void;
  onForgetMission: (missionId: string) => void;
  onMissionTextChange: (value: string) => void;
  missionJsonRef: RefObject<HTMLTextAreaElement>;
  jsonFocusLabel?: string;
  onClear: () => void;
}) {
  if (showNewMission) {
    return (
      <div className="space-y-4">
        {!missionText.trim() && (
          <div className="space-y-3">
            <div className="rounded-md border border-border bg-panel p-4 text-sm text-muted-foreground">
              Choose an example, draw/select an objective on the map, or select an asset and use the toolbar action to generate the mission.
            </div>
            <div className="space-y-2 rounded-md border border-border bg-panel p-3">
              <SectionTitle icon={<Plus className="h-4 w-4" />} label="Create From Example" />
              {examples.map((example) => (
                <button key={example.id} className="w-full rounded-md border border-border bg-background p-3 text-left hover:bg-muted" onClick={() => onLoadExample(example)}>
                  <div className="flex items-center justify-between">
                    <div className="font-medium">{example.name}</div>
                    <Badge>{example.behavior === 1 ? "coverage" : "navigate"}</Badge>
                  </div>
                  <div className="mt-1 flex flex-wrap gap-1 text-xs text-muted-foreground">
                    <span>{example.config.vehicles.length} vehicle{example.config.vehicles.length === 1 ? "" : "s"}</span>
                    {normalizeCapabilityTags(example.config.required_capabilities).map((capability) => (
                      <Badge key={capability}>{capability}</Badge>
                    ))}
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {missionText.trim() ? (
          <MissionEditor
            mission={mission}
            missionText={missionText}
            missionState={missionState}
            taskPlan={taskPlan}
            validation={validation}
            jsonFocusLabel={jsonFocusLabel}
            missionJsonRef={missionJsonRef}
            onMissionTextChange={onMissionTextChange}
            onClear={onClear}
          />
        ) : null}
      </div>
    );
  }

  if (missionText.trim() || missionState) {
    return (
      <div className="space-y-4">
        {missionText.trim() ? (
          <MissionEditor
            mission={mission}
            missionText={missionText}
            missionState={missionState}
            taskPlan={taskPlan}
            validation={validation}
            jsonFocusLabel={jsonFocusLabel}
            missionJsonRef={missionJsonRef}
            onMissionTextChange={onMissionTextChange}
            onClear={onClear}
          />
        ) : missionState ? (
          <RuntimeMissionDetails state={missionState} />
        ) : null}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {missionList.length > 0 ? (
        <div className="space-y-2">
          {missionList.map((item) => (
            <div
              key={item.mission_id}
              role="button"
              tabIndex={0}
              className={`w-full rounded-md border bg-panel p-3 text-left outline-none hover:bg-muted focus:ring-2 focus:ring-ring ${isActiveMission(item, mission, missionState) ? "border-primary shadow-sm" : "border-border"}`}
              onClick={() => onSelectMission(item.mission_id)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") onSelectMission(item.mission_id);
              }}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="truncate text-sm font-semibold">{missionCardTitle(item)}</div>
                  <div className="mt-1 break-all font-mono text-xs text-muted-foreground">{missionCardSubtitle(item)}</div>
                  <div className="mt-2 flex flex-wrap gap-1">
                    <Badge>{behaviorLabel(item.config?.behavior)}</Badge>
                    <Badge>{vehicleCountLabel(item.config)}</Badge>
                    <Badge>{objectiveSummary(item.config)}</Badge>
                    <span title={item.binding?.world_id ?? undefined}>
                      <Badge>world {shortId(item.binding?.world_id ?? "")}</Badge>
                    </span>
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <Badge tone={missionStateTone(item.state)}>{item.state ? missionStatusLabel(item.state) : "draft"}</Badge>
                  <Button
                    size="icon"
                    variant="ghost"
                    onClick={(event) => {
                      event.stopPropagation();
                      onForgetMission(item.mission_id);
                    }}
                    title="Remove from UI list"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="rounded-md border border-border bg-panel p-4 text-sm text-muted-foreground">No missions yet. Create one from an example or by selecting an objective point on the map.</div>
      )}

    </div>
  );
}

function PaneNavigation({
  title,
  icon,
  backLabel,
  onBack,
  actions,
}: {
  title: string;
  icon?: ReactNode;
  backLabel?: string;
  onBack?: () => void;
  actions?: ReactNode;
}) {
  return (
    <nav className="flex min-h-12 shrink-0 items-center justify-between gap-3 border-b border-border bg-background px-4 py-2" aria-label="Pane navigation">
      <div className="flex min-w-0 items-center gap-2">
        {onBack ? (
          <Button size="sm" variant="ghost" onClick={onBack} title={`Back to ${backLabel ?? "previous pane"}`}>
            <ArrowLeft className="h-4 w-4" />
            {backLabel ?? "Back"}
          </Button>
        ) : (
          <>
            {icon}
            <span className="truncate text-sm font-semibold">{title}</span>
          </>
        )}
        {onBack && <span className="truncate text-xs font-medium text-muted-foreground">{title}</span>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </nav>
  );
}

function MissionEditor({
  mission,
  missionText,
  missionState,
  taskPlan,
  validation,
  jsonFocusLabel,
  missionJsonRef,
  onMissionTextChange,
  onClear,
}: {
  mission?: MissionConfig;
  missionText: string;
  missionState?: MissionState;
  taskPlan?: ReturnType<typeof createTaskPlan>;
  validation: string[];
  jsonFocusLabel?: string;
  missionJsonRef: RefObject<HTMLTextAreaElement>;
  onMissionTextChange: (value: string) => void;
  onClear: () => void;
}) {
  const [cursor, setCursor] = useState({ line: 1, column: 1 });
  const canFormatJson = useMemo(() => {
    try {
      JSON.parse(missionText);
      return true;
    } catch {
      return false;
    }
  }, [missionText]);

  function formatJson() {
    if (!canFormatJson) return;
    onMissionTextChange(JSON.stringify(JSON.parse(missionText), null, 2));
  }

  function handleJsonKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.metaKey || event.ctrlKey || event.altKey) return;
    const edit = editJsonForKey(missionText, event.currentTarget.selectionStart, event.currentTarget.selectionEnd, event.key, event.shiftKey);
    if (!edit) return;
    event.preventDefault();
    const textarea = event.currentTarget;
    onMissionTextChange(edit.value);
    setCursor(jsonCursorPosition(edit.value, edit.selectionStart));
    window.requestAnimationFrame(() => {
      textarea.focus();
      textarea.setSelectionRange(edit.selectionStart, edit.selectionEnd);
    });
  }

  function updateCursor(textarea: HTMLTextAreaElement) {
    setCursor(jsonCursorPosition(missionText, textarea.selectionStart));
  }

  return (
    <div className="space-y-3">
      {mission && <MissionSummaryCard mission={mission} state={missionState} />}
      {taskPlan && <TaskProjectionDisclosure taskPlan={taskPlan} />}
      <div className="space-y-2">
        <div className="flex items-center justify-between gap-3">
          <SectionTitle icon={<FileJson className="h-4 w-4" />} label="Full Mission JSON" />
          {jsonFocusLabel && <Badge tone="ok">updated {jsonFocusLabel}</Badge>}
        </div>
        <Textarea
          ref={missionJsonRef}
          className="h-[360px] resize-none rounded-b-none font-mono text-xs transition-shadow"
          value={missionText}
          onChange={(event) => onMissionTextChange(event.target.value)}
          onKeyDown={handleJsonKeyDown}
          onClick={(event) => updateCursor(event.currentTarget)}
          onKeyUp={(event) => updateCursor(event.currentTarget)}
          onSelect={(event) => updateCursor(event.currentTarget)}
          aria-invalid={validation.length > 0}
          wrap="off"
          spellCheck={false}
        />
        <div className="flex items-center justify-between rounded-b-md border border-t-0 border-border bg-panel px-2 py-1 font-mono text-[10px] text-muted-foreground">
          <span>JSON · Spaces: 2</span>
          <span>Ln {cursor.line}, Col {cursor.column}</span>
        </div>
      </div>
      <div className="flex justify-end gap-2">
        <Button size="sm" variant="outline" onClick={formatJson} disabled={!canFormatJson}>
          Format JSON
        </Button>
        <Button size="sm" variant="ghost" onClick={onClear}>
          Clear Mission
        </Button>
      </div>
      <ValidationList errors={validation} />
    </div>
  );
}

function TaskProjectionDisclosure({ taskPlan }: { taskPlan: ReturnType<typeof createTaskPlan> }) {
  return (
    <details className="rounded-md border border-border bg-panel">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-2 px-3 py-2 text-xs font-medium outline-none focus-visible:ring-2 focus-visible:ring-ring">
        <span className="flex items-center gap-2"><Route className="h-4 w-4 text-primary" />Browser task preview</span>
        <Badge>{Object.keys(taskPlan.tasks).length} task{Object.keys(taskPlan.tasks).length === 1 ? "" : "s"}</Badge>
      </summary>
      <div className="space-y-2 border-t border-border p-3">
        <p className="text-xs leading-5 text-muted-foreground">
          This is generated locally from the mission definition by the UI. It is not the backend planner route; actual planner output appears in runtime status and diagnostics after Init.
        </p>
        <div className="grid grid-cols-2 gap-2">
          <InfoTile label="Mission ID" value={taskPlan.mission_id} />
          <InfoTile label="Objectives" value={Object.values(taskPlan.tasks).reduce((sum, task) => sum + task.objectives.length, 0).toString()} />
        </div>
        <JsonExplorer value={taskPlan} maxHeightClassName="max-h-80" />
      </div>
    </details>
  );
}

function ValidationList({ errors }: { errors: string[] }) {
  if (errors.length === 0) return null;
  return (
    <div className="space-y-2">
      {errors.map((error) => (
        <div key={error} className="flex items-start gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
          <XCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      ))}
    </div>
  );
}

function AssetsPanel({
  agents,
  mapFeatures,
  mission,
  selectedFeatureId,
  onSetObjective,
  onRemoveFeature,
}: {
  agents: Agent[];
  mapFeatures: MapFeature[];
  mission?: MissionConfig;
  selectedFeatureId?: string;
  onSetObjective: (feature: MapFeature) => void;
  onRemoveFeature: (feature: MapFeature) => void;
}) {
  return (
    <div className="space-y-5">
      <SectionTitle icon={<Settings2 className="h-4 w-4" />} label="Vehicles" />
      <div className="space-y-2">
        {agents.map((agent) => (
          <div key={agent.agent_id} className="rounded-md border border-border bg-panel p-3">
            <div className="flex items-center justify-between">
              <div className="font-medium">{agent.name || agent.agent_id}</div>
              <Badge tone={mission?.vehicles.includes(agent.agent_id) ? "ok" : "default"}>{agent.status}</Badge>
            </div>
            <div className="mt-1 text-xs text-muted-foreground">{agent.agent_id} · max {agent.constraints.max_speed ?? "?"} m/s</div>
          </div>
        ))}
      </div>
      <SectionTitle icon={<MapPinned className="h-4 w-4" />} label="Map Features" />
      <div className="space-y-2">
        {mapFeatures.map((feature) => (
          <div key={feature.feature_id} className={`rounded-md border bg-panel p-3 ${selectedFeatureId === feature.feature_id ? "border-primary shadow-sm" : "border-border"}`}>
            <div className="flex items-center justify-between">
              <div className="min-w-0">
                <div className="truncate font-medium">{feature.name}</div>
                <div className="mt-1 text-xs text-muted-foreground">{feature.feature_id}</div>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <Badge>{feature.feature_type}</Badge>
                <Button size="sm" variant="outline" disabled={feature.feature_type !== "objective" || feature.geometry.type !== "Point"} onClick={() => onSetObjective(feature)} title={feature.feature_type === "objective" && feature.geometry.type === "Point" ? "Use this objective point as the mission objective" : "Only objective Point assets can be used for simple navigation"}>
                  <Target className="h-4 w-4" />
                  Set objective
                </Button>
                <Button size="icon" variant="ghost" disabled={feature.properties?.source !== "live_overlay"} onClick={() => onRemoveFeature(feature)} title={feature.properties?.source === "live_overlay" ? "Remove deployment overlay" : "Immutable snapshot assets are read-only"}>
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function MissionSummaryCard({ mission, state }: { mission: MissionConfig; state?: MissionState }) {
  const objective = mission.objective.geometries[0];
  const constraints = mission.transit?.["desired_vehicle_constraints"] as Record<string, unknown> | undefined;
  const optimization = (mission.transit?.["optimization"] ?? mission.transit?.["optimalization"]) as Record<string, unknown> | undefined;
  return (
    <div className="rounded-md border border-border bg-panel p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold">{mission.name ?? shortId(mission.mission_id)}</div>
          <div className="mt-1 break-all font-mono text-xs text-muted-foreground">Mission ID: {mission.mission_id}</div>
        </div>
        <Badge tone={missionStateTone(state)}>{state ? missionStatusLabel(state) : "draft"}</Badge>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
        <InfoTile label="Behavior" value={behaviorLabel(mission.behavior)} />
        <InfoTile label="Phase" value={String(mission.phase ?? 1)} />
        <InfoTile label="Vehicles" value={mission.vehicles.length ? `${mission.vehicles.length}: ${mission.vehicles.map(shortId).join(", ")}` : "none"} />
        <InfoTile label="Objective" value={objectiveDetails(objective)} />
        <InfoTile label="Road usage" value={formatPercent(optimization?.road_usage)} />
        <InfoTile label="Max speed" value={constraints?.max_speed ? `${constraints.max_speed} m/s` : "default"} />
      </div>
    </div>
  );
}

function RuntimeMissionDetails({ state }: { state: MissionState }) {
  return (
    <div className="space-y-3">
      <div className="rounded-md border border-border bg-panel p-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="text-sm font-semibold">Legacy Runtime Mission</div>
            <div className="mt-1 break-all font-mono text-xs text-muted-foreground">Mission ID: {state.mission_id}</div>
          </div>
          <Badge tone={missionStateTone(state)}>{missionStatusLabel(state)}</Badge>
        </div>
        <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
          <InfoTile label="Command" value={state.command_phase ?? "unknown"} />
          <InfoTile label="Planner" value={state.planner_status ?? "unknown"} />
          <InfoTile label="Requested" value={state.requested_status_name ?? (state.requested_status !== undefined ? String(state.requested_status) : "none")} />
          <InfoTile label="Updated" value={formatTime(state.updated_at ?? state.initialized_at)} />
        </div>
      </div>
      <div className="rounded-md border border-border bg-panel p-3">
        <SectionTitle icon={<FileJson className="h-4 w-4" />} label="Runtime Details" />
        <Textarea className="mt-2 h-56 resize-none" value={JSON.stringify(state, null, 2)} readOnly spellCheck={false} />
      </div>
    </div>
  );
}

function InfoTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-sm border border-border bg-background p-2">
      <div className="text-muted-foreground">{label}</div>
      <div className="mt-1 break-words font-medium">{value}</div>
    </div>
  );
}

function DiagnosticsPanel({
  diagnostics,
  legacyTrace,
  plannerState,
  planningDiagnostics,
  planningDiagnosticsBusy,
  selectedPlanningVariantId,
  legacyResetBusy,
  legacyResetResult,
  onRefreshLegacyTrace,
  onRefreshPlanningDiagnostics,
  onSelectPlanningVariant,
  onCleanLegacyRuntime,
}: {
  diagnostics?: DiagnosticsState;
  legacyTrace?: LegacyTrace;
  plannerState?: PlannerUpdateEvent;
  planningDiagnostics?: PlanningDiagnostics;
  planningDiagnosticsBusy: boolean;
  selectedPlanningVariantId?: string;
  legacyResetBusy: boolean;
  legacyResetResult?: LegacyResetResult;
  onRefreshLegacyTrace: () => void;
  onRefreshPlanningDiagnostics: () => void;
  onSelectPlanningVariant: (worldId: string) => void;
  onCleanLegacyRuntime: () => void;
}) {
  if (!diagnostics) return <div className="text-sm text-muted-foreground">Waiting for diagnostics...</div>;
  return (
    <div className="space-y-3">
      <div className="flex justify-end gap-2">
        <Button size="sm" variant="outline" onClick={onRefreshPlanningDiagnostics} disabled={planningDiagnosticsBusy} title="Compare planning variants and backend mission output">
          <Route className="h-4 w-4" />
          {planningDiagnosticsBusy ? "Checking" : "World Debug"}
        </Button>
        <Button size="sm" variant="outline" onClick={onCleanLegacyRuntime} disabled={legacyResetBusy} title="Test-only: clear old mission configs, plans, feedback, and logs from MongoDB">
          <Trash2 className="h-4 w-4" />
          {legacyResetBusy ? "Cleaning" : "Clean Test DB"}
        </Button>
        <Button size="sm" variant="outline" onClick={onRefreshLegacyTrace}>
          <Bug className="h-4 w-4" />
          Legacy Trace
        </Button>
      </div>
      {legacyResetResult && (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-950">
          <div className="font-medium">{legacyResetResult.message}</div>
          <div className="mt-1 text-amber-900">Preserved: {legacyResetResult.preserved.join(", ")}</div>
          <Textarea className="mt-2 h-24 resize-none bg-background" value={JSON.stringify({ deleted: legacyResetResult.deleted, restart_required: legacyResetResult.restart_required }, null, 2)} readOnly />
        </div>
      )}
      {planningDiagnostics && (
        <div className="space-y-2 rounded-md border border-border bg-panel p-3">
          <div className="flex items-center justify-between gap-3">
            <div className="font-medium">Planning Diagnostic</div>
            <Badge tone={planningDiagnostics.checks.every((check) => check.status === "ok") ? "ok" : "warn"}>{planningDiagnostics.mission_id ? shortId(planningDiagnostics.mission_id) : "none"}</Badge>
          </div>
          {planningDiagnostics.interpretation?.map((note) => (
            <div key={note} className="rounded-sm border border-border bg-background px-2 py-1 text-xs text-muted-foreground">
              {note}
            </div>
          ))}
          <div className="grid grid-cols-2 gap-2">
            {planningDiagnostics.checks.map((check) => (
              <div key={check.id} className="flex items-center justify-between gap-2 rounded-sm border border-border bg-background px-2 py-1 text-xs">
                <span className="truncate">{check.id}</span>
                <Badge tone={check.status === "ok" ? "ok" : "error"}>{check.status}</Badge>
              </div>
            ))}
          </div>
          <PlanningVariantMatrix analysis={planningDiagnostics.variant_analysis} selectedVariantId={selectedPlanningVariantId} onSelectVariant={onSelectPlanningVariant} />
          <Textarea className="h-64 resize-none" value={JSON.stringify(planningDiagnostics, null, 2)} readOnly spellCheck={false} />
        </div>
      )}
      {legacyTrace && (
        <div className="space-y-2 rounded-md border border-border bg-panel p-3">
          <div className="flex items-center justify-between">
            <div className="font-medium">Legacy Backend Chain</div>
            <Button size="sm" variant="ghost" onClick={onRefreshLegacyTrace}>
              <RefreshCw className="h-4 w-4" />
              Refresh
            </Button>
          </div>
          {legacyTrace.steps.map((step) => (
            <div key={step.id} className="flex items-center justify-between gap-3 rounded-sm border border-border px-2 py-1 text-xs">
              <span>{step.id}</span>
              <Badge tone={step.status === "ok" ? "ok" : "error"}>{step.status}</Badge>
            </div>
          ))}
          <Textarea className="h-44 resize-none" value={JSON.stringify({ missions: legacyTrace.missions, agent_updates: legacyTrace.agent_updates, planner_state: legacyTrace.planner_state }, null, 2)} readOnly />
        </div>
      )}
      {plannerState && (
        <div className="rounded-md border border-border bg-panel p-3">
          <div className="flex items-center justify-between">
            <div className="font-medium">planner.updated</div>
            <Badge tone="ok">{plannerState.paths ? "path" : "live"}</Badge>
          </div>
          <Textarea className="mt-2 h-32 resize-none" value={JSON.stringify(plannerState.paths ?? plannerState.state ?? plannerState.raw, null, 2)} readOnly />
        </div>
      )}
      {Boolean(diagnostics.missions?.length || diagnostics.planner_state) && (
        <div className="rounded-md border border-border bg-panel p-3">
          <div className="flex items-center justify-between">
            <div className="font-medium">Adapter Runtime State</div>
            <Badge>{diagnostics.missions?.length ?? 0} mission{diagnostics.missions?.length === 1 ? "" : "s"}</Badge>
          </div>
          <Textarea className="mt-2 h-36 resize-none" value={JSON.stringify({ missions: diagnostics.missions ?? [], planner_state: diagnostics.planner_state ?? {} }, null, 2)} readOnly />
        </div>
      )}
      {diagnostics.checks.map((check) => (
        <div key={check.id} className="rounded-md border border-border bg-panel p-3">
          <div className="flex items-center justify-between">
            <div className="font-medium">{check.id}</div>
            <Badge tone={check.status === "ok" ? "ok" : "error"}>{check.status}</Badge>
          </div>
          <div className="mt-1 text-xs text-muted-foreground">{check.message}</div>
        </div>
      ))}
      <Textarea className="h-[280px] resize-none" value={JSON.stringify(diagnostics.ros ?? {}, null, 2)} readOnly />
    </div>
  );
}

function PlanningVariantMatrix({
  analysis,
  selectedVariantId,
  onSelectVariant,
}: {
  analysis?: PlanningVariantAnalysis;
  selectedVariantId?: string;
  onSelectVariant: (variantId: string) => void;
}) {
  if (!analysis) return null;
  const variants = analysis.variants ?? [];
  return (
    <div className="space-y-3">
      <div className="rounded-md border border-border bg-background p-3">
        <div className="flex items-center justify-between gap-3">
          <SectionTitle icon={<Route className="h-4 w-4" />} label="Planning Variant Matrix" />
          <Badge tone={analysis.status === "ok" ? "ok" : "warn"}>{analysis.status}</Badge>
        </div>
        <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
          <InfoTile label="Start" value={formatCoordinates(analysis.inputs?.start)} />
          <InfoTile label="Objective" value={formatCoordinates(analysis.inputs?.objective)} />
          <InfoTile label="Agent" value={shortId(analysis.inputs?.agent_id)} />
          <InfoTile label="Map" value={analysis.inputs?.map ?? "unknown"} />
        </div>
        {analysis.model?.legacy_planner_issue_to_watch ? <div className="mt-2 rounded-sm border border-border bg-panel px-2 py-1 text-xs text-muted-foreground">{String(analysis.model.legacy_planner_issue_to_watch)}</div> : null}
        {analysis.notes?.map((note) => (
          <div key={note} className="mt-2 rounded-sm border border-border bg-panel px-2 py-1 text-xs text-muted-foreground">
            {note}
          </div>
        ))}
      </div>
      <div className="space-y-2">
        {variants.map((variant) => (
          <PlanningVariantCard key={variant.id} variant={variant} selected={variant.id === selectedVariantId} onSelect={() => onSelectVariant(variant.id)} />
        ))}
      </div>
      {analysis.graph_summaries && (
        <div className="rounded-md border border-border bg-background p-3">
          <div className="font-medium">Graph Summaries</div>
          <Textarea className="mt-2 h-28 resize-none" value={JSON.stringify(analysis.graph_summaries, null, 2)} readOnly spellCheck={false} />
        </div>
      )}
    </div>
  );
}

function PlanningVariantCard({ variant, selected, onSelect }: { variant: PlanningVariant; selected: boolean; onSelect: () => void }) {
  const metrics = variant.metrics ?? {};
  const route = variant.route ?? [];
  return (
    <div className={`rounded-md border bg-background p-3 ${selected ? "border-primary shadow-sm" : "border-border"}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold">{variant.label}</div>
          <div className="mt-1 text-xs text-muted-foreground">{variant.id}</div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {route.length > 0 && (
            <Button size="sm" variant={selected ? "secondary" : "outline"} onClick={onSelect} title={selected ? "Hide this planning variant" : "Show this planning variant route"}>
              <MapPinned className="h-4 w-4" />
              {selected ? "Shown" : "Map"}
            </Button>
          )}
          <Badge tone={variantTone(variant.status)}>{variant.status}</Badge>
        </div>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
        <InfoTile label="Road filter" value={String(variant.parameters?.road_filter ?? variant.parameters?.source ?? "n/a")} />
        <InfoTile label="Candidates" value={String(variant.parameters?.candidate_count ?? "n/a")} />
        <InfoTile label="Endpoint penalty" value={String(variant.parameters?.endpoint_penalty ?? "n/a")} />
        <InfoTile label="Points" value={String(metrics.point_count ?? route.length ?? "0")} />
        <InfoTile label="Graph length" value={formatMeters(metrics.graph_length_m)} />
        <InfoTile label="Visible length" value={formatMeters(metrics.visible_length_m)} />
        <InfoTile label="Start snap" value={formatMeters(metrics.start_snap_m ?? metrics.start_gap_to_current_start_m)} />
        <InfoTile label="End snap" value={formatMeters(metrics.end_snap_m ?? metrics.end_gap_to_objective_m)} />
        <InfoTile label="Planner-like cost" value={formatMeters(metrics.planner_like_cost_m)} />
        <InfoTile label="Cost with endpoint" value={formatMeters(metrics.total_cost_with_endpoint_penalty_m)} />
      </div>
      {route.length > 0 && <div className="mt-2 rounded-sm border border-border bg-panel px-2 py-1 text-xs text-muted-foreground">{formatCoordinates(route[0])} to {formatCoordinates(route[route.length - 1])}</div>}
      {variant.notes?.map((note) => (
        <div key={note} className="mt-2 rounded-sm border border-amber-200 bg-amber-50 px-2 py-1 text-xs text-amber-900">
          {note}
        </div>
      ))}
      {variant.segments && variant.segments.length > 0 && <Textarea className="mt-2 h-24 resize-none" value={JSON.stringify({ selected_nodes: variant.selected_nodes, segments: variant.segments }, null, 2)} readOnly spellCheck={false} />}
    </div>
  );
}

function variantTone(status: string): "default" | "ok" | "warn" | "error" {
  if (status === "ok") return "ok";
  if (status === "no_route" || status === "no_graph" || status === "missing") return "warn";
  if (status === "error") return "error";
  return "default";
}

function Metric({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-md border border-border bg-panel p-3">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        {icon}
        {label}
      </div>
      <div className="mt-1 text-2xl font-semibold">{value}</div>
    </div>
  );
}

function SectionTitle({ icon, label }: { icon: ReactNode; label: string }) {
  return (
    <div className="flex items-center gap-2 text-sm font-semibold">
      {icon}
      {label}
    </div>
  );
}

type MissionListItem = { mission_id: string; config?: MissionConfig; state?: MissionState; binding?: WorldBinding };

function isActiveMission(item: MissionListItem, mission?: MissionConfig, missionState?: MissionState) {
  return mission?.mission_id === item.mission_id || (!mission && missionState?.mission_id === item.mission_id);
}

function missionCardTitle(item: MissionListItem) {
  return item.config?.name ?? asMissionConfig(item.state?.config)?.name ?? `Legacy mission ${shortId(item.mission_id)}`;
}

function missionCardSubtitle(item: MissionListItem) {
  const status = item.state ? missionStatusLabel(item.state) : "local draft";
  return `${status} · Mission ID: ${item.mission_id}`;
}

function behaviorLabel(behavior?: number) {
  if (behavior === 0) return "navigate";
  if (behavior === 1) return "coverage";
  if (behavior === 2) return "custom";
  return "legacy";
}

function vehicleCountLabel(config?: MissionConfig) {
  if (!config || !Array.isArray(config.vehicles)) return "vehicles ?";
  return `${config.vehicles.length} vehicle${config.vehicles.length === 1 ? "" : "s"}`;
}

function objectiveSummary(config?: MissionConfig) {
  if (!config?.objective?.geometries?.length) return "objective ?";
  const first = config.objective.geometries[0];
  if (first.feature_id) return `feature ${shortId(first.feature_id)}`;
  const geometry = first.geometry;
  return `${geometry?.geometry_type ?? geometry?.type ?? "geometry"} objective`;
}

function objectiveDetails(objective?: MissionConfig["objective"]["geometries"][number]) {
  if (!objective) return "none";
  if (objective.feature_id) return `feature ${objective.feature_id}`;
  if (!objective.geometry) return "geometry missing";
  return `${objective.geometry.geometry_type ?? objective.geometry.type ?? "geometry"} ${formatCoordinates(objective.geometry.coordinates)}`;
}

function asPlannerUpdate(value: unknown): PlannerUpdateEvent | undefined {
  if (!value || typeof value !== "object") return undefined;
  return value as PlannerUpdateEvent;
}

function asMissionConfig(value: unknown): MissionConfig | undefined {
  if (!value || typeof value !== "object") return undefined;
  const candidate = value as Partial<MissionConfig>;
  if (typeof candidate.mission_id !== "string") return undefined;
  if (!Array.isArray(candidate.vehicles)) return undefined;
  if (!candidate.objective || !Array.isArray(candidate.objective.geometries)) return undefined;
  if (candidate.behavior !== 0 && candidate.behavior !== 1 && candidate.behavior !== 2) return undefined;
  return candidate as MissionConfig;
}

function formatPercent(value: unknown) {
  if (typeof value !== "number") return "default";
  return `${Math.round(value * 100)}%`;
}

function formatMeters(value: unknown) {
  if (typeof value !== "number") return "n/a";
  if (value >= 1000) return `${(value / 1000).toFixed(2)} km`;
  return `${value.toFixed(value >= 100 ? 0 : 1)} m`;
}

function formatTime(value?: string) {
  if (!value) return "unknown";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function shortId(value?: string) {
  if (!value) return "none";
  return value.length > 12 ? value.slice(0, 8) : value;
}

const missionStatusNames: Record<number, string> = {
  0: "NONE",
  1: "PLANNED",
  2: "PLANNED_ALTERNATIVE",
  3: "PLANNED_FAILED",
  4: "ACCEPTED",
  5: "STARTED",
  6: "PAUSED",
  7: "FAILED",
  8: "STOPPED",
  9: "DELETED",
  10: "COMPLETED",
};

function missionStatusLabel(state: MissionState) {
  if (state.status_name) return state.status_name;
  if (typeof state.status === "number") return missionStatusNames[state.status] ?? `UNKNOWN (${state.status})`;
  if (typeof state.status === "string" && state.status) return state.status;
  return "UNKNOWN";
}

function missionStateTone(state?: MissionState): "default" | "ok" | "warn" | "error" {
  if (!state) return "default";
  const label = missionStatusLabel(state);
  if (["PLANNED", "PLANNED_ALTERNATIVE", "ACCEPTED", "STARTED", "COMPLETED"].includes(label)) return "ok";
  if (["PLANNED_FAILED", "FAILED"].includes(label)) return "error";
  if (label === "NONE") return "warn";
  return "default";
}

function normalizeUuidish(value: string) {
  return value.replace(/^agent_/, "").replace(/_/g, "-").toLowerCase();
}

function sameLonLat(left: [number, number] | null | undefined, right: [number, number] | null | undefined) {
  if (!left || !right) return false;
  return left[0] === right[0] && left[1] === right[1];
}

function ElapsedClock({ startedAt }: { startedAt: number }) {
  const [nowMs, setNowMs] = useState(() => Date.now());
  useEffect(() => {
    setNowMs(Date.now());
    const timer = window.setInterval(() => setNowMs(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);
  return (
    <div className="flex shrink-0 items-center gap-1 text-[11px] text-muted-foreground" title="Time since initialization was requested">
      <Clock className="h-3.5 w-3.5" />
      {formatDuration(Math.max(0, Math.floor((nowMs - startedAt) / 1000)))}
    </div>
  );
}

function normalizeCapabilityTags(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return [...new Set(value.flatMap((item) => {
    if (typeof item !== "string") return [];
    const capability = item.trim().toLowerCase();
    return capability ? [capability] : [];
  }))];
}

function agentMatchesMissionRequirements(agent: Agent, mission: MissionConfig): boolean {
  const availableCapabilities = new Set(normalizeCapabilityTags(agent.capabilities));
  if (!normalizeCapabilityTags(mission.required_capabilities).every((capability) => availableCapabilities.has(capability))) return false;

  const requested = mission.transit?.["desired_vehicle_constraints"];
  if (!requested || typeof requested !== "object" || Array.isArray(requested)) return true;
  const supported = agent.constraints as Record<string, unknown>;
  return Object.entries(requested).every(([key, desired]) => {
    const limit = supported[key];
    return typeof desired !== "number" || typeof limit !== "number" || desired <= limit;
  });
}

function commandLabel(command: "init" | "approve" | "start") {
  if (command === "init") return "Init";
  if (command === "approve") return "Approve";
  return "Start";
}

function commandSuccessMessage(command: "init" | "approve" | "start", state: MissionState) {
  const status = missionStatusLabel(state);
  if (command === "init") return `Init accepted by legacy REST. Current status: ${status}. Wait for PLANNED before approving.`;
  if (command === "approve") return `Approve accepted by legacy REST. Current status: ${status}. Wait for ACCEPTED before starting.`;
  return `Start accepted by legacy REST. Current status: ${status}.`;
}

function emptyMission(name: string, agentId: string): MissionConfig {
  return {
    schema_version: "1.0",
    mission_id: crypto.randomUUID(),
    phase: 1,
    name,
    behavior: 0,
    vehicles: [agentId],
    transit: {
      optimization: { road_usage: 1, energy: 0.8 },
      desired_vehicle_constraints: { max_speed: 4 },
    },
    objective: {
      geometries: [],
      maximize_coverage: false,
    },
  };
}

function coverageSwathsForVehicles(vehicleIds: string[], agents: Agent[]): number[] | undefined {
  if (!vehicleIds.length) return undefined;
  const agentsById = new Map(agents.map((agent) => [normalizeUuidish(agent.agent_id), agent]));
  const widths = vehicleIds.map((vehicleId) => agentsById.get(normalizeUuidish(vehicleId))?.constraints.coverage_width_m);
  if (widths.some((width) => typeof width !== "number" || !Number.isFinite(width) || width <= 0)) return undefined;
  const validWidths = widths as number[];
  return validWidths.every((width) => width === validWidths[0]) ? [validWidths[0]] : validWidths;
}

function formatCoordinates(coordinates: unknown) {
  if (Array.isArray(coordinates) && coordinates.length >= 2 && typeof coordinates[0] === "number" && typeof coordinates[1] === "number") {
    return `[${coordinates[0].toFixed(6)}, ${coordinates[1].toFixed(6)}]`;
  }
  if (Array.isArray(coordinates)) return `${coordinates.length} coordinate set${coordinates.length === 1 ? "" : "s"}`;
  return "coordinates";
}

function toGeoJsonGeometry(draft: DraftMapFeature): Geometry {
  if (draft.geometry_type === "Point") {
    return { type: "Point", coordinates: draft.coordinates as [number, number] };
  }
  if (draft.geometry_type === "LineString") {
    return { type: "LineString", coordinates: draft.coordinates as [number, number][] };
  }
  return { type: "Polygon", coordinates: draft.coordinates as [number, number][][] };
}
