import { Bot, Bug, CheckCircle2, ChevronRight, FileJson, Info, ListChecks, MapPinned, MessageSquareText, Play, RefreshCw, Route, Send, Settings2, ShieldCheck, Target, Trash2, XCircle } from "lucide-react";
import type { Feature, FeatureCollection, Geometry } from "geojson";
import type { ReactNode } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  approveMission,
  createMapFeature,
  createEventSource,
  deleteMapFeature,
  getDiagnostics,
  getLegacyTrace,
  getMissionExamples,
  getOsmRoads,
  getRuntimeBootstrap,
  initMission,
  resetLegacyRuntime,
  startMission,
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

export default function App() {
  const [agents, setAgents] = useState<Agent[]>(fallbackAgents);
  const [mapFeatures, setMapFeatures] = useState<MapFeature[]>(fallbackFeatures);
  const [geojson, setGeojson] = useState<FeatureCollection | undefined>();
  const [osmRoads, setOsmRoads] = useState<FeatureCollection | undefined>();
  const [examples, setExamples] = useState<MissionExample[]>(fallbackMissionExamples);
  const [mission, setMission] = useState<MissionConfig | undefined>();
  const [missionText, setMissionText] = useState("");
  const [missionState, setMissionState] = useState<MissionState | undefined>();
  const [diagnostics, setDiagnostics] = useState<DiagnosticsState | undefined>();
  const [legacyTrace, setLegacyTrace] = useState<LegacyTrace | undefined>();
  const [legacyResetResult, setLegacyResetResult] = useState<LegacyResetResult | undefined>();
  const [legacyResetBusy, setLegacyResetBusy] = useState(false);
  const [plannerState, setPlannerState] = useState<PlannerUpdateEvent | undefined>();
  const [apiError, setApiError] = useState("");
  const [commandFeedback, setCommandFeedback] = useState<{ tone: "default" | "ok" | "warn" | "error"; message: string } | undefined>();
  const [busyCommand, setBusyCommand] = useState<"init" | "approve" | "start" | undefined>();
  const [tab, setTab] = useState("mission");
  const [selectedFeatureId, setSelectedFeatureId] = useState<string | undefined>();
  const [assistantOpen, setAssistantOpen] = useState(false);
  const [assistantPrompt, setAssistantPrompt] = useState("Send Themis Fr to the selected objective point using roads.");
  const activeMissionIdRef = useRef<string | undefined>();

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
    getDiagnostics().then(setDiagnostics).catch(() => undefined);

    const source = createEventSource();
    source.addEventListener("diagnostics.updated", (event) => setDiagnostics(JSON.parse((event as MessageEvent).data)));
    source.addEventListener("mission.updated", (event) => {
      const update = JSON.parse((event as MessageEvent).data) as MissionState;
      const activeMissionId = activeMissionIdRef.current;
      if (activeMissionId && update.mission_id !== activeMissionId) return;
      if (!activeMissionId && update.mission_id) return;
      setMissionState(update);
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

  const validation = useMemo(() => {
    if (!missionText.trim()) return [];
    try {
      return validateMission(normalizeMission(JSON.parse(missionText)), agents, mapFeatures);
    } catch (error) {
      return [error instanceof Error ? error.message : "Mission JSON could not be parsed."];
    }
  }, [agents, mapFeatures, missionText]);

  const taskPlan = useMemo(() => (mission ? createTaskPlan(mission, agents, mapFeatures) : undefined), [agents, mapFeatures, mission]);

  function updateMission(next: MissionConfig) {
    activeMissionIdRef.current = next.mission_id;
    setMission(next);
    setMissionText(JSON.stringify(next, null, 2));
    setCommandFeedback(undefined);
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
      }
    } catch {
      // Keep the last valid local mission preview while the user is typing.
    }
  }

  function loadExample(example: MissionExample) {
    const next = { ...example.config, mission_id: crypto.randomUUID() };
    updateMission(next);
    setMissionState(undefined);
    setPlannerState(undefined);
    setTab("mission");
  }

  function clearMission() {
    activeMissionIdRef.current = undefined;
    setMission(undefined);
    setMissionText("");
    setMissionState(undefined);
    setPlannerState(undefined);
    setCommandFeedback(undefined);
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
      setInlineObjective(name, draft.geometry_type, draft.coordinates, draft.geometry_type === "Polygon");
    }
  }

  function setInlineObjective(name: string, geometryType: string, coordinates: unknown, maximizeCoverage = false) {
    const base = mission ?? emptyMission(`Navigate to ${name}`, agents[0]?.agent_id ?? LEGACY_AGENT_ID);
    updateMission({
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
    });
    setMissionState(undefined);
    setPlannerState(undefined);
    setCommandFeedback({ tone: "ok", message: `Mission objective set to '${name}'. Click Init to send a fresh mission to legacy ROS.` });
    setTab("mission");
  }

  function setFeatureAsObjective(feature: MapFeature) {
    const geometryType = feature.geometry.type;
    setSelectedFeatureId(feature.feature_id);
    setInlineObjective(feature.name, geometryType, feature.geometry.coordinates, geometryType === "Polygon" || geometryType === "MultiPolygon");
  }

  function selectFeatureAsObjective(featureId: string) {
    const feature = mapFeatures.find((candidate) => candidate.feature_id === featureId);
    if (!feature) return;
    setFeatureAsObjective(feature);
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
    setCommandFeedback({ tone: "warn", message: `${commandLabel(command)} request sent to the adapter...` });
    try {
      const result = await action();
      setMissionState(result);
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
      const result = await initMission(next);
      if (result.mission_id !== next.mission_id) updateMission({ ...next, mission_id: result.mission_id });
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
    });
  }

  const hasMission = Boolean(missionText.trim());
  const canSendMission = hasMission && validation.length === 0;
  const currentStatus = missionState ? missionStatusLabel(missionState) : "";
  const missionMatchesState = Boolean(mission && missionState?.mission_id === mission.mission_id);
  const canApproveMission = missionMatchesState && ["PLANNED", "PLANNED_ALTERNATIVE"].includes(currentStatus);
  const canStartMission = missionMatchesState && currentStatus === "ACCEPTED";

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
        onSelectFeature={selectFeatureAsObjective}
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
          {!hasMission ? <Badge>empty</Badge> : validation.length === 0 ? <Badge tone="ok">valid</Badge> : <Badge tone="error">{validation.length} issue{validation.length === 1 ? "" : "s"}</Badge>}
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
              validation={validation}
              onLoadExample={loadExample}
              onMissionTextChange={updateMissionText}
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

