import { ArrowLeft, Bot, Bug, CheckCircle2, Clock, FileJson, GripVertical, ListChecks, MapPinned, MessageSquareText, Play, Plus, RefreshCw, Route, Send, Settings2, ShieldCheck, SlidersHorizontal, Target, Trash2, Workflow, XCircle } from "lucide-react";
import type { Feature, FeatureCollection, Geometry } from "geojson";
import type { KeyboardEvent, PointerEvent as ReactPointerEvent, ReactNode, RefObject } from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  approveMission,
  createMapFeature,
  createEventSource,
  deleteMapFeature,
  forgetMission as forgetMissionRecord,
  getContracts,
  getActiveScenario,
  getAssistantStatus,
  getDiagnostics,
  getLegacyTrace,
  getMissionState,
  getMissionExamples,
  getOsmRoads,
  getPlanningDiagnostics,
  getRuntimeBootstrap,
  getScenarios,
  initMission,
  launchScenario,
  queryOsmRoads,
  resetLegacyRuntime,
  resetAssistantConversation,
  sendAssistantMessage,
  startMission,
  updateMapFeature,
  type AgentUpdateEvent,
  type AssistantDebugTrace,
  type AssistantMessageResponse,
  type AssistantStatus,
  type ContractGraph,
  type DiagnosticsState,
  type LegacyResetResult,
  type LegacyTrace,
  type MissionExample,
  type MissionState,
  type OsmRoadImportRequest,
  type PlanningDiagnostics,
  type PlanningScenario,
  type PlanningScenarioAnalysis,
  type PlannerUpdateEvent,
  type ScenarioLaunchRequest,
  type ScenarioLaunchResult,
  type ScenarioCatalogEntry,
} from "./api";
import { Badge } from "./components/ui/badge";
import { Button } from "./components/ui/button";
import { Tabs } from "./components/ui/tabs";
import { Textarea } from "./components/ui/textarea";
import { agents as fallbackAgents, mapFeatures as fallbackFeatures, missionExamples as fallbackMissionExamples } from "./data/demo";
import { editJsonForKey, jsonCursorPosition } from "./jsonEditor";
import { createTaskPlan, normalizeMission, validateMission } from "./mission";
import { ContractExplorer } from "./ContractExplorer";
import { MapView, type DraftMapFeature } from "./MapView";
import { ScenarioLab, loadScenarioContextLibrary, type ScenarioAgentPlacement, type ScenarioContextLibrary, type ScenarioMapView } from "./ScenarioLab";
import type { Agent, MapFeature, MissionConfig } from "./types";

const LEGACY_AGENT_ID = "f9992bb3-9871-451f-90a0-9207eb9fe6c5";
const HIDDEN_MISSIONS_STORAGE_KEY = "c2_imugs2_hidden_missions";
const ASSISTANT_SESSION_STORAGE_KEY = "c2_imugs2_assistant_session_v1";
const ASSISTANT_MISSION_DRAFTS_STORAGE_KEY = "c2_imugs2_assistant_mission_drafts_v1";
const MAX_ASSISTANT_TRANSCRIPT_ITEMS = 80;
const RIGHT_PANE_WIDTHS_STORAGE_KEY = "c2_imugs2_right_pane_widths";
const DEFAULT_RIGHT_PANE_WIDTHS = { c2: 540, scenario: 860 } as const;
const MIN_RIGHT_PANE_WIDTHS = { c2: 380, scenario: 520 } as const;
const MIN_MAP_WIDTH = 360;
const RESIZE_HANDLE_WIDTH = 8;

type ResizableWorkspace = keyof typeof DEFAULT_RIGHT_PANE_WIDTHS;

type AssistantTranscriptItem = {
  id: string;
  role: "user" | "assistant";
  text: string;
  response?: AssistantMessageResponse;
  debugRequested?: boolean;
};

type AssistantSession = {
  conversationId: string;
  messages: AssistantTranscriptItem[];
};

function assistantDebugGateEnabled() {
  if (typeof window === "undefined") return false;
  return new URLSearchParams(window.location.search).get("assistantDebug") === "1";
}

function newAssistantSession(): AssistantSession {
  return { conversationId: crypto.randomUUID(), messages: [] };
}

function readAssistantSession(): AssistantSession {
  if (typeof window === "undefined") return newAssistantSession();
  try {
    const stored = JSON.parse(window.localStorage.getItem(ASSISTANT_SESSION_STORAGE_KEY) ?? "null") as {
      conversation_id?: unknown;
      messages?: unknown;
    } | null;
    if (!stored || typeof stored.conversation_id !== "string" || !stored.conversation_id.trim() || !Array.isArray(stored.messages)) {
      return newAssistantSession();
    }
    const messages = stored.messages
      .filter((item): item is AssistantTranscriptItem => {
        if (!item || typeof item !== "object") return false;
        const candidate = item as Partial<AssistantTranscriptItem>;
        return typeof candidate.id === "string"
          && (candidate.role === "user" || candidate.role === "assistant")
          && typeof candidate.text === "string";
      })
      .slice(-MAX_ASSISTANT_TRANSCRIPT_ITEMS);
    return { conversationId: stored.conversation_id, messages };
  } catch {
    return newAssistantSession();
  }
}

function writeAssistantSession(conversationId: string, messages: AssistantTranscriptItem[]) {
  if (typeof window === "undefined") return;
  const retained = messages.slice(-MAX_ASSISTANT_TRANSCRIPT_ITEMS);
  const payload = { conversation_id: conversationId, messages: retained };
  try {
    window.localStorage.setItem(ASSISTANT_SESSION_STORAGE_KEY, JSON.stringify(payload));
  } catch {
    // Debug traces can be large. Keep the visible conversation and proposals
    // if the browser's local-storage quota cannot retain every trace envelope.
    const withoutDebug = retained.map((item) => item.response?.debug_trace
      ? { ...item, response: { ...item.response, debug_trace: undefined } }
      : item);
    try {
      window.localStorage.setItem(ASSISTANT_SESSION_STORAGE_KEY, JSON.stringify({
        conversation_id: conversationId,
        messages: withoutDebug,
      }));
    } catch {
      // A disabled or exhausted local-storage implementation must not block chat.
    }
  }
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
      scenario: typeof saved.scenario === "number" && Number.isFinite(saved.scenario) ? Math.max(MIN_RIGHT_PANE_WIDTHS.scenario, saved.scenario) : DEFAULT_RIGHT_PANE_WIDTHS.scenario,
    };
  } catch {
    return { ...DEFAULT_RIGHT_PANE_WIDTHS };
  }
}

