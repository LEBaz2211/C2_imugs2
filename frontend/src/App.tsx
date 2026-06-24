import { ArrowLeft, Bot, Bug, CheckCircle2, ChevronRight, Clock, FileJson, ListChecks, MapPinned, MessageSquareText, Play, Plus, RefreshCw, Route, Send, Settings2, ShieldCheck, Target, Trash2, XCircle } from "lucide-react";
import type { Feature, FeatureCollection, Geometry } from "geojson";
import type { ReactNode, RefObject } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  approveMission,
  createMapFeature,
  createEventSource,
  deleteMapFeature,
  forgetMission as forgetMissionRecord,
  getDiagnostics,
  getLegacyTrace,
  getMissionExamples,
  getOsmRoads,
  getRuntimeBootstrap,
  initMission,
  resetLegacyRuntime,
  startMission,
  updateMapFeature,
  type AgentUpdateEvent,
  type DiagnosticsState,
  type LegacyResetResult,
  type LegacyTrace,
  type MissionExample,
  type MissionState,
  type PlannerUpdateEvent,
} from "./api";
import { Badge } from "./components/ui/badge";
import { Button } from "./components/ui/button";
import { Tabs } from "./components/ui/tabs";
import { Textarea } from "./components/ui/textarea";
import { agents as fallbackAgents, mapFeatures as fallbackFeatures, missionExamples as fallbackMissionExamples } from "./data/demo";
import { createTaskPlan, normalizeMission, validateMission } from "./mission";
import { MapView, type DraftMapFeature } from "./MapView";
import type { Agent, MapFeature, MissionConfig } from "./types";

const LEGACY_AGENT_ID = "f9992bb3-9871-451f-90a0-9207eb9fe6c5";
const HIDDEN_MISSIONS_STORAGE_KEY = "c2_imugs2_hidden_missions";

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

function directGeometryRefFromFeature(feature: MapFeature) {
  if (isUserMapFeature(feature)) {
    return geometryLiteralFromFeature(feature);
  }
  return { feature_id: feature.feature_id };
}