function MissionPanel({
  examples,
  mission,
  missionText,
  missionState,
  validation,
  onLoadExample,
  onMissionTextChange,
  onClear,
}: {
  examples: MissionExample[];
  mission?: MissionConfig;
  missionText: string;
  missionState?: MissionState;
  validation: string[];
  onLoadExample: (example: MissionExample) => void;
  onMissionTextChange: (value: string) => void;
  onClear: () => void;
}) {
  return (
    <div className="space-y-4">
      <div className="rounded-md border border-border bg-panel p-3">
        <div className="flex items-center gap-2 text-sm font-semibold">
          <Info className="h-4 w-4 text-primary" />
          Command Flow
        </div>
        <div className="mt-2 grid grid-cols-3 gap-2 text-xs text-muted-foreground">
          <Step label="Init" text="POST initialize to old REST" />
          <Step label="Approve" text="Request ACCEPTED" />
          <Step label="Start" text="Request STARTED" />
        </div>
      </div>

      <div className="space-y-2">
        <SectionTitle icon={<ListChecks className="h-4 w-4" />} label="Examples" />
        {examples.map((example) => (
          <button key={example.id} className="w-full rounded-md border border-border bg-panel p-3 text-left hover:bg-muted" onClick={() => onLoadExample(example)}>
            <div className="flex items-center justify-between">
              <div className="font-medium">{example.name}</div>
              <Badge>{example.behavior === 1 ? "coverage" : "navigate"}</Badge>
            </div>
            <div className="mt-1 text-xs text-muted-foreground">{example.vehicles.join(", ")}</div>
          </button>
        ))}
      </div>

      {!missionText.trim() ? (
        <div className="rounded-md border border-border bg-panel p-4 text-sm text-muted-foreground">No mission is loaded. Choose an example above, use the draw tool, or draft one from the side assistant.</div>
      ) : (
        <div className="space-y-3">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>{mission?.mission_id ?? "editing JSON"}</span>
            <span>{missionState ? missionStatusLabel(missionState) : "not initialized"}</span>
          </div>
          {mission && <MinimalMissionCard mission={mission} />}
          <div className="space-y-2">
            <SectionTitle icon={<FileJson className="h-4 w-4" />} label="Full Mission JSON" />
            <Textarea className="h-[300px] resize-none" value={missionText} onChange={(event) => onMissionTextChange(event.target.value)} spellCheck={false} />
          </div>
          <div className="flex justify-end">
            <Button size="sm" variant="ghost" onClick={onClear}>
              Clear Mission
            </Button>
          </div>
          <ValidationList errors={validation} />
        </div>
      )}
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
                <Button size="sm" variant="outline" onClick={() => onSetObjective(feature)} title="Use this feature as the mission objective">
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

function Step({ label, text }: { label: string; text: string }) {
  return (
    <div className="rounded-sm border border-border bg-background p-2">
      <div className="font-semibold text-foreground">{label}</div>
      <div>{text}</div>
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