function loadInitialScenarioState() {
  const library = loadScenarioContextLibrary();
  return {
    library,
    activeId: library.active_scenario_id || undefined,
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
  return feature.properties?.source === "user";
}

function geoJsonFeatureId(feature: Feature) {
  const featureId = feature.properties?.feature_id ?? feature.id;
  return typeof featureId === "string" ? featureId : undefined;
}

function isScenarioVisibleMapFeature(feature: MapFeature, scenarioFeatureIds: Set<string>) {
  return scenarioFeatureIds.has(feature.feature_id);
}

function filterGeojsonForScenario(collection: FeatureCollection | undefined, scenarioFeatureIds: Set<string>): FeatureCollection | undefined {
  if (!collection) return collection;
  return {
    ...collection,
    features: collection.features.filter((feature) => {
      const featureId = geoJsonFeatureId(feature);
      return featureId !== undefined && scenarioFeatureIds.has(featureId);
    }),
  };
}

function flattenGeoJsonPoints(collection: FeatureCollection | undefined) {
  return collection?.features.flatMap((feature) => flattenCoordinatePoints(geoJsonCoordinates(feature.geometry))) ?? [];
}

function geoJsonCoordinates(geometry: Geometry | null | undefined) {
  return geometry && "coordinates" in geometry ? geometry.coordinates : undefined;
}

function flattenCoordinatePoints(value: unknown): [number, number][] {
  if (!Array.isArray(value)) return [];
  if (typeof value[0] === "number" && typeof value[1] === "number") return [[value[0], value[1]]];
  return value.flatMap((item) => flattenCoordinatePoints(item));
}

function mapViewKey(scenarioId: string, view: ScenarioMapView) {
  return `${scenarioId}:${view.center[0].toFixed(7)},${view.center[1].toFixed(7)},${view.zoom}`;
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

function mergeMissionState(current: Record<string, MissionState>, update: MissionState) {
  const next = { ...current };
  if (update.command_target === true) {
    for (const [missionId, state] of Object.entries(next)) {
      if (missionId !== update.mission_id && state.command_target === true) {
        next[missionId] = { ...state, command_target: false };
      }
    }
  }
  next[update.mission_id] = { ...next[update.mission_id], ...update };
  return next;
}

export default function App() {
  const [initialAssistantSession] = useState<AssistantSession>(() => readAssistantSession());
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
    ...assistantProposalConfigs(initialAssistantSession.messages),
    // The dedicated draft is the operator's latest working copy; the
    // transcript envelope is only the original model proposal.
    ...readAssistantMissionDrafts(),
  }));
  const [missionStates, setMissionStates] = useState<Record<string, MissionState>>({});
  const [hiddenMissionIds, setHiddenMissionIds] = useState<Set<string>>(() => readHiddenMissionIds());
  const [showNewMission, setShowNewMission] = useState(false);
  const [diagnostics, setDiagnostics] = useState<DiagnosticsState | undefined>();
  const [legacyTrace, setLegacyTrace] = useState<LegacyTrace | undefined>();
  const [contractGraph, setContractGraph] = useState<ContractGraph | undefined>();
  const [contractsBusy, setContractsBusy] = useState(false);
  const [contractsError, setContractsError] = useState("");
  const [planningDiagnostics, setPlanningDiagnostics] = useState<PlanningDiagnostics | undefined>();
  const [planningDiagnosticsBusy, setPlanningDiagnosticsBusy] = useState(false);
  const [selectedPlanningScenarioId, setSelectedPlanningScenarioId] = useState<string | undefined>();
  const [legacyResetResult, setLegacyResetResult] = useState<LegacyResetResult | undefined>();
  const [legacyResetBusy, setLegacyResetBusy] = useState(false);
  const [plannerState, setPlannerState] = useState<PlannerUpdateEvent | undefined>();
  const [apiError, setApiError] = useState("");
  const [commandFeedback, setCommandFeedback] = useState<{ tone: "default" | "ok" | "warn" | "error"; message: string } | undefined>();
  const [busyCommand, setBusyCommand] = useState<"init" | "approve" | "start" | undefined>();
  const [busyCommandMissionId, setBusyCommandMissionId] = useState<string | undefined>();
  const [initRequestedAt, setInitRequestedAt] = useState<number | undefined>();
  const [nowMs, setNowMs] = useState(Date.now());
  const [tab, setTab] = useState("mission");
  const [workspace, setWorkspace] = useState<"c2" | "scenario" | "contracts">("c2");
  const [selectedFeatureId, setSelectedFeatureId] = useState<string | undefined>();
  const [scenarioAgents, setScenarioAgents] = useState<Agent[]>([]);
  const [scenarioFeatureIds, setScenarioFeatureIds] = useState<string[]>([]);
  const [scenarioRoads, setScenarioRoads] = useState<FeatureCollection | undefined>();
  const [scenarioState, setScenarioState] = useState<{ library: ScenarioContextLibrary; activeId?: string }>(() => loadInitialScenarioState());
  const [activeScenarioRuntime, setActiveScenarioRuntime] = useState<ScenarioLaunchResult | undefined>();
  const [scenarioCatalog, setScenarioCatalog] = useState<ScenarioCatalogEntry[]>([]);
  const [pendingScenarioFeatureToAdd, setPendingScenarioFeatureToAdd] = useState<{ featureId: string; scenarioId: string; nonce: number } | undefined>();
  const [pendingScenarioAgentPlacement, setPendingScenarioAgentPlacement] = useState<ScenarioAgentPlacement | undefined>();
  const [placingScenarioAgentId, setPlacingScenarioAgentId] = useState<string | undefined>();
  const [mapFocus, setMapFocus] = useState<{ featureIds: string[]; nonce: number } | undefined>();
  const [mapFocusPoints, setMapFocusPoints] = useState<{ points: [number, number][]; nonce: number } | undefined>();
  const [currentMapView, setCurrentMapView] = useState<ScenarioMapView | undefined>();
  const [mapViewFocus, setMapViewFocus] = useState<{ view: ScenarioMapView; nonce: number } | undefined>();
  const [mapDraftResetNonce, setMapDraftResetNonce] = useState(0);
  const [assistantOpen, setAssistantOpen] = useState(false);
  const [assistantConversationId, setAssistantConversationId] = useState(initialAssistantSession.conversationId);
  const [assistantPrompt, setAssistantPrompt] = useState("");
  const [assistantMessages, setAssistantMessages] = useState<AssistantTranscriptItem[]>(initialAssistantSession.messages);
  const [assistantStatus, setAssistantStatus] = useState<AssistantStatus | undefined>();
  const [assistantStatusBusy, setAssistantStatusBusy] = useState(false);
  const [assistantBusy, setAssistantBusy] = useState(false);
  const [assistantError, setAssistantError] = useState("");
  const [assistantDebugEnabled, setAssistantDebugEnabled] = useState(false);
  const [assistantDebugAvailable] = useState(() => assistantDebugGateEnabled());
  const [rightPaneWidths, setRightPaneWidths] = useState<Record<ResizableWorkspace, number>>(() => readRightPaneWidths());
  const activeMissionIdRef = useRef<string | undefined>();
  const draftMissionIdRef = useRef<string | undefined>();
  const focusedScenarioViewRef = useRef<string | undefined>();
  const missionJsonRef = useRef<HTMLTextAreaElement | null>(null);
  const rightPaneRef = useRef<HTMLElement | null>(null);
  const [jsonFocus, setJsonFocus] = useState<{ needle: string; label: string; nonce: number } | undefined>();

  useEffect(() => {
    window.localStorage.setItem(RIGHT_PANE_WIDTHS_STORAGE_KEY, JSON.stringify(rightPaneWidths));
  }, [rightPaneWidths]);

  useEffect(() => {
    writeAssistantSession(assistantConversationId, assistantMessages);
  }, [assistantConversationId, assistantMessages]);

  useEffect(() => {
    const timer = window.setInterval(() => setNowMs(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

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
    getActiveScenario().then(setActiveScenarioRuntime).catch(() => undefined);
    getScenarios().then((payload) => setScenarioCatalog(payload.scenarios)).catch(() => undefined);
    getMissionExamples()
      .then((payload) => {
        setExamples(payload.examples.length ? payload.examples : fallbackMissionExamples);
      })
      .catch(() => setExamples(fallbackMissionExamples));
    getDiagnostics().then(applyDiagnostics).catch(() => undefined);
    refreshContracts(false);

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
      setAgentTelemetry((current) => ({ ...current, [updateAgentId]: update }));
      setAgents((current) =>
        current.map((agent) =>
          normalizeUuidish(agent.agent_id) === updateAgentId
            ? {
                ...agent,
                status: update.status ?? agent.status,
                current_location: update.current_location ?? agent.current_location,
              }
            : agent,
        ),
      );
    });
    source.onerror = () => setApiError("Live ROS event stream interrupted; reconnecting...");
    return () => source.close();
  }, []);

  useEffect(() => {
    let cancelled = false;
    const refreshScenarioReadiness = () => {
      getActiveScenario()
        .then((scenario) => {
          if (!cancelled) setActiveScenarioRuntime(scenario);
        })
        .catch(() => undefined);
    };
    const timer = window.setInterval(refreshScenarioReadiness, 10_000);
    window.addEventListener("focus", refreshScenarioReadiness);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
      window.removeEventListener("focus", refreshScenarioReadiness);
    };
  }, []);

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

  const activeScenarioContext = useMemo(
    () => scenarioState.library.scenarios.find((scenario) => scenario.scenario_id === scenarioState.activeId),
    [scenarioState.activeId, scenarioState.library.scenarios],
  );
  const scenarioFeatureIdSet = useMemo(() => {
    const featureIds = new Set(scenarioFeatureIds);
    const pending = pendingScenarioFeatureToAdd;
    if (pending && pending.scenarioId === activeScenarioContext?.scenario_id) {
      featureIds.add(pending.featureId);
    }
    return featureIds;
  }, [activeScenarioContext?.scenario_id, pendingScenarioFeatureToAdd, scenarioFeatureIds]);
  const scenarioVisibleMapFeatures = useMemo(
    () => mapFeatures.filter((feature) => isScenarioVisibleMapFeature(feature, scenarioFeatureIdSet)),
    [mapFeatures, scenarioFeatureIdSet],
  );
  const runtimeScenarioContext = useMemo(
    () => scenarioState.library.scenarios.find((scenario) => scenario.scenario_id === activeScenarioRuntime?.scenario_id),
    [activeScenarioRuntime?.scenario_id, scenarioState.library.scenarios],
  );
  const runtimeFeatureIdSet = useMemo(() => new Set(runtimeScenarioContext?.feature_ids ?? []), [runtimeScenarioContext?.feature_ids]);
  const runtimeMapFeatures = useMemo(
    () => mapFeatures.filter((feature) => isScenarioVisibleMapFeature(feature, runtimeFeatureIdSet)),
    [mapFeatures, runtimeFeatureIdSet],
  );
  const hasRuntimeScenario = Boolean(activeScenarioRuntime?.scenario_id);
  const c2Agents = useMemo(() => {
    if (!activeScenarioRuntime?.scenario_id) return [];

    const scenarioAgents = activeScenarioRuntime.agents ?? runtimeScenarioContext?.agents ?? [];
    const liveAgentsById = new Map(agents.map((agent) => [normalizeUuidish(agent.agent_id), agent]));
    return scenarioAgents.map((agent) => {
      const agentId = normalizeUuidish(agent.agent_id);
      const liveAgent = liveAgentsById.get(agentId);
      const telemetry = agentTelemetry[agentId];
      return {
        ...agent,
        status: telemetry?.status ?? liveAgent?.status ?? agent.status,
        current_location: telemetry?.current_location ?? liveAgent?.current_location ?? agent.current_location,
      };
    });
  }, [activeScenarioRuntime, agentTelemetry, agents, runtimeScenarioContext?.agents]);
  const c2MapFeatures = hasRuntimeScenario ? runtimeMapFeatures : [];

  const validation = useMemo(() => {
    if (!missionText.trim()) return [];
    try {
      return validateMission(normalizeMission(JSON.parse(missionText)), c2Agents, c2MapFeatures);
    } catch (error) {
      return [error instanceof Error ? error.message : "Mission JSON could not be parsed."];
    }
  }, [c2Agents, c2MapFeatures, missionText]);

  const taskPlan = useMemo(() => (mission ? createTaskPlan(mission, c2Agents, c2MapFeatures) : undefined), [c2Agents, c2MapFeatures, mission]);
  const mapMission = workspace === "scenario" ? undefined : mission;
  const mapTaskPlan = workspace === "scenario" ? undefined : taskPlan;
  const mapPlannerState = workspace === "scenario" ? undefined : plannerState;
  const mapUsesScenarioContext = workspace === "scenario" || hasRuntimeScenario;
  const mapAgents = workspace === "scenario" ? scenarioAgents : c2Agents;
  const placingScenarioAgent = scenarioAgents.find((agent) => agent.agent_id === placingScenarioAgentId);
  const applyScenarioAgents = useCallback((nextAgents: Agent[]) => setScenarioAgents(nextAgents), []);
  const applyScenarioFeatureIds = useCallback((featureIds: string[]) => setScenarioFeatureIds(featureIds), []);
  const applyScenarioRoads = useCallback((roads?: FeatureCollection) => setScenarioRoads(roads), []);
  const applyScenarioLibrary = useCallback((library: ScenarioContextLibrary) => {
    setScenarioState((current) => {
      const requestedId = library.active_scenario_id || current.activeId;
      const activeId = requestedId && library.scenarios.some((scenario) => scenario.scenario_id === requestedId)
        ? requestedId
        : library.scenarios[0]?.scenario_id;
      return { library, activeId };
    });
    setPendingScenarioFeatureToAdd((pending) => {
      if (!pending) return pending;
      const target = library.scenarios.find((scenario) => scenario.scenario_id === pending.scenarioId);
      return target?.feature_ids.includes(pending.featureId) ? undefined : pending;
    });
  }, []);
  const resetScenarioWorkspace = useCallback(() => {
    setSelectedFeatureId(undefined);
    setScenarioAgents([]);
    setScenarioFeatureIds([]);
    setScenarioRoads(undefined);
    setPendingScenarioFeatureToAdd(undefined);
    setPendingScenarioAgentPlacement(undefined);
    setPlacingScenarioAgentId(undefined);
    setMapFocus(undefined);
    setMapFocusPoints(undefined);
    setMapViewFocus(undefined);
    setMapDraftResetNonce(Date.now());
  }, []);
  const mapViewFeatures = useMemo(
    () => (workspace === "scenario" ? scenarioVisibleMapFeatures : c2MapFeatures),
    [c2MapFeatures, scenarioVisibleMapFeatures, workspace],
  );
  const mapViewGeojson = useMemo(
    () => workspace === "scenario"
      ? filterGeojsonForScenario(geojson, scenarioFeatureIdSet)
      : hasRuntimeScenario
        ? filterGeojsonForScenario(geojson, runtimeFeatureIdSet)
        : filterGeojsonForScenario(geojson, new Set()),
    [geojson, hasRuntimeScenario, runtimeFeatureIdSet, scenarioFeatureIdSet, workspace],
  );

  useEffect(() => {
    if (!mapUsesScenarioContext || !selectedFeatureId) return;
    if (!mapViewFeatures.some((feature) => feature.feature_id === selectedFeatureId)) setSelectedFeatureId(undefined);
  }, [mapUsesScenarioContext, mapViewFeatures, selectedFeatureId]);

  useEffect(() => {
    if (!activeScenarioContext) {
      setScenarioAgents([]);
      setScenarioFeatureIds([]);
      setScenarioRoads(undefined);
      return;
    }
    setScenarioAgents(activeScenarioContext.agents);
    setScenarioFeatureIds(activeScenarioContext.feature_ids);
    setScenarioRoads(activeScenarioContext.roads);
  }, [activeScenarioContext]);

  useEffect(() => {
    if (workspace !== "scenario" || !activeScenarioContext?.map_view) return;
    const key = mapViewKey(activeScenarioContext.scenario_id, activeScenarioContext.map_view);
    if (focusedScenarioViewRef.current === key) return;
    focusedScenarioViewRef.current = key;
    setMapViewFocus({ view: activeScenarioContext.map_view, nonce: Date.now() });
  }, [
    activeScenarioContext?.scenario_id,
    activeScenarioContext?.map_view?.center[0],
    activeScenarioContext?.map_view?.center[1],
    activeScenarioContext?.map_view?.zoom,
    workspace,
  ]);

  function beginPlaceScenarioAgent(agentId: string) {
    setPlacingScenarioAgentId(agentId);
    setCommandFeedback({
      tone: "warn",
      message: "Click the map to set this scenario vehicle start position.",
    });
  }

  function cancelPlaceScenarioAgent() {
    setPlacingScenarioAgentId(undefined);
    setCommandFeedback(undefined);
  }

  function placeScenarioAgent(point: [number, number]) {
    const scenarioId = activeScenarioContext?.scenario_id ?? scenarioState.activeId;
    if (!scenarioId || !placingScenarioAgentId) return;
    setPendingScenarioAgentPlacement({
      scenarioId,
      agentId: placingScenarioAgentId,
      point,
      nonce: Date.now(),
    });
    setPlacingScenarioAgentId(undefined);
    setMapFocusPoints({ points: [point], nonce: Date.now() });
    setCommandFeedback({
      tone: "ok",
      message: "Scenario vehicle start position updated.",
    });
  }

  function updateMission(next: MissionConfig, focus?: { needle: string; label: string }) {
    activeMissionIdRef.current = undefined;
    setMission(next);
    storeDraftMission(next);
    setMissionState(undefined);
    setPlannerState(undefined);
    setMissionText(JSON.stringify(next, null, 2));
    if (focus) setJsonFocus({ ...focus, nonce: Date.now() });
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
      if (!missionStates[next.mission_id]) updated[next.mission_id] = next;
      return updated;
    });
    if (isAssistantOwned) {
      if (previousDraftId && previousDraftId !== next.mission_id) {
        removeAssistantMissionDraft(previousDraftId);
      }
      writeAssistantMissionDraft(next);
    }
    draftMissionIdRef.current = missionStates[next.mission_id] ? undefined : next.mission_id;
  }

  function loadExample(example: MissionExample) {
    const next = { ...example.config, mission_id: crypto.randomUUID() };
    updateMission(next, { needle: '"mission_id"', label: "mission_id" });
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
    const targetScenarioId = workspace === "scenario" ? activeScenarioContext?.scenario_id ?? scenarioState.activeId : undefined;
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
      const result = await createMapFeature(feature);
      setGeojson(result.geojson);
      setMapFeatures(result.map_features);
      setMapFeaturesReady(true);
      setSelectedFeatureId(featureId);
      setMapFocus({ featureIds: [featureId], nonce: Date.now() });
      setMapFocusPoints(undefined);
      if (targetScenarioId) setPendingScenarioFeatureToAdd({ featureId, scenarioId: targetScenarioId, nonce: Date.now() });
      setCommandFeedback({ tone: "ok", message: `Added ${draft.feature_type} feature '${name}'.` });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setApiError(message);
      setCommandFeedback({ tone: "error", message: `Feature creation failed: ${message}` });
      return;
    }

    if (draft.use_as_objective) {
      setInlineObjective(name, draft.geometry_type, draft.coordinates, false);
    }
  }

  async function updateDrawnFeature(featureId: string, draft: DraftMapFeature) {
    const existing = mapFeatures.find((feature) => feature.feature_id === featureId);
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
      const coverageDistances = base.objective.maximum_coverage_distances?.length
        ? base.objective.maximum_coverage_distances
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
            maximum_coverage_distances: coverageDistances,
          },
        },
        { needle: '"objective"', label: "coverage geofence" },
      );
      setCommandFeedback({ tone: "ok", message: `Added '${feature.name}' as the coverage geofence and objective.` });
    } else if (feature.feature_type === "road" && feature.geometry.type === "LineString") {
      const transit = base.transit ?? {};
      const roads = Array.isArray(transit["roads"]) ? transit["roads"] : [];
      const missionRoad = missionGeometryRefFromFeature(feature);
      updateMission(
        {
          ...base,
          mission_id: crypto.randomUUID(),
          name: base.objective.geometries.length ? `${base.name ?? "Mission"} via ${feature.name}` : `Mission with ${feature.name}`,
          behavior: base.behavior,
          vehicles,
          objective: {
            ...base.objective,
            geometries: [...base.objective.geometries, missionRoad],
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
      setCommandFeedback({ tone: "ok", message: `Added road '${feature.name}' as a routable mission road.` });
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
      const result = await deleteMapFeature(feature.feature_id);
      setGeojson(result.geojson);
      setMapFeatures(result.map_features);
      setMapFeaturesReady(true);
      setScenarioFeatureIds((current) => current.filter((featureId) => featureId !== feature.feature_id));
      if (selectedFeatureId === feature.feature_id) setSelectedFeatureId(undefined);
      const missionUsesFeature = mission?.objective.geometries.some((geometryRef) => geometryRef.feature_id === feature.feature_id);
      if (missionUsesFeature) clearMission();
      setCommandFeedback({ tone: "ok", message: `Removed asset '${feature.name}'.` });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setApiError(message);
      setCommandFeedback({ tone: "error", message: `Remove asset failed: ${message}` });
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
      setMissionState(result);
      setMissionStates((current) => mergeMissionState(current, result));
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
      setSelectedPlanningScenarioId((current) => {
        const scenarios = result.scenario_analysis?.scenarios ?? [];
        if (current && scenarios.some((scenario) => scenario.id === current)) return current;
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

  async function importScenarioOsmRoads(request: OsmRoadImportRequest) {
    const result = await queryOsmRoads(request);
    const points = flattenGeoJsonPoints(result.geojson);
    if (points.length) {
      setMapFocus(undefined);
      setMapFocusPoints({ points, nonce: Date.now() });
    }
    setCommandFeedback({
      tone: result.feature_count > 0 ? "ok" : "warn",
      message: `Added OSM road section with ${result.feature_count} way${result.feature_count === 1 ? "" : "s"} to this scenario.`,
    });
    return result;
  }

  async function launchScenarioFromLab(request: ScenarioLaunchRequest): Promise<ScenarioLaunchResult> {
    setCommandFeedback({ tone: "warn", message: "Freezing and activating scenario reality..." });
    const result = await launchScenario(request);
    setAgentTelemetry({});
    if (result.agents) setAgents(result.agents);
    setActiveScenarioRuntime(result);
    getScenarios().then((payload) => setScenarioCatalog(payload.scenarios)).catch(() => undefined);
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

    const debugRequested = assistantDebugAvailable && assistantDebugEnabled;
    const assistantMessageId = crypto.randomUUID();
    setAssistantError("");
    setAssistantPrompt("");
    setAssistantMessages((current) => [
      ...current,
      { id: crypto.randomUUID(), role: "user", text: message },
      {
        id: assistantMessageId,
        role: "assistant",
        text: "Generating a validated response…",
        debugRequested,
      },
    ]);
    setAssistantBusy(true);
    try {
      const response = await sendAssistantMessage({
        conversation_id: assistantConversationId,
        message,
        debug: debugRequested || undefined,
      });
      registerAssistantProposal(response);
      setAssistantConversationId(response.conversation_id);
      setAssistantMessages((current) => current.map((item) => item.id === assistantMessageId
        ? { ...item, text: response.answer, response }
        : item));
    } catch (error) {
      setAssistantError(error instanceof Error ? error.message : String(error));
      setAssistantMessages((current) => current.map((item) => item.id === assistantMessageId
        ? {
            ...item,
            text: "Assistant response failed before a validated answer was returned.",
          }
        : item));
    } finally {
      setAssistantBusy(false);
    }
  }

  async function clearAssistantConversation() {
    if (assistantBusy) return;
    setAssistantBusy(true);
    setAssistantError("");
    try {
      await resetAssistantConversation(assistantConversationId);
      setAssistantConversationId(crypto.randomUUID());
      setAssistantMessages([]);
      setAssistantPrompt("");
    } catch (error) {
      setAssistantError(error instanceof Error ? error.message : String(error));
    } finally {
      setAssistantBusy(false);
    }
  }

  function registerAssistantProposal(response: AssistantMessageResponse) {
    const proposed = assistantProposalConfig(response);
    if (!proposed) return undefined;
    const state = missionStates[proposed.mission_id];
    // Once a proposal is in the ordinary mission editor, that editor owns the
    // working copy. Reopening or commanding the conversation card must not
    // silently replace operator edits with the original model envelope.
    const config = missionConfigs[proposed.mission_id]
      ?? asMissionConfig(state?.config)
      ?? proposed;
    setMissionConfigs((current) => ({ ...current, [config.mission_id]: current[config.mission_id] ?? config }));
    writeAssistantMissionDraft(config);
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
    activeMissionIdRef.current = state ? config.mission_id : undefined;
    draftMissionIdRef.current = state ? undefined : config.mission_id;
    setMission(config);
    setMissionText(JSON.stringify(config, null, 2));
    setMissionState(state);
    setPlannerState(hasPlannedPaths(state?.planned_paths)
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
      if (!activeScenarioRuntime?.ready) {
        setCommandFeedback({ tone: "error", message: scenarioReadinessMessage });
        return;
      }
      await initializeMissionConfig(config);
      return;
    }
    const state = missionStates[config.mission_id];
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
  const canSendMission = hasMission && validation.length === 0 && Boolean(activeScenarioRuntime?.ready);
  const scenarioReadinessMessage = activeScenarioRuntime?.ready
    ? ""
    : activeScenarioRuntime?.status === "stale"
      ? "The scenario runtime became stale after backend containers stopped. Open Scenario and activate it again."
      : activeScenarioRuntime?.error || activeScenarioRuntime?.message || "Open Scenario and activate one before initializing a mission.";
  const initDisabledReason = !hasMission
    ? "Load or create a valid mission first."
    : validation.length > 0
      ? `Resolve the mission validation issue${validation.length === 1 ? "" : "s"} first.`
      : scenarioReadinessMessage;
  const currentStatus = missionState ? missionStatusLabel(missionState) : "";
  const missionMatchesState = Boolean(mission && missionState?.mission_id === mission.mission_id);
  const missionIsCommandTarget = missionState?.command_target === true;
  const canApproveMission = missionMatchesState && missionIsCommandTarget && ["PLANNED", "PLANNED_ALTERNATIVE"].includes(currentStatus);
  const canStartMission = missionMatchesState && missionIsCommandTarget && currentStatus === "ACCEPTED";
  const missionList = useMemo(() => {
    const ids = new Set([...Object.keys(missionConfigs), ...Object.keys(missionStates)]);
    return [...ids].filter((missionId) => !hiddenMissionIds.has(missionId)).map((missionId) => ({
      mission_id: missionId,
      config: missionConfigs[missionId] ?? asMissionConfig(missionStates[missionId]?.config),
      state: missionStates[missionId],
    }));
  }, [hiddenMissionIds, missionConfigs, missionStates]);
  const selectedPlanningScenario = useMemo(
    () => planningDiagnostics?.scenario_analysis?.scenarios?.find((scenario) => scenario.id === selectedPlanningScenarioId),
    [planningDiagnostics, selectedPlanningScenarioId],
  );
  const resizableWorkspace: ResizableWorkspace = workspace === "scenario" ? "scenario" : "c2";
  const rightPaneWidth = rightPaneWidths[resizableWorkspace];
  const rightPaneMinWidth = MIN_RIGHT_PANE_WIDTHS[resizableWorkspace];
  const assistantActive = workspace === "c2" && assistantOpen;
  const assistantPaneWidth = 48;

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

  if (workspace === "contracts") {
    return (
      <main className="flex h-screen min-h-[720px] flex-col overflow-hidden bg-[#07111f] text-slate-100">
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-slate-800 bg-[#091522] px-4">
          <div className="flex min-w-0 items-center gap-2">
            <Workflow className="h-5 w-5 shrink-0 text-cyan-400" />
            <div className="min-w-0">
              <h2 className="text-sm font-semibold text-slate-100">System Contract Atlas</h2>
              <p className="truncate text-xs text-slate-400">Evidence-backed map of the legacy mission, planning, execution, and feedback contracts.</p>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <Tabs
              value={workspace}
              onValueChange={(value) => setWorkspace(value as "c2" | "scenario" | "contracts")}
              items={[
                { value: "c2", label: "C2" },
                { value: "scenario", label: "Scenario" },
                { value: "contracts", label: "Contracts" },
              ]}
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
        osmRoads={mapUsesScenarioContext ? undefined : osmRoads}
        scenarioRoads={workspace === "scenario" ? scenarioRoads : runtimeScenarioContext?.roads}
        mission={mapMission}
        taskPlan={mapTaskPlan}
        plannerState={mapPlannerState}
        planningScenario={selectedPlanningScenario}
        selectedFeatureId={selectedFeatureId}
        focusFeatureIds={mapFocus?.featureIds}
        focusPoints={mapFocusPoints?.points}
        focusNonce={mapFocus?.nonce}
        focusPointsNonce={mapFocusPoints?.nonce}
        focusView={mapViewFocus}
        resetDraftNonce={mapDraftResetNonce}
        placingAgentName={placingScenarioAgent?.name || placingScenarioAgent?.agent_id}
        onPlaceAgent={placingScenarioAgentId ? placeScenarioAgent : undefined}
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
            {workspace === "scenario" ? <SlidersHorizontal className="h-5 w-5 text-primary" /> : assistantActive ? <Bot className="h-5 w-5 text-primary" /> : <FileJson className="h-5 w-5 text-primary" />}
            <div>
              <h2 className="text-sm font-semibold">{workspace === "scenario" ? "Scenario Lab" : assistantActive ? "C2 Assistant" : "Mission Definition"}</h2>
              <p className="text-xs text-muted-foreground">{workspace === "scenario" ? "Situation, vehicles, and map assets." : assistantActive ? "Natural-language drafting connected to the manual editor." : "UI to adapter to old REST/ROS."}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Tabs
              value={workspace}
              onValueChange={(value) => setWorkspace(value as "c2" | "scenario" | "contracts")}
              items={[
                { value: "c2", label: "C2" },
                { value: "scenario", label: "Scenario" },
                { value: "contracts", label: "Contracts" },
              ]}
            />
            {assistantActive ? (
              <Badge tone={assistantStatus?.configured ? "ok" : "default"}>assistant</Badge>
            ) : workspace === "c2" ? (
              !hasSelectedMission ? <Badge>empty</Badge> : !hasMission ? <Badge>runtime</Badge> : validation.length === 0 ? <Badge tone="ok">valid</Badge> : <Badge tone="error">{validation.length} issue{validation.length === 1 ? "" : "s"}</Badge>
            ) : (
              <Badge tone="ok">builder</Badge>
            )}
          </div>
        </header>

        {workspace === "c2" && !assistantActive && (
          <div className="space-y-3 border-b border-border px-4 py-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <Tabs
                value={tab}
                onValueChange={setTab}
                items={[
                  { value: "mission", label: "Mission" },
                  { value: "plan", label: "Plan" },
                  { value: "assets", label: "Assets" },
                  { value: "diagnostics", label: "Diagnostics" },
                ]}
              />
              <span title={activeScenarioRuntime?.error}>
                <Badge tone={activeScenarioRuntime?.ready ? "ok" : "warn"}>
                  {activeScenarioRuntime?.ready
                    ? `active: ${activeScenarioRuntime.name ?? activeScenarioRuntime.scenario_id}`
                    : activeScenarioRuntime?.status === "stale"
                      ? "scenario stale"
                      : "no ready scenario"}
                </Badge>
              </span>
            </div>
            {!activeScenarioRuntime?.ready && (
              <div className="flex items-center justify-between gap-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-950">
                <span>{scenarioReadinessMessage}</span>
                <Button size="sm" variant="outline" className="shrink-0" onClick={() => setWorkspace("scenario")}>
                  Open Scenario
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
                nowMs={nowMs}
              />
            )}
            <div className="grid grid-cols-3 gap-2">
              <Button size="sm" variant="outline" onClick={() => sendInitMission().catch(() => undefined)} disabled={!canSendMission || Boolean(busyCommand)} title={canSendMission ? "Initialize this mission in the active scenario" : initDisabledReason}>
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
                <Badge tone={commandFeedback.tone}>{commandFeedback.tone === "warn" ? "sending" : commandFeedback.tone}</Badge>
                <span className="leading-6">{commandFeedback.message}</span>
              </div>
            )}
            {apiError && <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">{apiError}</div>}
          </div>
        )}

        <section className={assistantActive ? "flex min-h-0 flex-1 overflow-hidden" : "min-h-0 flex-1 overflow-auto overflow-x-hidden p-4"}>
          {assistantActive ? (
            <AssistantPanel
              status={assistantStatus}
              statusBusy={assistantStatusBusy}
              busy={assistantBusy}
              error={assistantError}
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
              nowMs={nowMs}
              activeScenarioReady={activeScenarioRuntime?.ready === true}
              commandFeedback={commandFeedback}
              debugAvailable={assistantDebugAvailable}
              debugEnabled={assistantDebugEnabled}
              onPromptChange={setAssistantPrompt}
              onDebugEnabledChange={setAssistantDebugEnabled}
              onSend={() => submitAssistantMessage().catch(() => undefined)}
              onReset={() => clearAssistantConversation().catch(() => undefined)}
              onRefreshStatus={() => refreshAssistantStatus().catch(() => undefined)}
              onBack={() => setAssistantOpen(false)}
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
                  showNewMission={showNewMission}
                  validation={validation}
                  onLoadExample={loadExample}
                  onSelectMission={selectMission}
                  onNewMission={startNewMission}
                  onCloseComposer={closeMissionComposer}
                  onForgetMission={(missionId) => forgetMission(missionId).catch((error) => setApiError(String(error)))}
                  onMissionTextChange={updateMissionText}
                  missionJsonRef={missionJsonRef}
                  jsonFocusLabel={jsonFocus?.label}
                  onClear={clearMission}
                />
              )}

              {tab === "plan" && <PlanPanel taskPlan={taskPlan} />}

              {tab === "assets" && <AssetsPanel agents={c2Agents} mapFeatures={c2MapFeatures} mission={mission} selectedFeatureId={selectedFeatureId} onSetObjective={setFeatureAsObjective} onRemoveFeature={(feature) => removeFeature(feature).catch((error) => setApiError(String(error)))} />}

              {tab === "diagnostics" && (
                <DiagnosticsPanel
                  diagnostics={diagnostics}
                  legacyTrace={legacyTrace}
                  plannerState={plannerState}
                  planningDiagnostics={planningDiagnostics}
                  planningDiagnosticsBusy={planningDiagnosticsBusy}
                  selectedPlanningScenarioId={selectedPlanningScenarioId}
                  legacyResetBusy={legacyResetBusy}
                  legacyResetResult={legacyResetResult}
                  onRefreshLegacyTrace={() => refreshLegacyTrace().catch((error) => setApiError(String(error)))}
                  onRefreshPlanningDiagnostics={() => refreshPlanningDiagnostics()}
                  onSelectPlanningScenario={(scenarioId) => setSelectedPlanningScenarioId((current) => (current === scenarioId ? undefined : scenarioId))}
                  onCleanLegacyRuntime={() => cleanLegacyRuntimeForExamples()}
                />
              )}
            </>
          ) : (
            <ScenarioLab
              mapFeatures={mapFeatures}
              mapFeaturesReady={mapFeaturesReady}
              selectedFeatureId={selectedFeatureId}
              pendingFeatureToAdd={pendingScenarioFeatureToAdd}
              pendingAgentPlacement={pendingScenarioAgentPlacement}
              currentMapView={currentMapView}
              catalogScenarios={scenarioCatalog}
              placingAgentId={placingScenarioAgentId}
              onScenarioAgentsChange={applyScenarioAgents}
              onActiveScenarioFeaturesChange={applyScenarioFeatureIds}
              onScenarioRoadsChange={applyScenarioRoads}
              onScenarioLibraryChange={applyScenarioLibrary}
              onSelectFeature={selectMapFeature}
              onImportOsmRoads={importScenarioOsmRoads}
              onLaunchScenario={launchScenarioFromLab}
              onScenarioContextReset={resetScenarioWorkspace}
              onBeginPlaceAgent={beginPlaceScenarioAgent}
              onCancelPlaceAgent={cancelPlaceScenarioAgent}
            />
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
  nowMs,
  activeScenarioReady,
  commandFeedback,
  debugAvailable,
  debugEnabled,
  onPromptChange,
  onDebugEnabledChange,
  onSend,
  onReset,
  onRefreshStatus,
  onBack,
  onOpenMission,
  onValidateMission,
  onMissionCommand,
}: {
  status?: AssistantStatus;
  statusBusy: boolean;
  busy: boolean;
  error: string;
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
  nowMs: number;
  activeScenarioReady: boolean;
  commandFeedback?: { tone: "default" | "ok" | "warn" | "error"; message: string };
  debugAvailable: boolean;
  debugEnabled: boolean;
  onPromptChange: (value: string) => void;
  onDebugEnabledChange: (value: boolean) => void;
  onSend: () => void;
  onReset: () => void;
  onRefreshStatus: () => void;
  onBack: () => void;
  onOpenMission: (response: AssistantMessageResponse) => void;
  onValidateMission: (response: AssistantMessageResponse) => void;
  onMissionCommand: (response: AssistantMessageResponse, command: "init" | "approve" | "start") => void;
}) {
  const transcriptEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: busy ? "auto" : "smooth", block: "end" });
  }, [busy, messages.length, messages[messages.length - 1]?.text]);

  const configured = status?.configured === true;
  const statusTone = statusBusy ? "default" : configured ? "ok" : "warn";
  const statusLabel = statusBusy ? "checking" : configured ? "ready" : "not configured";

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="shrink-0 space-y-2 border-b border-border p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <MessageSquareText className="h-4 w-4 shrink-0 text-primary" />
              <h2 className="text-sm font-semibold">Mission Assistant</h2>
            </div>
            <p
              className="mt-1 truncate text-xs text-muted-foreground"
              title={status ? `${status.base_url} · max output ${status.max_output_tokens} tokens · thinking ${status.thinking_enabled ? "enabled" : "disabled"}${status.preserve_thinking ? " and preserved" : ""}` : undefined}
            >
              {status ? `${status.model} · ${status.thinking_enabled ? `${status.reasoning_effort || "max"} thinking` : "thinking off"} · prompts ${status.prompt_version}` : "Backend-grounded mission drafting"}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-1">
            <Button type="button" size="sm" variant="outline" onClick={onBack}>
              <ArrowLeft className="h-4 w-4" />
              Manual UI
            </Button>
            <Button
              type="button"
              size="icon"
              variant="ghost"
              className="h-8 w-8"
              disabled={busy || messages.length === 0}
              onClick={onReset}
              title="Reset conversation"
              aria-label="Reset assistant conversation"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
        <div className="flex items-center justify-between gap-2">
          <Badge tone={statusTone}>{statusLabel}</Badge>
          <div className="flex items-center gap-1">
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
        {debugEnabled && (
          <div className="rounded-md border border-amber-200 bg-amber-50 px-2 py-1.5 text-[11px] leading-4 text-amber-950">
            Diagnostic capture is enabled for new messages. Backend context reads and validation events are separate from LLM tool calls; this assistant currently exposes no callable tools to the model.
          </div>
        )}
      </div>

      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-3" aria-live="polite">
        {messages.length === 0 && (
          <div className="rounded-md border border-dashed border-border bg-background p-3 text-xs leading-5 text-muted-foreground">
            Ask about the current map, fleet, missions, or request a mission draft. Each answer is grounded in a fresh operational-picture revision.
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
                    <div className="flex flex-wrap items-center gap-1 text-[11px] text-muted-foreground">
                      <span>picture r{response.picture_revision}</span>
                      <span aria-hidden="true">·</span>
                      <span title={response.picture_observed_at}>{formatAssistantObservedAt(response.picture_observed_at)}</span>
                      <span aria-hidden="true">·</span>
                      <span>prompt {response.prompt_version}</span>
                    </div>

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
                        nowMs={nowMs}
                        selected={proposalSelected}
                        activeScenarioReady={activeScenarioReady}
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
        <Textarea
          className="min-h-20 resize-none font-sans text-sm"
          value={prompt}
          onChange={(event) => onPromptChange(event.target.value)}
          placeholder={configured ? "Ask about operations or request a mission…" : "Assistant unavailable"}
          disabled={!configured || busy}
          aria-label="Message the mission assistant"
        />
        <Button type="submit" className="w-full" disabled={!configured || busy || !prompt.trim()}>
          <Send className="h-4 w-4" />
          {busy ? "Working…" : "Send"}
        </Button>
        <p className="text-[11px] leading-4 text-muted-foreground">Validated proposals are saved in Missions. Runtime commands remain explicit operator actions.</p>
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
  nowMs,
  selected,
  activeScenarioReady,
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
  nowMs: number;
  selected: boolean;
  activeScenarioReady: boolean;
  feedback?: { tone: "default" | "ok" | "warn" | "error"; message: string };
  onOpen: () => void;
  onValidate: () => void;
  onCommand: (command: "init" | "approve" | "start") => void;
}) {
  const validation = response.mission_proposal_validation;
  const valid = validation?.valid === true && Boolean(config);
  const status = state ? missionStatusLabel(state) : "DRAFT";
  const isCommandTarget = state?.command_target === true;
  const canApprove = valid && isCommandTarget && ["PLANNED", "PLANNED_ALTERNATIVE"].includes(status) && !busyCommand;
  const canStart = valid && isCommandTarget && status === "ACCEPTED" && !busyCommand;
  const canInit = valid && activeScenarioReady && !busyCommand;

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
          <div className="mt-0.5 truncate text-[10px] text-muted-foreground">{config?.mission_id ?? "No valid mission ID"}</div>
        </button>
        <Badge tone={valid ? state ? missionStateTone(state) : "ok" : "error"}>
          {valid ? state ? humanizeEnum(status) : "Validated draft" : "Invalid"}
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

      {valid && (
        <>
          <MissionRuntimeStatus
            mission={config}
            missionState={state}
            plannerState={plannerState}
            agentTelemetry={agentTelemetry}
            busyCommand={busyCommand}
            initRequestedAt={initRequestedAt}
            nowMs={nowMs}
          />
          <p className="text-[10px] leading-4 text-muted-foreground">
            Draft validation is deterministic. Init requests planning; Approve and Start unlock only for the latest initialized mission after confirmed runtime transitions.
          </p>
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
            <Button type="button" size="sm" variant="outline" onClick={() => onCommand("init")} disabled={!canInit} title={activeScenarioReady ? "Initialize this mission and request planning" : "A ready environment is required before Init"}>
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

  return (
    <div className="mt-2 space-y-2 border-t border-dashed border-border pt-2 text-[11px]">
      <div className="flex flex-wrap items-center justify-between gap-1">
        <span className="font-medium text-foreground">Diagnostic trace</span>
        <Badge tone={trace ? "ok" : "warn"}>{trace ? "captured" : "unavailable"}</Badge>
      </div>

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
            <pre className="max-h-64 overflow-auto whitespace-pre-wrap break-all font-mono text-[10px] leading-4 text-muted-foreground">
              {safeDebugJson(modelEvents)}
            </pre>
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
          <pre className="max-h-80 overflow-auto whitespace-pre-wrap break-all border-t border-border p-2 font-mono text-[10px] leading-4 text-muted-foreground">
            {safeDebugJson(trace)}
          </pre>
        </details>
      )}
    </div>
  );
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
      <pre className="max-h-64 overflow-auto whitespace-pre-wrap break-all font-mono text-[10px] leading-4 text-muted-foreground">
        {safeDebugJson(value)}
      </pre>
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

function formatAssistantObservedAt(value: string) {
  const timestamp = new Date(value);
  if (Number.isNaN(timestamp.getTime())) return value;
  return timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
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
  nowMs,
}: {
  mission?: MissionConfig;
  missionState?: MissionState;
  plannerState?: PlannerUpdateEvent;
  agentTelemetry: Record<string, AgentUpdateEvent>;
  busyCommand?: "init" | "approve" | "start";
  initRequestedAt?: number;
  nowMs: number;
}) {
  const missionSignal = missionRuntimeSignal(missionState, busyCommand);
  const plannerSignal = plannerRuntimeSignal(mission?.mission_id ?? missionState?.mission_id, missionState, plannerState);
  const routeSignal = routeRuntimeSignal(mission?.mission_id ?? missionState?.mission_id, missionState, plannerState);
  const executionSignal = executionRuntimeSignal(mission, missionState, agentTelemetry);
  const signals = [missionSignal, plannerSignal, routeSignal, executionSignal];
  const startedAt = missionState?.initialized_at ? Date.parse(missionState.initialized_at) : initRequestedAt;
  const elapsedSeconds = startedAt ? Math.max(0, Math.floor((nowMs - startedAt) / 1000)) : 0;
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
        {startedAt && !isTerminal && (
          <div className="flex shrink-0 items-center gap-1 text-[11px] text-muted-foreground" title="Time since initialization was requested">
            <Clock className="h-3.5 w-3.5" />
            {formatDuration(elapsedSeconds)}
          </div>
        )}
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
  showNewMission,
  validation,
  onLoadExample,
  onSelectMission,
  onNewMission,
  onCloseComposer,
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
  showNewMission: boolean;
  validation: string[];
  onLoadExample: (example: MissionExample) => void;
  onSelectMission: (missionId: string) => void;
  onNewMission: () => void;
  onCloseComposer: () => void;
  onForgetMission: (missionId: string) => void;
  onMissionTextChange: (value: string) => void;
  missionJsonRef: RefObject<HTMLTextAreaElement>;
  jsonFocusLabel?: string;
  onClear: () => void;
}) {
  if (showNewMission) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <Button size="sm" variant="ghost" onClick={onCloseComposer}>
            <ArrowLeft className="h-4 w-4" />
            Missions
          </Button>
          <Badge tone={missionText.trim() && validation.length === 0 ? "ok" : "default"}>{missionText.trim() ? "draft" : "new"}</Badge>
        </div>

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
                  <div className="mt-1 text-xs text-muted-foreground">{example.vehicles.join(", ")}</div>
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
        <div className="flex items-center justify-between">
          <Button size="sm" variant="ghost" onClick={onClear}>
            <ArrowLeft className="h-4 w-4" />
            Missions
          </Button>
          {missionState ? <Badge tone={missionStateTone(missionState)}>{missionStatusLabel(missionState)}</Badge> : <Badge>draft</Badge>}
        </div>

        {missionText.trim() ? (
          <MissionEditor
            mission={mission}
            missionText={missionText}
            missionState={missionState}
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
      <div className="flex items-center justify-between">
        <SectionTitle icon={<ListChecks className="h-4 w-4" />} label="Missions" />
        <Button size="sm" variant={showNewMission ? "secondary" : "outline"} onClick={onNewMission}>
          <Plus className="h-4 w-4" />
          New Mission
        </Button>
      </div>

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
                  <div className="mt-1 text-xs text-muted-foreground">{missionCardSubtitle(item)}</div>
                  <div className="mt-2 flex flex-wrap gap-1">
                    <Badge>{behaviorLabel(item.config?.behavior)}</Badge>
                    <Badge>{vehicleCountLabel(item.config)}</Badge>
                    <Badge>{objectiveSummary(item.config)}</Badge>
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

      <div className="rounded-md border border-border bg-panel p-4 text-sm text-muted-foreground">Select an existing mission, create one from an example, or choose an objective point on the map.</div>
    </div>
  );
}

function MissionEditor({
  mission,
  missionText,
  missionState,
  validation,
  jsonFocusLabel,
  missionJsonRef,
  onMissionTextChange,
  onClear,
}: {
  mission?: MissionConfig;
  missionText: string;
  missionState?: MissionState;
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

function PlanPanel({ taskPlan }: { taskPlan?: ReturnType<typeof createTaskPlan> }) {
  if (!taskPlan) return <div className="rounded-md border border-border bg-panel p-4 text-sm text-muted-foreground">Load or edit a valid mission to preview the adapter-side task projection.</div>;
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2">
        <Metric icon={<Route className="h-4 w-4" />} label="Tasks" value={Object.keys(taskPlan.tasks).length.toString()} />
        <Metric icon={<MapPinned className="h-4 w-4" />} label="Objectives" value={Object.values(taskPlan.tasks).reduce((sum, task) => sum + task.objectives.length, 0).toString()} />
      </div>
      <Textarea className="h-[500px] resize-none" value={JSON.stringify(taskPlan, null, 2)} readOnly />
    </div>
  );
}

function ValidationList({ errors }: { errors: string[] }) {
  if (errors.length === 0) {
    return (
      <div className="flex items-center gap-2 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
        <CheckCircle2 className="h-4 w-4" />
        Mission conforms to the active contract.
      </div>
    );
  }
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
                <Button size="icon" variant="ghost" disabled={feature.properties?.source !== "user"} onClick={() => onRemoveFeature(feature)} title={feature.properties?.source === "user" ? "Remove user-created asset" : "Legacy baseline assets are read-only"}>
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
          <div className="mt-1 break-all text-xs text-muted-foreground">{mission.mission_id}</div>
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
            <div className="mt-1 break-all text-xs text-muted-foreground">{state.mission_id}</div>
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
  selectedPlanningScenarioId,
  legacyResetBusy,
  legacyResetResult,
  onRefreshLegacyTrace,
  onRefreshPlanningDiagnostics,
  onSelectPlanningScenario,
  onCleanLegacyRuntime,
}: {
  diagnostics?: DiagnosticsState;
  legacyTrace?: LegacyTrace;
  plannerState?: PlannerUpdateEvent;
  planningDiagnostics?: PlanningDiagnostics;
  planningDiagnosticsBusy: boolean;
  selectedPlanningScenarioId?: string;
  legacyResetBusy: boolean;
  legacyResetResult?: LegacyResetResult;
  onRefreshLegacyTrace: () => void;
  onRefreshPlanningDiagnostics: () => void;
  onSelectPlanningScenario: (scenarioId: string) => void;
  onCleanLegacyRuntime: () => void;
}) {
  if (!diagnostics) return <div className="text-sm text-muted-foreground">Waiting for diagnostics...</div>;
  return (
    <div className="space-y-3">
      <div className="flex justify-end gap-2">
        <Button size="sm" variant="outline" onClick={onRefreshPlanningDiagnostics} disabled={planningDiagnosticsBusy} title="Compare planner parameter scenarios and legacy mission output">
          <Route className="h-4 w-4" />
          {planningDiagnosticsBusy ? "Checking" : "Scenario Debug"}
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
          <PlanningScenarioMatrix analysis={planningDiagnostics.scenario_analysis} selectedScenarioId={selectedPlanningScenarioId} onSelectScenario={onSelectPlanningScenario} />
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

function PlanningScenarioMatrix({
  analysis,
  selectedScenarioId,
  onSelectScenario,
}: {
  analysis?: PlanningScenarioAnalysis;
  selectedScenarioId?: string;
  onSelectScenario: (scenarioId: string) => void;
}) {
  if (!analysis) return null;
  const scenarios = analysis.scenarios ?? [];
  return (
    <div className="space-y-3">
      <div className="rounded-md border border-border bg-background p-3">
        <div className="flex items-center justify-between gap-3">
          <SectionTitle icon={<Route className="h-4 w-4" />} label="Scenario Matrix" />
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
        {scenarios.map((scenario) => (
          <PlanningScenarioCard key={scenario.id} scenario={scenario} selected={scenario.id === selectedScenarioId} onSelect={() => onSelectScenario(scenario.id)} />
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

function PlanningScenarioCard({ scenario, selected, onSelect }: { scenario: PlanningScenario; selected: boolean; onSelect: () => void }) {
  const metrics = scenario.metrics ?? {};
  const route = scenario.route ?? [];
  return (
    <div className={`rounded-md border bg-background p-3 ${selected ? "border-primary shadow-sm" : "border-border"}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold">{scenario.label}</div>
          <div className="mt-1 text-xs text-muted-foreground">{scenario.id}</div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {route.length > 0 && (
            <Button size="sm" variant={selected ? "secondary" : "outline"} onClick={onSelect} title={selected ? "Hide this scenario on the map" : "Show this scenario route on the map"}>
              <MapPinned className="h-4 w-4" />
              {selected ? "Shown" : "Map"}
            </Button>
          )}
          <Badge tone={scenarioTone(scenario.status)}>{scenario.status}</Badge>
        </div>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
        <InfoTile label="Road filter" value={String(scenario.parameters?.road_filter ?? scenario.parameters?.source ?? "n/a")} />
        <InfoTile label="Candidates" value={String(scenario.parameters?.candidate_count ?? "n/a")} />
        <InfoTile label="Endpoint penalty" value={String(scenario.parameters?.endpoint_penalty ?? "n/a")} />
        <InfoTile label="Points" value={String(metrics.point_count ?? route.length ?? "0")} />
        <InfoTile label="Graph length" value={formatMeters(metrics.graph_length_m)} />
        <InfoTile label="Visible length" value={formatMeters(metrics.visible_length_m)} />
        <InfoTile label="Start snap" value={formatMeters(metrics.start_snap_m ?? metrics.start_gap_to_current_start_m)} />
        <InfoTile label="End snap" value={formatMeters(metrics.end_snap_m ?? metrics.end_gap_to_objective_m)} />
        <InfoTile label="Planner-like cost" value={formatMeters(metrics.planner_like_cost_m)} />
        <InfoTile label="Cost with endpoint" value={formatMeters(metrics.total_cost_with_endpoint_penalty_m)} />
      </div>
      {route.length > 0 && <div className="mt-2 rounded-sm border border-border bg-panel px-2 py-1 text-xs text-muted-foreground">{formatCoordinates(route[0])} to {formatCoordinates(route[route.length - 1])}</div>}
      {scenario.notes?.map((note) => (
        <div key={note} className="mt-2 rounded-sm border border-amber-200 bg-amber-50 px-2 py-1 text-xs text-amber-900">
          {note}
        </div>
      ))}
      {scenario.segments && scenario.segments.length > 0 && <Textarea className="mt-2 h-24 resize-none" value={JSON.stringify({ selected_nodes: scenario.selected_nodes, segments: scenario.segments }, null, 2)} readOnly spellCheck={false} />}
    </div>
  );
}

function scenarioTone(status: string): "default" | "ok" | "warn" | "error" {
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

type MissionListItem = { mission_id: string; config?: MissionConfig; state?: MissionState };

function isActiveMission(item: MissionListItem, mission?: MissionConfig, missionState?: MissionState) {
  return mission?.mission_id === item.mission_id || (!mission && missionState?.mission_id === item.mission_id);
}

function missionCardTitle(item: MissionListItem) {
  return item.config?.name ?? asMissionConfig(item.state?.config)?.name ?? `Legacy mission ${shortId(item.mission_id)}`;
}

function missionCardSubtitle(item: MissionListItem) {
  const status = item.state ? missionStatusLabel(item.state) : "local draft";
  return `${status} · ${item.mission_id}`;
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