export default function App() {
  const [agents, setAgents] = useState<Agent[]>(fallbackAgents);
  const [mapFeatures, setMapFeatures] = useState<MapFeature[]>(fallbackFeatures);
  const [geojson, setGeojson] = useState<FeatureCollection | undefined>();
  const [osmRoads, setOsmRoads] = useState<FeatureCollection | undefined>();
  const [examples, setExamples] = useState<MissionExample[]>(fallbackMissionExamples);
  const [mission, setMission] = useState<MissionConfig | undefined>();
  const [missionText, setMissionText] = useState("");
  const [missionState, setMissionState] = useState<MissionState | undefined>();
  const [missionConfigs, setMissionConfigs] = useState<Record<string, MissionConfig>>({});
  const [missionStates, setMissionStates] = useState<Record<string, MissionState>>({});
  const [hiddenMissionIds, setHiddenMissionIds] = useState<Set<string>>(() => readHiddenMissionIds());
  const [showNewMission, setShowNewMission] = useState(false);
  const [diagnostics, setDiagnostics] = useState<DiagnosticsState | undefined>();
  const [legacyTrace, setLegacyTrace] = useState<LegacyTrace | undefined>();
  const [legacyResetResult, setLegacyResetResult] = useState<LegacyResetResult | undefined>();
  const [legacyResetBusy, setLegacyResetBusy] = useState(false);
  const [plannerState, setPlannerState] = useState<PlannerUpdateEvent | undefined>();
  const [apiError, setApiError] = useState("");
  const [commandFeedback, setCommandFeedback] = useState<{ tone: "default" | "ok" | "warn" | "error"; message: string } | undefined>();
  const [busyCommand, setBusyCommand] = useState<"init" | "approve" | "start" | undefined>();
  const [initRequestedAt, setInitRequestedAt] = useState<number | undefined>();
  const [nowMs, setNowMs] = useState(Date.now());
  const [tab, setTab] = useState("mission");
  const [selectedFeatureId, setSelectedFeatureId] = useState<string | undefined>();
  const [assistantOpen, setAssistantOpen] = useState(false);
  const [assistantPrompt, setAssistantPrompt] = useState("Send Themis Fr to the selected objective point using roads.");
  const activeMissionIdRef = useRef<string | undefined>();
  const missionJsonRef = useRef<HTMLTextAreaElement | null>(null);
  const [jsonFocus, setJsonFocus] = useState<{ needle: string; label: string; nonce: number } | undefined>();

  useEffect(() => {
    const timer = window.setInterval(() => setNowMs(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

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
        setGeojson(bootstrap.geojson);
        if (bootstrap.osm_roads) setOsmRoads(bootstrap.osm_roads);
      })
      .catch((error) => setApiError(`Backend bootstrap unavailable, using fallback data. ${String(error)}`));

    getOsmRoads().then(setOsmRoads).catch(() => undefined);
    getMissionExamples()
      .then((payload) => {
        setExamples(payload.examples.length ? payload.examples : fallbackMissionExamples);
      })
      .catch(() => setExamples(fallbackMissionExamples));
    getDiagnostics().then(applyDiagnostics).catch(() => undefined);

    const source = createEventSource();
    source.addEventListener("diagnostics.updated", (event) => {
      const update = JSON.parse((event as MessageEvent).data) as DiagnosticsState;
      applyDiagnostics(update);
    });
    source.addEventListener("mission.updated", (event) => {
      const update = JSON.parse((event as MessageEvent).data) as MissionState;
      const activeMissionId = activeMissionIdRef.current;
      setMissionStates((current) => ({ ...current, [update.mission_id]: { ...current[update.mission_id], ...update } }));
      if (activeMissionId && update.mission_id === activeMissionId) setMissionState((current) => ({ ...current, ...update }));
    });
    source.addEventListener("planner.updated", (event) => {
      const update = JSON.parse((event as MessageEvent).data) as PlannerUpdateEvent;
      const activeMissionId = activeMissionIdRef.current;
      if (update.mission_id && activeMissionId && update.mission_id !== activeMissionId) return;
      if (!activeMissionId && update.mission_id) return;
      setPlannerState((current) => {
        if (update.paths) return update;
        if (current?.paths) return { ...current, state: update.state, raw: update.raw };
        return update;
      });
    });
    source.addEventListener("agent.updated", (event) => {
      const update = JSON.parse((event as MessageEvent).data) as AgentUpdateEvent;
      const updateAgentId = normalizeUuidish(update.agent_id);
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

  function applyDiagnostics(update: DiagnosticsState) {
    setDiagnostics(update);
    if (update.missions?.length) {
      setMissionStates((current) => {
        const next = { ...current };
        for (const missionUpdate of update.missions ?? []) next[missionUpdate.mission_id] = { ...next[missionUpdate.mission_id], ...missionUpdate };
        return next;
      });
    }
  }

  const validation = useMemo(() => {
    if (!missionText.trim()) return [];
    try {
      return validateMission(normalizeMission(JSON.parse(missionText)), agents, mapFeatures);
    } catch (error) {
      return [error instanceof Error ? error.message : "Mission JSON could not be parsed."];
    }
  }, [agents, mapFeatures, missionText]);

  const taskPlan = useMemo(() => (mission ? createTaskPlan(mission, agents, mapFeatures) : undefined), [agents, mapFeatures, mission]);

  function updateMission(next: MissionConfig, focus?: { needle: string; label: string }) {
    activeMissionIdRef.current = next.mission_id;
    setMission(next);
    setMissionConfigs((current) => ({ ...current, [next.mission_id]: next }));
    setMissionState(missionStates[next.mission_id]);
    setMissionText(JSON.stringify(next, null, 2));
    if (focus) setJsonFocus({ ...focus, nonce: Date.now() });
    setCommandFeedback(undefined);
    setInitRequestedAt(undefined);
  }

  function updateMissionText(value: string) {
    setMissionText(value);
    if (!value.trim()) {
      activeMissionIdRef.current = undefined;
      setMission(undefined);
      return;
    }
    try {
      const next = normalizeMission(JSON.parse(value));
      const errors = validateMission(next, agents, mapFeatures);
      if (errors.length === 0) {
        activeMissionIdRef.current = next.mission_id;
        setMission(next);
        setMissionConfigs((current) => ({ ...current, [next.mission_id]: next }));
        setMissionState(missionStates[next.mission_id]);
      }
    } catch {
      // Keep the last valid local mission preview while the user is typing.
    }
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
    setMission(undefined);
    setMissionText("");
    setMissionState(undefined);
    setPlannerState(undefined);
    setCommandFeedback(undefined);
    setInitRequestedAt(undefined);
  }

  function selectMission(missionId: string) {
    const config = missionConfigs[missionId] ?? asMissionConfig(missionStates[missionId]?.config);
    activeMissionIdRef.current = missionId;
    setShowNewMission(false);
    setMissionState(missionStates[missionId]);
    setPlannerState(undefined);
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
    if (activeMissionIdRef.current === missionId) clearMission();
    setCommandFeedback({ tone: "ok", message: "Mission removed from the adapter/UI list. Legacy ROS runtime is unchanged; use Clean Test DB in Diagnostics for test cleanup." });
  }

  async function createDrawnFeature(draft: DraftMapFeature) {
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
      setSelectedFeatureId(featureId);
      setCommandFeedback({ tone: "ok", message: `Updated asset '${name}'.` });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setApiError(message);
      setCommandFeedback({ tone: "error", message: `Asset update failed: ${message}` });
    }
  }

  function setInlineObjective(name: string, geometryType: string, coordinates: unknown, maximizeCoverage = false) {
    const base = mission ?? emptyMission(`Navigate to ${name}`, agents[0]?.agent_id ?? LEGACY_AGENT_ID);
    updateMission(
      {
        ...base,
        mission_id: crypto.randomUUID(),
        name: `Navigate to ${name}`,
        behavior: 0,
        vehicles: base.vehicles.length ? base.vehicles : [agents[0]?.agent_id ?? LEGACY_AGENT_ID],
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
    const base = mission ?? emptyMission(`Mission with ${feature.name}`, agents[0]?.agent_id ?? LEGACY_AGENT_ID);
    const vehicles = base.vehicles.length ? base.vehicles : [agents[0]?.agent_id ?? LEGACY_AGENT_ID];

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
      updateMission(
        {
          ...base,
          vehicles,
          transit: {
            ...base.transit,
            geofence: directGeometryRefFromFeature(feature),
          },
        },
        { needle: '"geofence"', label: "geofence" },
      );
      setCommandFeedback({ tone: "ok", message: `Added '${feature.name}' as mission geofence.` });
    } else if (feature.feature_type === "road" && feature.geometry.type === "LineString") {
      updateMission(
        {
          ...base,
          mission_id: crypto.randomUUID(),
          name: `Patrol ${feature.name}`,
          behavior: 1,
          vehicles,
          transit: {
            ...base.transit,
            optimization: {
              ...((base.transit?.["optimization"] ?? base.transit?.["optimalization"]) as Record<string, unknown> | undefined),
              road_usage: 1,
            },
          },
          objective: {
            ...base.objective,
            geometries: [missionGeometryRefFromFeature(feature)],
            maximize_coverage: true,
          },
        },
        { needle: '"objective"', label: "route objective" },
      );
      setCommandFeedback({ tone: "ok", message: `Added road '${feature.name}' as a route patrol objective.` });
    } else if (feature.feature_type === "risk" && feature.geometry.type === "Polygon") {
      updateMission(
        {
          ...base,
          vehicles,
          objective: {
            ...base.objective,
            line_of_sight: directGeometryRefFromFeature(feature),
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

  async function runCommand(command: "init" | "approve" | "start", action: () => Promise<MissionState>) {
    setApiError("");
    setBusyCommand(command);
    if (command === "init") setInitRequestedAt(Date.now());
    setCommandFeedback({ tone: "warn", message: `${commandLabel(command)} request sent to the adapter...` });
    try {
      const result = await action();
      setMissionState(result);
      setMissionStates((current) => ({ ...current, [result.mission_id]: { ...current[result.mission_id], ...result } }));
      setCommandFeedback({ tone: "ok", message: commandSuccessMessage(command, result) });
      return result;
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setApiError(message);
      setCommandFeedback({ tone: "error", message: `${commandLabel(command)} failed: ${message}` });
      throw error;
    } finally {
      setBusyCommand(undefined);
    }
  }

  async function sendInitMission() {
    await runCommand("init", async () => {
      const next = normalizeMission(JSON.parse(missionText));
      activeMissionIdRef.current = next.mission_id;
      setMission(next);
      setMissionState(undefined);
      setPlannerState(undefined);
      const result = await initMission(next);
      const returnedConfig = asMissionConfig(result.config);
      const updated = returnedConfig ? { ...returnedConfig, mission_id: result.mission_id } : { ...next, mission_id: result.mission_id };
      activeMissionIdRef.current = result.mission_id;
      setMission(updated);
      setMissionText(JSON.stringify(updated, null, 2));
      setMissionConfigs((current) => ({ ...current, [result.mission_id]: updated }));
      return result;
    });
  }

  async function sendApproveMission() {
    if (!mission) return;
    await runCommand("approve", () => approveMission(mission.mission_id));
  }

  async function sendStartMission() {
    if (!mission) return;
    await runCommand("start", () => startMission(mission.mission_id));
  }

  async function refreshLegacyTrace() {
    setLegacyTrace(await getLegacyTrace());
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

  function draftFromAssistant() {
    const firstAgent = agents[0]?.agent_id ?? LEGACY_AGENT_ID;
    const base = mission ?? emptyMission("Draft navigation mission", firstAgent);
    updateMission({
      ...base,
      mission_id: crypto.randomUUID(),
      name: "Draft navigation mission",
      behavior: 0,
      vehicles: [firstAgent],
      transit: {
        geofence: base.transit?.["geofence"],
        optimization: { road_usage: /road/i.test(assistantPrompt) ? 1 : 0.4, energy: 0.8 },
        desired_vehicle_constraints: { max_speed: 4 },
      },
    }, { needle: '"transit"', label: "transit" });
    setShowNewMission(true);
  }

  const hasMission = Boolean(missionText.trim());
  const hasSelectedMission = hasMission || Boolean(missionState);
  const canSendMission = hasMission && validation.length === 0;
  const currentStatus = missionState ? missionStatusLabel(missionState) : "";
  const missionMatchesState = Boolean(mission && missionState?.mission_id === mission.mission_id);
  const canApproveMission = missionMatchesState && ["PLANNED", "PLANNED_ALTERNATIVE"].includes(currentStatus);
  const canStartMission = missionMatchesState && currentStatus === "ACCEPTED";
  const missionList = useMemo(() => {
    const ids = new Set([...Object.keys(missionConfigs), ...Object.keys(missionStates)]);
    return [...ids].filter((missionId) => !hiddenMissionIds.has(missionId)).map((missionId) => ({
      mission_id: missionId,
      config: missionConfigs[missionId] ?? asMissionConfig(missionStates[missionId]?.config),
      state: missionStates[missionId],
    }));
  }, [hiddenMissionIds, missionConfigs, missionStates]);

  return (
    <main className="flex h-screen min-h-[720px] overflow-hidden bg-background text-foreground">
      <MapView
        agents={agents}
        features={mapFeatures}
        geojson={geojson}
        osmRoads={osmRoads}
        mission={mission}
        taskPlan={taskPlan}
        plannerState={plannerState}
        selectedFeatureId={selectedFeatureId}
        onCreateFeature={(feature) => createDrawnFeature(feature).catch((error) => setApiError(String(error)))}
        onUpdateFeature={(featureId, feature) => updateDrawnFeature(featureId, feature).catch((error) => setApiError(String(error)))}
        onRemoveFeature={(feature) => removeFeature(feature).catch((error) => setApiError(String(error)))}
        onSetObjective={setFeatureAsObjective}
        onAddFeatureToMission={addFeatureToMission}
        missionComposerActive={showNewMission}
        onSelectFeature={selectMapFeature}
        onClearSelection={() => setSelectedFeatureId(undefined)}
      />

      <aside className="flex w-[500px] shrink-0 flex-col border-l border-border bg-background">
        <header className="flex h-14 items-center justify-between border-b border-border px-4">
          <div className="flex items-center gap-2">
            <FileJson className="h-5 w-5 text-primary" />
            <div>
              <h2 className="text-sm font-semibold">Mission Definition</h2>
              <p className="text-xs text-muted-foreground">UI to adapter to old REST/ROS.</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {mission && <PlannerProgressTag mission={mission} missionState={missionState} plannerState={plannerState} busyCommand={busyCommand} initRequestedAt={initRequestedAt} nowMs={nowMs} />}
            {!hasSelectedMission ? <Badge>empty</Badge> : !hasMission ? <Badge>runtime</Badge> : validation.length === 0 ? <Badge tone="ok">valid</Badge> : <Badge tone="error">{validation.length} issue{validation.length === 1 ? "" : "s"}</Badge>}
          </div>
        </header>

        <div className="space-y-3 border-b border-border px-4 py-3">
          <div className="flex items-center justify-between">
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
          </div>
          <div className="grid grid-cols-3 gap-2">
            <Button size="sm" variant="outline" onClick={() => sendInitMission().catch(() => undefined)} disabled={!canSendMission || Boolean(busyCommand)}>
              <ShieldCheck className="h-4 w-4" />
              {busyCommand === "init" ? "Initializing" : "Init"}
            </Button>
            <Button size="sm" variant="outline" onClick={() => sendApproveMission().catch(() => undefined)} disabled={!canApproveMission || Boolean(busyCommand)} title={canApproveMission ? "Approve planned mission" : "Wait until the legacy mission status is PLANNED"}>
              <CheckCircle2 className="h-4 w-4" />
              {busyCommand === "approve" ? "Approving" : "Approve"}
            </Button>
            <Button size="sm" onClick={() => sendStartMission().catch(() => undefined)} disabled={!canStartMission || Boolean(busyCommand)} title={canStartMission ? "Start accepted mission" : "Wait until the legacy mission status is ACCEPTED"}>
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

        <section className="min-h-0 flex-1 overflow-auto p-4">
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

          {tab === "assets" && <AssetsPanel agents={agents} mapFeatures={mapFeatures} mission={mission} selectedFeatureId={selectedFeatureId} onSetObjective={setFeatureAsObjective} onRemoveFeature={(feature) => removeFeature(feature).catch((error) => setApiError(String(error)))} />}

          {tab === "diagnostics" && (
            <DiagnosticsPanel
              diagnostics={diagnostics}
              legacyTrace={legacyTrace}
              plannerState={plannerState}
              legacyResetBusy={legacyResetBusy}
              legacyResetResult={legacyResetResult}
              onRefreshLegacyTrace={() => refreshLegacyTrace().catch((error) => setApiError(String(error)))}
              onCleanLegacyRuntime={() => cleanLegacyRuntimeForExamples()}
      />
          )}
        </section>
      </aside>

      <aside className={assistantOpen ? "w-[340px] border-l border-border bg-panel transition-all" : "w-12 border-l border-border bg-panel transition-all"}>
        <button className="flex h-14 w-full items-center justify-center border-b border-border hover:bg-muted" onClick={() => setAssistantOpen((value) => !value)} title="Mission assistant">
          {assistantOpen ? <ChevronRight className="h-5 w-5" /> : <Bot className="h-5 w-5 text-primary" />}
        </button>
        {assistantOpen && (
          <div className="space-y-4 p-4">
            <div>
              <div className="flex items-center gap-2">
                <MessageSquareText className="h-4 w-4 text-primary" />
                <h2 className="text-sm font-semibold">Mission Assistant</h2>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">Local drafting helper. LLM benchmarking comes later.</p>
            </div>
            <Textarea className="h-36 resize-none font-sans text-sm" value={assistantPrompt} onChange={(event) => setAssistantPrompt(event.target.value)} />
            <Button className="w-full" onClick={draftFromAssistant}>
              <Send className="h-4 w-4" />
              Draft Mission
            </Button>
          </div>
        )}
      </aside>
    </main>
  );
}

function PlannerProgressTag({
  mission,
  missionState,
  plannerState,
  busyCommand,
  initRequestedAt,
  nowMs,
}: {
  mission: MissionConfig;
  missionState?: MissionState;
  plannerState?: PlannerUpdateEvent;
  busyCommand?: "init" | "approve" | "start";
  initRequestedAt?: number;
  nowMs: number;
}) {
  const status = missionState ? missionStatusLabel(missionState) : busyCommand === "init" ? "INIT_REQUEST_SENT" : "LOCAL_ONLY";
  const pathSummary = plannerPathSummary(plannerState);
  const startedAt = missionState?.initialized_at ? Date.parse(missionState.initialized_at) : initRequestedAt;
  const elapsedSeconds = startedAt ? Math.max(0, Math.floor((nowMs - startedAt) / 1000)) : 0;
  const progress = plannerProgress(status, missionState?.planner_status, Boolean(pathSummary), busyCommand, missionState?.path_status);
  const isTerminal = ["COMPLETED", "FAILED", "PLANNED_FAILED", "STOPPED", "DELETED"].includes(status);

  return (
    <div className="flex items-center gap-2 rounded-md border border-border bg-panel px-2 py-1 text-xs" title={`${progress.message} ${pathSummary ? `${pathSummary.pathCount} path(s), ${pathSummary.waypointCount} waypoint(s).` : ""}`}>
      {!isTerminal && <Clock className="h-3.5 w-3.5 text-primary" />}
      <Badge tone={progress.tone}>{progress.label}</Badge>
      <span className="text-muted-foreground">{status}</span>
      {startedAt && !isTerminal && <span className="text-muted-foreground">{formatDuration(elapsedSeconds)}</span>}
    </div>
  );
}

function plannerProgress(status: string, plannerStatus: string | undefined, hasPath: boolean, busyCommand?: "init" | "approve" | "start", pathStatus?: string) {
  if (busyCommand === "init") return { tone: "warn" as const, label: "sending", message: "Sending mission_config to the adapter and old REST bridge." };
  if (status === "COMPLETED") return { tone: "ok" as const, label: "completed", message: "Legacy mission feedback reports completion." };
  if (["PLANNED_FAILED", "FAILED"].includes(status) || plannerStatus === "failed") return { tone: "error" as const, label: "failed", message: "Legacy feedback reports planning failure. Open Diagnostics / Legacy Trace for raw ROS state." };
  if (hasPath) return { tone: "ok" as const, label: "path received", message: "A planned path has been received from legacy mission feedback." };
  if (pathStatus === "missing" && ["PLANNED", "PLANNED_ALTERNATIVE"].includes(status)) return { tone: "warn" as const, label: "no path", message: "Legacy mission feedback says planned, but it contains no waypoint Tasks. The planner probably could not resolve the objective." };
  if (["PLANNED", "PLANNED_ALTERNATIVE"].includes(status)) return { tone: "ok" as const, label: "planned", message: "Legacy mission feedback says planning completed. Waiting for normalized path data if none is visible yet." };
  if (status === "STARTED") return { tone: "ok" as const, label: "started", message: "Mission was started. Waiting for edge/autonomy feedback to move the UI marker." };
  if (status === "ACCEPTED") return { tone: "ok" as const, label: "accepted", message: "Plan was approved. Click Start to request execution." };
  if (status === "NONE") return { tone: "warn" as const, label: "planning", message: "Old REST accepted Init. Waiting for /multi_robot/mission_feedback from the legacy planner chain." };
  if (status === "INIT_REQUEST_SENT") return { tone: "warn" as const, label: "init sent", message: "The UI has sent Init; waiting for adapter/REST acknowledgement." };
  return { tone: "default" as const, label: "idle", message: "Load a mission and click Init to begin the legacy planning chain." };
}

function plannerPathSummary(plannerState?: PlannerUpdateEvent) {
  if (plannerState?.path_summary) {
    return { pathCount: plannerState.path_summary.path_count, waypointCount: plannerState.path_summary.waypoint_count };
  }
  if (!plannerState?.paths) return undefined;
  const paths = Object.values(plannerState.paths);
  return { pathCount: paths.length, waypointCount: paths.reduce((sum, path) => sum + path.length, 0) };
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
  return (
    <div className="space-y-3">
      {mission && <MissionSummaryCard mission={mission} state={missionState} />}
      {mission && <MinimalMissionCard mission={mission} />}
      <div className="space-y-2">
        <div className="flex items-center justify-between gap-3">
          <SectionTitle icon={<FileJson className="h-4 w-4" />} label="Full Mission JSON" />
          {jsonFocusLabel && <Badge tone="ok">updated {jsonFocusLabel}</Badge>}
        </div>
        <Textarea ref={missionJsonRef} className="h-[360px] resize-none transition-shadow" value={missionText} onChange={(event) => onMissionTextChange(event.target.value)} spellCheck={false} />
      </div>
      <div className="flex justify-end">
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

function MinimalMissionCard({ mission }: { mission: MissionConfig }) {
  const minimal = minimalMissionPayload(mission);
  const objective = mission.objective.geometries[0];
  const objectiveText = objective?.feature_id
    ? `feature ${objective.feature_id}`
    : objective?.geometry
      ? `${objective.geometry.geometry_type ?? objective.geometry.type ?? "geometry"} ${formatCoordinates(objective.geometry.coordinates)}`
      : "none";
  return (
    <div className="rounded-md border border-border bg-panel p-3">
      <div className="flex items-center justify-between gap-3">
        <SectionTitle icon={<Target className="h-4 w-4" />} label="Minimal Mission" />
        <Badge tone="ok">generated</Badge>
      </div>
      <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
        <div className="rounded-sm border border-border bg-background p-2">
          <div className="font-semibold">Vehicle</div>
          <div className="mt-1 break-all text-muted-foreground">{mission.vehicles[0] ?? "none"}</div>
        </div>
        <div className="rounded-sm border border-border bg-background p-2">
          <div className="font-semibold">Objective</div>
          <div className="mt-1 break-words text-muted-foreground">{objectiveText}</div>
        </div>
      </div>
      <Textarea className="mt-2 h-52 resize-none" value={JSON.stringify(minimal, null, 2)} readOnly spellCheck={false} />
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
  legacyResetBusy,
  legacyResetResult,
  onRefreshLegacyTrace,
  onCleanLegacyRuntime,
}: {
  diagnostics?: DiagnosticsState;
  legacyTrace?: LegacyTrace;
  plannerState?: PlannerUpdateEvent;
  legacyResetBusy: boolean;
  legacyResetResult?: LegacyResetResult;
  onRefreshLegacyTrace: () => void;
  onCleanLegacyRuntime: () => void;
}) {
  if (!diagnostics) return <div className="text-sm text-muted-foreground">Waiting for diagnostics...</div>;
  return (
    <div className="space-y-3">
      <div className="flex justify-end gap-2">
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
  const adjustment = state.adapter_adjustments?.find((item) => item.type === "road_snap");
  const adjustmentText = adjustment ? ` ${adjustment.message ?? "Adapter adjusted the mission before legacy dispatch."}` : "";
  if (command === "init") return `Init accepted by legacy REST. Current status: ${status}. Wait for PLANNED before approving.${adjustmentText}`;
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

function minimalMissionPayload(mission: MissionConfig) {
  return {
    schema_version: mission.schema_version ?? "1.0",
    mission_id: mission.mission_id,
    phase: mission.phase ?? 1,
    name: mission.name ?? "Navigation mission",
    behavior: mission.behavior,
    vehicles: mission.vehicles,
    transit: {
      optimization: mission.transit?.["optimization"] ?? mission.transit?.["optimalization"] ?? { road_usage: 1, energy: 0.8 },
      desired_vehicle_constraints: mission.transit?.["desired_vehicle_constraints"] ?? { max_speed: 4 },
    },
    objective: {
      geometries: mission.objective.geometries,
      maximize_coverage: mission.objective.maximize_coverage ?? false,
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
