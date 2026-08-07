import {
  Activity,
  AlertTriangle,
  Braces,
  Check,
  ChevronLeft,
  ChevronRight,
  Database,
  Eye,
  FileCode2,
  Filter,
  Focus,
  Gauge,
  GitBranch,
  Globe2,
  Layers3,
  Maximize2,
  Network,
  Pause,
  Play,
  RadioTower,
  RefreshCw,
  Search,
  Server,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import {
  Background,
  BackgroundVariant,
  BaseEdge,
  Controls,
  EdgeLabelRenderer,
  Handle,
  MarkerType,
  MiniMap,
  Position,
  ReactFlow,
  ReactFlowProvider,
  getSmoothStepPath,
  useReactFlow,
  useUpdateNodeInternals,
  useViewport,
  type Edge as FlowEdge,
  type EdgeProps,
  type Node as FlowNode,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties, type KeyboardEvent, type ReactNode } from "react";
import type {
  ContractAtlas,
  ContractAtlasComponent,
  ContractAtlasInteraction,
  ContractAtlasWorkflowStep,
  ContractAtlasZone,
  ContractEvidenceRef,
  ContractField,
  ContractGraph,
} from "./api";
import { Badge } from "./components/ui/badge";
import { Button } from "./components/ui/button";

type ContractExplorerProps = {
  graph?: ContractGraph;
  busy: boolean;
  error?: string;
  onRefresh: () => void;
};

type LayoutBox = {
  x: number;
  y: number;
  width: number;
  height: number;
};

type ProtocolToneId = "http" | "ros_topic" | "ros_service" | "in_process" | "data" | "sse";

type ProtocolTone = {
  id: ProtocolToneId;
  label: string;
  shortLabel: string;
  color: string;
  soft: string;
};

type ZoneNodeData = Record<string, unknown> & {
  zone: ContractAtlasZone;
  accent: string;
  legacy: boolean;
};

type ComponentNodeData = Record<string, unknown> & {
  component: ContractAtlasComponent;
  accent: string;
  dimmed: boolean;
  workflowActive: boolean;
  connectionCount: number;
  evidenceKinds: string[];
  ports: FlowPort[];
};

type InteractionEdgeData = Record<string, unknown> & {
  interaction: ContractAtlasInteraction;
  tone: ProtocolTone;
  dimmed: boolean;
  workflowActive: boolean;
  hovered: boolean;
  routeOffset: number;
  pairIndex: number;
  pairCount: number;
};

type FlowPort = {
  id: string;
  type: "source" | "target";
  position: Position;
  offsetPercent: number;
};

type EdgeRoute = {
  sourceHandle: string;
  targetHandle: string;
  pairIndex: number;
  pairCount: number;
};

type RoutingPlan = {
  routes: Map<string, EdgeRoute>;
  portsByComponent: Map<string, FlowPort[]>;
};

type AtlasZoneNode = FlowNode<ZoneNodeData, "zone">;
type AtlasComponentNode = FlowNode<ComponentNodeData, "component">;
type AtlasFlowNode = AtlasZoneNode | AtlasComponentNode;
type AtlasFlowEdge = FlowEdge<InteractionEdgeData, "contract">;

type SelectedPayload =
  | { kind: "component"; component: ContractAtlasComponent }
  | { kind: "interaction"; interaction: ContractAtlasInteraction }
  | undefined;

type SearchResult =
  | { kind: "component"; id: string; label: string; detail: string }
  | { kind: "interaction"; id: string; label: string; detail: string };

const COMPONENT_SIZE = { width: 570, height: 310 };
const SYSTEM_FIT_PADDING = { top: "24px", right: "28px", bottom: "150px", left: "28px" } as const;

// World-space gaps are deliberately wider than the largest near-zoom edge label.
const ZONE_LAYOUT: Record<string, LayoutBox> = {
  operator_ui: { x: 80, y: 690, width: 1680, height: 2840 },
  adapter: { x: 1880, y: 690, width: 1200, height: 2840 },
  legacy_fog: { x: 3250, y: 380, width: 4550, height: 3380 },
  edge_robot: { x: 8000, y: 690, width: 1790, height: 2840 },
  data_observability: { x: 1880, y: 3970, width: 7910, height: 920 },
};

const COMPONENT_LAYOUT: Record<string, { x: number; y: number }> = {
  operator: { x: 190, y: 1570 },
  browser_ui: { x: 1110, y: 1570 },
  fastapi_adapter: { x: 2060, y: 1510 },
  legacy_rest: { x: 3430, y: 1510 },
  c2_interface: { x: 4350, y: 1510 },
  orchestrator: { x: 5270, y: 1510 },
  mission_manager: { x: 6190, y: 1510 },
  planner: { x: 7110, y: 840 },
  fleet_manager: { x: 7110, y: 2220 },
  edge_supervisor: { x: 8180, y: 1510 },
  autonomy_sim: { x: 9100, y: 1510 },
  rosbridge: { x: 2060, y: 4320 },
  mongodb: { x: 5270, y: 4320 },
  map_files: { x: 7645, y: 4320 },
};

const ROUTING_CORRIDORS = {
  adapterLegacyGutterX: (ZONE_LAYOUT.adapter.x + ZONE_LAYOUT.adapter.width + ZONE_LAYOUT.legacy_fog.x) / 2,
  upperReturnY: COMPONENT_LAYOUT.planner.y + COMPONENT_SIZE.height + 120,
  plannerObserveY: ZONE_LAYOUT.data_observability.y - 490,
  missionFeedbackY: ZONE_LAYOUT.data_observability.y - 330,
  edgeFeedbackY: ZONE_LAYOUT.data_observability.y - 210,
};

const ZONE_COLORS: Record<string, string> = {
  operator_ui: "#38bdf8",
  adapter: "#60a5fa",
  legacy_fog: "#f59e0b",
  edge_robot: "#34d399",
  data_observability: "#94a3b8",
};

const PROTOCOL_TONES: Record<ProtocolToneId, ProtocolTone> = {
  http: { id: "http", label: "Command HTTP", shortLabel: "HTTP", color: "#3b82f6", soft: "#93c5fd" },
  ros_topic: { id: "ros_topic", label: "ROS topic", shortLabel: "Topic", color: "#f59e0b", soft: "#fcd34d" },
  ros_service: { id: "ros_service", label: "ROS service", shortLabel: "Service", color: "#14b8a6", soft: "#5eead4" },
  in_process: { id: "in_process", label: "In-process", shortLabel: "Internal", color: "#8b5cf6", soft: "#c4b5fd" },
  data: { id: "data", label: "Data / storage", shortLabel: "Data", color: "#64748b", soft: "#cbd5e1" },
  sse: { id: "sse", label: "SSE / live", shortLabel: "SSE", color: "#06b6d4", soft: "#67e8f9" },
};

const PHASE_ORDER = ["author", "init", "register", "plan", "approve", "start", "execute", "feedback", "complete", "observability", "persistence", "deployment"];

const NODE_TYPES = {
  zone: AtlasZoneCard,
  component: AtlasComponentCard,
};

const EDGE_TYPES = {
  contract: AtlasInteractionEdge,
};

export function ContractExplorer(props: ContractExplorerProps) {
  return (
    <ReactFlowProvider>
      <ContractAtlasWorkspace {...props} />
    </ReactFlowProvider>
  );
}

function ContractAtlasWorkspace({ graph, busy, error, onRefresh }: ContractExplorerProps) {
  const atlas = graph?.atlas;
  const flow = useReactFlow();
  const updateNodeInternals = useUpdateNodeInternals();
  const [query, setQuery] = useState("");
  const [protocolFilters, setProtocolFilters] = useState<Set<ProtocolToneId>>(new Set());
  const [phaseFilters, setPhaseFilters] = useState<Set<string>>(new Set());
  const [selectedComponentId, setSelectedComponentId] = useState<string>();
  const [selectedInteractionId, setSelectedInteractionId] = useState<string>();
  const [hoveredInteractionId, setHoveredInteractionId] = useState<string>();
  const [inspectorOpen, setInspectorOpen] = useState(false);
  const [workflowMode, setWorkflowMode] = useState(false);
  const [workflowIndex, setWorkflowIndex] = useState(0);
  const [workflowPlaying, setWorkflowPlaying] = useState(false);
  const [workflowExpanded, setWorkflowExpanded] = useState(false);
  const initialFitDone = useRef(false);

  const components = atlas?.components ?? [];
  const interactions = atlas?.interactions ?? [];
  const workflowSteps = atlas?.workflow.steps ?? [];
  const currentStep = workflowSteps[clamp(workflowIndex, 0, Math.max(0, workflowSteps.length - 1))];
  const componentById = useMemo(() => new Map(components.map((component) => [component.id, component])), [components]);
  const interactionById = useMemo(() => new Map(interactions.map((interaction) => [interaction.id, interaction])), [interactions]);
  const currentActorIds = useMemo(() => new Set(workflowMode ? currentStep?.actor_ids ?? [] : []), [currentStep, workflowMode]);
  const currentInteractionIds = useMemo(() => new Set(workflowMode ? currentStep?.interaction_ids ?? [] : []), [currentStep, workflowMode]);
  const normalizedQuery = query.trim().toLowerCase();
  const filtering = normalizedQuery.length > 0 || protocolFilters.size > 0 || phaseFilters.size > 0;

  const matchedComponentIds = useMemo(() => {
    if (!normalizedQuery) return new Set(components.map((component) => component.id));
    return new Set(
      components
        .filter((component) =>
          searchableText([
            component.id,
            component.label,
            component.short_label,
            component.kind,
            component.description,
            component.runtime_name,
            component.container,
            ...component.responsibilities,
            ...component.tags,
          ]).includes(normalizedQuery),
        )
        .map((component) => component.id),
    );
  }, [components, normalizedQuery]);

  const matchedInteractionIds = useMemo(() => {
    return new Set(
      interactions
        .filter((interaction) => {
          const tone = protocolTone(interaction);
          const protocolMatch = protocolFilters.size === 0 || protocolFilters.has(tone.id);
          const phaseMatch = phaseFilters.size === 0 || interaction.phases.some((phase) => phaseFilters.has(normalizeToken(phase)));
          const queryMatch =
            !normalizedQuery ||
            matchedComponentIds.has(interaction.source) ||
            matchedComponentIds.has(interaction.target) ||
            searchableText([
              interaction.id,
              interaction.label,
              interaction.channel,
              interaction.protocol,
              interaction.interface,
              interaction.contract,
              interaction.description,
              interaction.direction,
              ...interaction.phases,
              ...interaction.notes,
            ]).includes(normalizedQuery);
          return protocolMatch && phaseMatch && queryMatch;
        })
        .map((interaction) => interaction.id),
    );
  }, [interactions, matchedComponentIds, normalizedQuery, phaseFilters, protocolFilters]);

  const relevantComponentIds = useMemo(() => {
    if (!filtering) return new Set(components.map((component) => component.id));
    const ids = new Set(matchedComponentIds);
    for (const interaction of interactions) {
      if (matchedInteractionIds.has(interaction.id)) {
        ids.add(interaction.source);
        ids.add(interaction.target);
      }
    }
    return ids;
  }, [components, filtering, interactions, matchedComponentIds, matchedInteractionIds]);

  const phaseOptions = useMemo(() => {
    const values = new Set<string>();
    for (const interaction of interactions) {
      for (const phase of interaction.phases) values.add(normalizeToken(phase));
    }
    for (const step of workflowSteps) values.add(normalizeToken(step.phase));
    return [...values].filter(Boolean).sort((left, right) => {
      const leftIndex = PHASE_ORDER.indexOf(left);
      const rightIndex = PHASE_ORDER.indexOf(right);
      return (leftIndex < 0 ? 99 : leftIndex) - (rightIndex < 0 ? 99 : rightIndex) || left.localeCompare(right);
    });
  }, [interactions, workflowSteps]);

  const connectionCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const interaction of interactions) {
      counts.set(interaction.source, (counts.get(interaction.source) ?? 0) + 1);
      counts.set(interaction.target, (counts.get(interaction.target) ?? 0) + 1);
    }
    return counts;
  }, [interactions]);

  const routingPlan = useMemo(() => buildRoutingPlan(interactions), [interactions]);

  useEffect(() => {
    if (!components.length) return;
    const frame = window.requestAnimationFrame(() => updateNodeInternals(components.map((component) => component.id)));
    return () => window.cancelAnimationFrame(frame);
  }, [components, routingPlan, updateNodeInternals]);

  const flowNodes = useMemo<AtlasFlowNode[]>(() => {
    if (!atlas) return [];
    const zoneNodes: AtlasZoneNode[] = atlas.zones.map((zone, index) => {
      const box = ZONE_LAYOUT[zone.id] ?? fallbackZoneBox(index);
      return {
        id: `zone:${zone.id}`,
        type: "zone",
        position: { x: box.x, y: box.y },
        style: { width: box.width, height: box.height },
        selectable: false,
        draggable: false,
        connectable: false,
        deletable: false,
        focusable: false,
        zIndex: -5,
        data: {
          zone,
          accent: ZONE_COLORS[zone.id] ?? zone.tone ?? "#64748b",
          legacy: zone.id === "legacy_fog",
        },
      };
    });

    const zoneMemberIndexes = new Map<string, number>();
    const componentNodes: AtlasComponentNode[] = atlas.components.map((component) => {
      const zoneIndex = zoneMemberIndexes.get(component.zone) ?? 0;
      zoneMemberIndexes.set(component.zone, zoneIndex + 1);
      const position = COMPONENT_LAYOUT[component.id] ?? fallbackComponentPosition(component.zone, zoneIndex);
      const workflowActive = currentActorIds.has(component.id);
      const dimmed = (filtering && !relevantComponentIds.has(component.id)) || (workflowMode && !workflowActive);
      return {
        id: component.id,
        type: "component",
        position,
        style: { width: COMPONENT_SIZE.width, height: COMPONENT_SIZE.height },
        selected: component.id === selectedComponentId,
        draggable: false,
        connectable: false,
        deletable: false,
        zIndex: workflowActive ? 30 : 20,
        ariaLabel: `${component.label}, ${component.description}`,
        data: {
          component,
          accent: ZONE_COLORS[component.zone] ?? "#64748b",
          dimmed,
          workflowActive,
          connectionCount: connectionCounts.get(component.id) ?? 0,
          evidenceKinds: evidenceKinds(component.source_refs),
          ports: routingPlan.portsByComponent.get(component.id) ?? [],
        },
      };
    });
    return [...zoneNodes, ...componentNodes];
  }, [atlas, connectionCounts, currentActorIds, filtering, relevantComponentIds, routingPlan, selectedComponentId, workflowMode]);

  const flowEdges = useMemo<AtlasFlowEdge[]>(() => {
    return interactions.map((interaction) => {
      const tone = protocolTone(interaction);
      const workflowActive = currentInteractionIds.has(interaction.id);
      const filterDimmed = filtering && !matchedInteractionIds.has(interaction.id);
      const storyDimmed = workflowMode && !workflowActive;
      const color = workflowActive ? "#f97316" : tone.color;
      const route = routingPlan.routes.get(interaction.id);
      return {
        id: interaction.id,
        type: "contract",
        source: interaction.source,
        target: interaction.target,
        sourceHandle: route?.sourceHandle,
        targetHandle: route?.targetHandle,
        selected: interaction.id === selectedInteractionId,
        selectable: true,
        focusable: true,
        interactionWidth: 34,
        animated: workflowActive,
        zIndex: workflowActive ? 14 : interaction.id === selectedInteractionId ? 13 : 2,
        markerEnd: {
          type: MarkerType.ArrowClosed,
          width: workflowActive ? 23 : 18,
          height: workflowActive ? 23 : 18,
          color,
        },
        data: {
          interaction,
          tone,
          dimmed: filterDimmed || storyDimmed,
          workflowActive,
          hovered: interaction.id === hoveredInteractionId,
          routeOffset: 52,
          pairIndex: route?.pairIndex ?? 0,
          pairCount: route?.pairCount ?? 1,
        },
      };
    });
  }, [currentInteractionIds, filtering, hoveredInteractionId, interactions, matchedInteractionIds, routingPlan, selectedInteractionId, workflowMode]);

  const selectedPayload = useMemo<SelectedPayload>(() => {
    const interaction = selectedInteractionId ? interactionById.get(selectedInteractionId) : undefined;
    if (interaction) return { kind: "interaction", interaction };
    const component = selectedComponentId ? componentById.get(selectedComponentId) : undefined;
    if (component) return { kind: "component", component };
    return undefined;
  }, [componentById, interactionById, selectedComponentId, selectedInteractionId]);

  const searchResults = useMemo<SearchResult[]>(() => {
    if (!normalizedQuery) return [];
    const results: SearchResult[] = [];
    for (const component of components) {
      if (matchedComponentIds.has(component.id)) {
        results.push({ kind: "component", id: component.id, label: component.label, detail: component.runtime_name ?? component.kind });
      }
    }
    for (const interaction of interactions) {
      if (
        searchableText([interaction.label, interaction.interface, interaction.contract, interaction.protocol, interaction.description]).includes(normalizedQuery)
      ) {
        results.push({
          kind: "interaction",
          id: interaction.id,
          label: interaction.label,
          detail: `${componentById.get(interaction.source)?.short_label ?? interaction.source} → ${componentById.get(interaction.target)?.short_label ?? interaction.target}`,
        });
      }
    }
    return results.slice(0, 9);
  }, [componentById, components, interactions, matchedComponentIds, normalizedQuery]);

  const fitAll = useCallback(
    (duration = 650) => {
      const zones = flow.getNodes().filter((node) => node.type === "zone");
      void flow.fitView({ nodes: zones, padding: SYSTEM_FIT_PADDING, minZoom: 0.07, maxZoom: 0.2, duration });
    },
    [flow],
  );

  const focusIds = useCallback(
    (ids: string[], maxZoom = 0.72) => {
      const idSet = new Set(ids);
      const targets = flow.getNodes().filter((node) => node.type === "component" && idSet.has(node.id));
      if (!targets.length) return;
      void flow.fitView({ nodes: targets, padding: 0.82, minZoom: 0.28, maxZoom, duration: 720 });
    },
    [flow],
  );

  const focusLegacy = useCallback(() => {
    const ids = ["c2_interface", "orchestrator", "mission_manager", "planner", "fleet_manager", "edge_supervisor"];
    focusIds(ids, 0.31);
  }, [focusIds]);

  useEffect(() => {
    if (!atlas || initialFitDone.current) return;
    initialFitDone.current = true;
    const frame = window.requestAnimationFrame(() => fitAll(0));
    return () => window.cancelAnimationFrame(frame);
  }, [atlas, fitAll]);

  useEffect(() => {
    if (!workflowMode || !currentStep) return;
    const timer = window.setTimeout(() => focusIds(currentStep.actor_ids), 80);
    return () => window.clearTimeout(timer);
  }, [currentStep, focusIds, workflowMode]);

  useEffect(() => {
    if (!workflowPlaying || !workflowMode || workflowSteps.length < 2) return;
    const timer = window.setInterval(() => {
      setWorkflowIndex((current) => {
        if (current >= workflowSteps.length - 1) {
          setWorkflowPlaying(false);
          return current;
        }
        return current + 1;
      });
    }, 2800);
    return () => window.clearInterval(timer);
  }, [workflowMode, workflowPlaying, workflowSteps.length]);

  function toggleProtocol(tone: ProtocolToneId) {
    setProtocolFilters((current) => toggleSetValue(current, tone));
  }

  function togglePhase(phase: string) {
    setPhaseFilters((current) => toggleSetValue(current, phase));
  }

  function clearFilters() {
    setQuery("");
    setProtocolFilters(new Set());
    setPhaseFilters(new Set());
  }

  function selectComponent(componentId: string) {
    setSelectedComponentId(componentId);
    setSelectedInteractionId(undefined);
    setInspectorOpen(true);
  }

  function selectInteraction(interactionId: string) {
    setSelectedInteractionId(interactionId);
    setSelectedComponentId(undefined);
    setInspectorOpen(true);
  }

  function focusSearchResult(result: SearchResult) {
    if (result.kind === "component") {
      selectComponent(result.id);
      focusIds([result.id]);
      return;
    }
    const interaction = interactionById.get(result.id);
    if (!interaction) return;
    selectInteraction(result.id);
    focusIds([interaction.source, interaction.target]);
  }

  function handleSearchKey(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter" && searchResults[0]) {
      event.preventDefault();
      focusSearchResult(searchResults[0]);
    }
    if (event.key === "Escape") setQuery("");
  }

  function startWorkflow(index = 0) {
    setWorkflowIndex(clamp(index, 0, Math.max(0, workflowSteps.length - 1)));
    setWorkflowMode(true);
    setWorkflowPlaying(false);
  }

  function exitWorkflow() {
    setWorkflowMode(false);
    setWorkflowPlaying(false);
    window.requestAnimationFrame(() => fitAll());
  }

  function moveWorkflow(delta: number) {
    if (!workflowMode) {
      startWorkflow(delta > 0 ? 0 : Math.max(0, workflowSteps.length - 1));
      return;
    }
    setWorkflowIndex((current) => clamp(current + delta, 0, Math.max(0, workflowSteps.length - 1)));
  }

  if (!atlas) {
    return <AtlasUnavailable busy={busy} error={error} onRefresh={onRefresh} />;
  }

  return (
    <div className="contract-atlas">
      <AtlasToolbar
        atlas={atlas}
        graph={graph}
        busy={busy}
        error={error}
        query={query}
        searchResults={searchResults}
        protocolFilters={protocolFilters}
        phaseFilters={phaseFilters}
        phaseOptions={phaseOptions}
        matchedInteractions={matchedInteractionIds.size}
        onQueryChange={setQuery}
        onSearchKey={handleSearchKey}
        onFocusResult={focusSearchResult}
        onToggleProtocol={toggleProtocol}
        onTogglePhase={togglePhase}
        onClearFilters={clearFilters}
        onFitAll={() => fitAll()}
        onFocusLegacy={focusLegacy}
        onRefresh={onRefresh}
      />

      <div className="contract-atlas__viewport">
        <ReactFlow<AtlasFlowNode, AtlasFlowEdge>
          nodes={flowNodes}
          edges={flowEdges}
          nodeTypes={NODE_TYPES}
          edgeTypes={EDGE_TYPES}
          minZoom={0.07}
          maxZoom={1.85}
          fitView
          fitViewOptions={{ padding: SYSTEM_FIT_PADDING, minZoom: 0.07, maxZoom: 0.2 }}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable
          elevateEdgesOnSelect
          panOnDrag
          panOnScroll
          zoomOnScroll
          zoomOnPinch
          zoomOnDoubleClick
          selectionOnDrag={false}
          onNodeClick={(_, node) => {
            if (node.type === "component") selectComponent(node.id);
          }}
          onEdgeClick={(_, edge) => selectInteraction(edge.id)}
          onEdgeMouseEnter={(_, edge) => setHoveredInteractionId(edge.id)}
          onEdgeMouseLeave={() => setHoveredInteractionId(undefined)}
          onPaneClick={() => {
            setSelectedComponentId(undefined);
            setSelectedInteractionId(undefined);
            setHoveredInteractionId(undefined);
          }}
          proOptions={{ hideAttribution: true }}
          colorMode="dark"
          aria-label="Legacy system contract atlas"
        >
          <Background color="#1f3650" gap={52} size={1.25} variant={BackgroundVariant.Dots} />
          <Controls showInteractive={false} fitViewOptions={{ padding: SYSTEM_FIT_PADDING, minZoom: 0.07, maxZoom: 0.2 }} />
          <MiniMap
            pannable
            zoomable
            nodeStrokeWidth={8}
            maskColor="rgba(3, 10, 20, 0.72)"
            nodeColor={(node) => {
              if (node.type === "zone") return "rgba(30, 52, 74, 0.74)";
              const component = componentById.get(node.id);
              return component?.runtime_status === "visible" ? "#34d399" : ZONE_COLORS[component?.zone ?? ""] ?? "#64748b";
            }}
          />
        </ReactFlow>

        <div className="contract-atlas__orientation" aria-hidden="true">
          <span>COMMAND &amp; INTENT</span>
          <span className="contract-atlas__orientation-line" />
          <span>EXECUTION &amp; FEEDBACK</span>
        </div>

        {inspectorOpen && (
          <AtlasInspector
            atlas={atlas}
            payload={selectedPayload}
            componentById={componentById}
            interactions={interactions}
            onClose={() => setInspectorOpen(false)}
            onSelectComponent={(id) => {
              selectComponent(id);
              focusIds([id]);
            }}
            onSelectInteraction={(id) => {
              selectInteraction(id);
              const interaction = interactionById.get(id);
              if (interaction) focusIds([interaction.source, interaction.target]);
            }}
          />
        )}

        {!inspectorOpen && (
          <button className="contract-atlas__inspector-reopen" type="button" onClick={() => setInspectorOpen(true)}>
            <Eye className="h-4 w-4" />
            Inspector
          </button>
        )}

        <WorkflowDock
          atlas={atlas}
          active={workflowMode}
          playing={workflowPlaying}
          expanded={workflowExpanded}
          currentIndex={workflowIndex}
          currentStep={currentStep}
          onStart={startWorkflow}
          onExit={exitWorkflow}
          onMove={moveWorkflow}
          onSelectStep={startWorkflow}
          onTogglePlaying={() => {
            if (!workflowMode) startWorkflow(0);
            setWorkflowPlaying((current) => !current);
          }}
          onToggleExpanded={() => setWorkflowExpanded((current) => !current)}
        />
      </div>
    </div>
  );
}

function AtlasToolbar({
  atlas,
  graph,
  busy,
  error,
  query,
  searchResults,
  protocolFilters,
  phaseFilters,
  phaseOptions,
  matchedInteractions,
  onQueryChange,
  onSearchKey,
  onFocusResult,
  onToggleProtocol,
  onTogglePhase,
  onClearFilters,
  onFitAll,
  onFocusLegacy,
  onRefresh,
}: {
  atlas: ContractAtlas;
  graph?: ContractGraph;
  busy: boolean;
  error?: string;
  query: string;
  searchResults: SearchResult[];
  protocolFilters: Set<ProtocolToneId>;
  phaseFilters: Set<string>;
  phaseOptions: string[];
  matchedInteractions: number;
  onQueryChange: (value: string) => void;
  onSearchKey: (event: KeyboardEvent<HTMLInputElement>) => void;
  onFocusResult: (result: SearchResult) => void;
  onToggleProtocol: (tone: ProtocolToneId) => void;
  onTogglePhase: (phase: string) => void;
  onClearFilters: () => void;
  onFitAll: () => void;
  onFocusLegacy: () => void;
  onRefresh: () => void;
}) {
  const filtersActive = Boolean(query.trim() || protocolFilters.size || phaseFilters.size);
  return (
    <div className="contract-atlas__toolbar">
      <div className="contract-atlas__toolbar-main">
        <div className="contract-atlas__identity">
          <div className="contract-atlas__identity-icon">
            <Network className="h-5 w-5" />
          </div>
          <div>
            <div className="contract-atlas__identity-title">
              {atlas.title}
              <VerificationPill status={atlas.verification.status} />
            </div>
            <div className="contract-atlas__identity-meta">
              <span>{atlas.components.length} systems</span>
              <span>{atlas.interactions.length} interactions</span>
              <span>{atlas.workflow.steps.length}-step mission trace</span>
              {graph?.source_digest && <span className="font-mono">{graph.source_digest}</span>}
            </div>
          </div>
        </div>

        <div className="contract-atlas__search-wrap">
          <div className="contract-atlas__search">
            <Search className="h-4 w-4" />
            <input
              value={query}
              onChange={(event) => onQueryChange(event.target.value)}
              onKeyDown={onSearchKey}
              placeholder="Find a node, topic, service, field…"
              aria-label="Search contract atlas"
            />
            {query && (
              <button type="button" onClick={() => onQueryChange("")} aria-label="Clear search">
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
          {query.trim() && (
            <div className="contract-atlas__search-results">
              {searchResults.length ? (
                searchResults.map((result) => (
                  <button key={`${result.kind}:${result.id}`} type="button" onClick={() => onFocusResult(result)}>
                    <span className={`contract-atlas__search-kind contract-atlas__search-kind--${result.kind}`}>
                      {result.kind === "component" ? <Server className="h-3.5 w-3.5" /> : <GitBranch className="h-3.5 w-3.5" />}
                    </span>
                    <span className="min-w-0">
                      <strong>{result.label}</strong>
                      <small>{result.detail}</small>
                    </span>
                    <Focus className="ml-auto h-3.5 w-3.5" />
                  </button>
                ))
              ) : (
                <div className="contract-atlas__search-empty">No matching contract</div>
              )}
            </div>
          )}
        </div>

        <div className="contract-atlas__toolbar-actions">
          <span className="contract-atlas__visible-count">{matchedInteractions} visible</span>
          <button type="button" className="contract-atlas__tool-button contract-atlas__tool-button--legacy" onClick={onFocusLegacy}>
            <RadioTower className="h-4 w-4" />
            Legacy core
          </button>
          <button type="button" className="contract-atlas__tool-button" onClick={onFitAll}>
            <Maximize2 className="h-4 w-4" />
            Fit system
          </button>
          <button type="button" className="contract-atlas__tool-button contract-atlas__tool-button--icon" onClick={onRefresh} disabled={busy} title="Refresh verified contract data">
            <RefreshCw className={`h-4 w-4 ${busy ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      <div className="contract-atlas__filter-row">
        <div className="contract-atlas__filter-label">
          <Filter className="h-3.5 w-3.5" />
          Protocol
        </div>
        <div className="contract-atlas__filter-group">
          {Object.values(PROTOCOL_TONES).map((tone) => (
            <button
              key={tone.id}
              type="button"
              className={`contract-atlas__filter-chip ${protocolFilters.has(tone.id) ? "is-active" : ""}`}
              style={{ "--chip-color": tone.color } as CSSProperties}
              onClick={() => onToggleProtocol(tone.id)}
            >
              <span />
              {tone.label}
            </button>
          ))}
        </div>
        <div className="contract-atlas__filter-divider" />
        <div className="contract-atlas__filter-label">
          <Layers3 className="h-3.5 w-3.5" />
          Phase
        </div>
        <div className="contract-atlas__filter-group contract-atlas__filter-group--phases">
          {phaseOptions.map((phase) => (
            <button key={phase} type="button" className={`contract-atlas__phase-chip ${phaseFilters.has(phase) ? "is-active" : ""}`} onClick={() => onTogglePhase(phase)}>
              {prettyToken(phase)}
            </button>
          ))}
        </div>
        {filtersActive && (
          <button type="button" className="contract-atlas__clear-filters" onClick={onClearFilters}>
            Clear
          </button>
        )}
        {error && <span className="contract-atlas__toolbar-error">{error}</span>}
      </div>
    </div>
  );
}

function AtlasZoneCard({ data }: NodeProps<AtlasZoneNode>) {
  return (
    <div
      className={`contract-atlas-zone ${data.legacy ? "contract-atlas-zone--legacy" : ""}`}
      style={{ "--zone-accent": data.accent } as CSSProperties}
    >
      <div className="contract-atlas-zone__heading">
        <span>{data.zone.eyebrow}</span>
        <strong>{data.zone.label}</strong>
        <small>{data.zone.description}</small>
      </div>
      {data.legacy && (
        <div className="contract-atlas-zone__focus">
          <RadioTower className="h-4 w-4" />
          PRIMARY LEGACY RUNTIME
        </div>
      )}
    </div>
  );
}

function AtlasComponentCard({ data, selected }: NodeProps<AtlasComponentNode>) {
  const { zoom } = useViewport();
  const detailLevel = zoom >= 0.67 ? "near" : zoom >= 0.31 ? "mid" : "far";
  const component = data.component;
  return (
    <div
      className={[
        "contract-atlas-component",
        `contract-atlas-component--${detailLevel}`,
        selected ? "is-selected" : "",
        data.dimmed ? "is-dimmed" : "",
        data.workflowActive ? "is-workflow-active" : "",
      ].join(" ")}
      style={{ "--component-accent": data.accent } as CSSProperties}
    >
      <FlowHandles ports={data.ports} />
      <div className="contract-atlas-component__rail" />
      <div className="contract-atlas-component__header">
        <ComponentIcon component={component} />
        <div className="contract-atlas-component__title">
          <span>{prettyToken(component.kind)}</span>
          <strong>{component.short_label ?? component.label}</strong>
          {component.runtime_name && <code>{component.runtime_name}</code>}
        </div>
        <RuntimeDot status={component.runtime_status} />
      </div>
      <div className="contract-atlas-component__far-label">{component.short_label ?? component.label}</div>
      <div className="contract-atlas-component__body">
        <p>{component.description}</p>
        <div className="contract-atlas-component__responsibilities">
          {component.responsibilities.slice(0, detailLevel === "near" ? 3 : 2).map((responsibility) => (
            <span key={responsibility}>{responsibility}</span>
          ))}
        </div>
      </div>
      <div className="contract-atlas-component__footer">
        <div className="contract-atlas-component__tags">
          {component.tags.slice(0, 3).map((tag) => (
            <span key={tag}>{tag}</span>
          ))}
        </div>
        <div className="contract-atlas-component__counts">
          <GitBranch className="h-3.5 w-3.5" />
          {data.connectionCount}
          {data.evidenceKinds.slice(0, 2).map((kind) => (
            <ProvenanceDot key={kind} kind={kind} />
          ))}
        </div>
      </div>
    </div>
  );
}

function AtlasInteractionEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  markerEnd,
  data,
  selected,
}: EdgeProps<AtlasFlowEdge>) {
  const { zoom } = useViewport();
  if (!data) return null;
  const color = data.workflowActive ? "#f97316" : data.tone.color;
  const [path, labelX, labelY] = interactionPath({
    interactionId: data.interaction.id,
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
    routeOffset: data.routeOffset,
  });
  const emphasized = selected || data.workflowActive || data.hovered;
  const showLabel = zoom >= 0.6 || emphasized;
  const showTitle = emphasized || (data.pairCount === 1 && zoom >= 0.86);
  const detailLabel = (zoom >= 1.05 && data.pairCount === 1) || selected || data.workflowActive;
  return (
    <>
      <BaseEdge
        id={id}
        path={path}
        markerEnd={markerEnd}
        interactionWidth={34}
        style={{
          stroke: color,
          strokeWidth: data.workflowActive ? 6 : selected || data.hovered ? 4.5 : 3.25,
          opacity: data.dimmed ? 0.075 : emphasized ? 1 : 0.68,
          filter: data.workflowActive ? "drop-shadow(0 0 13px rgba(249,115,22,.9))" : selected ? `drop-shadow(0 0 8px ${color})` : undefined,
        }}
      />
      {showLabel && !data.dimmed && (
        <EdgeLabelRenderer>
          <div
            className={[
              "contract-atlas-edge-label",
              !showTitle ? "is-tone-only" : "",
              data.pairCount > 1 ? "is-bundled" : "",
              selected ? "is-selected" : "",
              data.workflowActive ? "is-workflow-active" : "",
            ].join(" ")}
            style={{
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
              "--edge-color": color,
              zIndex: data.workflowActive ? 16 : selected || data.hovered ? 15 : 4,
            } as CSSProperties}
          >
            <span>
              {data.tone.shortLabel}
              {data.pairCount > 1 ? ` ${data.pairIndex + 1}/${data.pairCount}` : ""}
            </span>
            {showTitle && <strong>{data.interaction.label}</strong>}
            {detailLabel && (data.interaction.interface || data.interaction.contract) && (
              <code>{data.interaction.interface ?? data.interaction.contract}</code>
            )}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}

function AtlasInspector({
  atlas,
  payload,
  componentById,
  interactions,
  onClose,
  onSelectComponent,
  onSelectInteraction,
}: {
  atlas: ContractAtlas;
  payload: SelectedPayload;
  componentById: Map<string, ContractAtlasComponent>;
  interactions: ContractAtlasInteraction[];
  onClose: () => void;
  onSelectComponent: (id: string) => void;
  onSelectInteraction: (id: string) => void;
}) {
  return (
    <aside className="contract-atlas-inspector">
      <div className="contract-atlas-inspector__topbar">
        <span>
          <Eye className="h-4 w-4" />
          Contract inspector
        </span>
        <button type="button" onClick={onClose} aria-label="Close inspector">
          <X className="h-4 w-4" />
        </button>
      </div>
      {payload?.kind === "component" ? (
        <ComponentInspector
          component={payload.component}
          interactions={interactions}
          componentById={componentById}
          onSelectInteraction={onSelectInteraction}
        />
      ) : payload?.kind === "interaction" ? (
        <InteractionInspector interaction={payload.interaction} componentById={componentById} onSelectComponent={onSelectComponent} />
      ) : (
        <AtlasOverviewInspector atlas={atlas} />
      )}
    </aside>
  );
}

function ComponentInspector({
  component,
  interactions,
  componentById,
  onSelectInteraction,
}: {
  component: ContractAtlasComponent;
  interactions: ContractAtlasInteraction[];
  componentById: Map<string, ContractAtlasComponent>;
  onSelectInteraction: (id: string) => void;
}) {
  const related = interactions.filter((interaction) => interaction.source === component.id || interaction.target === component.id);
  return (
    <div className="contract-atlas-inspector__content">
      <InspectorHero
        icon={<ComponentIcon component={component} />}
        eyebrow={`${prettyToken(component.kind)} · ${prettyToken(component.zone)}`}
        title={component.label}
        description={component.description}
        runtimeStatus={component.runtime_status}
      />
      {component.runtime_name && <InspectorValue label="Runtime identity" value={component.runtime_name} mono />}
      {component.container && <InspectorValue label="Container" value={component.container} mono />}
      <InspectorSection icon={<Gauge className="h-4 w-4" />} title="Responsibilities">
        <div className="contract-atlas-inspector__bullet-list">
          {component.responsibilities.map((responsibility) => (
            <div key={responsibility}>
              <Check className="h-3.5 w-3.5" />
              {responsibility}
            </div>
          ))}
        </div>
      </InspectorSection>
      <InspectorSection icon={<GitBranch className="h-4 w-4" />} title={`Interactions · ${related.length}`}>
        <div className="contract-atlas-inspector__connections">
          {related.map((interaction) => {
            const outgoing = interaction.source === component.id;
            const peerId = outgoing ? interaction.target : interaction.source;
            const tone = protocolTone(interaction);
            return (
              <button key={interaction.id} type="button" onClick={() => onSelectInteraction(interaction.id)}>
                <span className="contract-atlas-inspector__connection-dot" style={{ background: tone.color }} />
                <span className="min-w-0">
                  <strong>{interaction.label}</strong>
                  <small>
                    {outgoing ? "to" : "from"} {componentById.get(peerId)?.short_label ?? peerId} · {tone.shortLabel}
                  </small>
                </span>
                <ChevronRight className="ml-auto h-4 w-4" />
              </button>
            );
          })}
        </div>
      </InspectorSection>
      {component.tags.length > 0 && (
        <InspectorSection icon={<Layers3 className="h-4 w-4" />} title="Tags">
          <div className="contract-atlas-inspector__tags">
            {component.tags.map((tag) => (
              <span key={tag}>{tag}</span>
            ))}
          </div>
        </InspectorSection>
      )}
      <EvidenceList refs={component.source_refs} />
    </div>
  );
}

function InteractionInspector({
  interaction,
  componentById,
  onSelectComponent,
}: {
  interaction: ContractAtlasInteraction;
  componentById: Map<string, ContractAtlasComponent>;
  onSelectComponent: (id: string) => void;
}) {
  const tone = protocolTone(interaction);
  const fields = interaction.fields ?? [];
  const requestFields = interaction.request_fields ?? [];
  const responseFields = interaction.response_fields ?? [];
  return (
    <div className="contract-atlas-inspector__content">
      <InspectorHero
        icon={<GitBranch className="h-5 w-5" style={{ color: tone.color }} />}
        eyebrow={`${tone.label} · ${interaction.phases.map(prettyToken).join(" / ")}`}
        title={interaction.label}
        description={interaction.description}
        runtimeStatus={interaction.runtime_status}
      />
      <div className="contract-atlas-inspector__actors">
        <ActorButton label="Source" component={componentById.get(interaction.source)} fallback={interaction.source} onClick={() => onSelectComponent(interaction.source)} />
        <div className="contract-atlas-inspector__actor-arrow" style={{ color: tone.color }}>
          <ChevronRight className="h-5 w-5" />
        </div>
        <ActorButton label="Target" component={componentById.get(interaction.target)} fallback={interaction.target} onClick={() => onSelectComponent(interaction.target)} />
      </div>
      <div className="contract-atlas-inspector__value-grid">
        <InspectorValue label="Channel" value={interaction.channel} />
        <InspectorValue label="Protocol" value={interaction.protocol} />
        {interaction.interface && <InspectorValue label="Interface" value={interaction.interface} mono />}
        {interaction.contract && <InspectorValue label="Payload contract" value={interaction.contract} mono />}
        {interaction.direction && <InspectorValue label="Direction" value={interaction.direction} />}
      </div>
      {requestFields.length > 0 && <FieldList title="Request fields" fields={requestFields} />}
      {responseFields.length > 0 && <FieldList title="Response fields" fields={responseFields} />}
      {fields.length > 0 && <FieldList title="Payload fields" fields={fields} />}
      {interaction.notes.length > 0 && (
        <InspectorSection icon={<AlertTriangle className="h-4 w-4" />} title="Contract notes">
          <div className="contract-atlas-inspector__notes">
            {interaction.notes.map((note) => (
              <div key={note}>{note}</div>
            ))}
          </div>
        </InspectorSection>
      )}
      <EvidenceList refs={interaction.source_refs} />
    </div>
  );
}

function AtlasOverviewInspector({ atlas }: { atlas: ContractAtlas }) {
  return (
    <div className="contract-atlas-inspector__content">
      <InspectorHero
        icon={<ShieldCheck className="h-5 w-5 text-emerald-300" />}
        eyebrow="Evidence-backed system model"
        title="How to read this atlas"
        description={atlas.scope}
      />
      <div className="contract-atlas-inspector__overview-stats">
        <div>
          <strong>{atlas.components.length}</strong>
          <span>systems</span>
        </div>
        <div>
          <strong>{atlas.interactions.length}</strong>
          <span>contracts</span>
        </div>
        <div>
          <strong>{atlas.verification.source_evidence_count}</strong>
          <span>source proofs</span>
        </div>
      </div>
      <InspectorValue label="Verification method" value={atlas.verification.method} />
      <InspectorValue label="Runtime observation" value={atlas.verification.runtime_status} />
      <InspectorSection icon={<Activity className="h-4 w-4" />} title="Explore">
        <div className="contract-atlas-inspector__bullet-list">
          <div>
            <Check className="h-3.5 w-3.5" />
            Zoom into a system to reveal responsibilities and evidence.
          </div>
          <div>
            <Check className="h-3.5 w-3.5" />
            Select any line to inspect its exact protocol, contract and fields.
          </div>
          <div>
            <Check className="h-3.5 w-3.5" />
            Start the mission trace below to follow data through all 15 stages.
          </div>
        </div>
      </InspectorSection>
      {atlas.contract_gaps.length > 0 && (
        <InspectorSection icon={<AlertTriangle className="h-4 w-4" />} title={`Known contract gaps · ${atlas.contract_gaps.length}`}>
          <div className="contract-atlas-inspector__gaps">
            {atlas.contract_gaps.map((gap) => (
              <div key={gap.id} data-severity={gap.severity}>
                <span>{prettyToken(gap.severity)}</span>
                <strong>{gap.title}</strong>
                <p>{gap.description}</p>
              </div>
            ))}
          </div>
        </InspectorSection>
      )}
      {atlas.verification.caveats.length > 0 && (
        <InspectorSection icon={<AlertTriangle className="h-4 w-4" />} title="Verification caveats">
          <div className="contract-atlas-inspector__notes">
            {atlas.verification.caveats.map((caveat) => (
              <div key={caveat}>{caveat}</div>
            ))}
          </div>
        </InspectorSection>
      )}
    </div>
  );
}

function WorkflowDock({
  atlas,
  active,
  playing,
  expanded,
  currentIndex,
  currentStep,
  onStart,
  onExit,
  onMove,
  onSelectStep,
  onTogglePlaying,
  onToggleExpanded,
}: {
  atlas: ContractAtlas;
  active: boolean;
  playing: boolean;
  expanded: boolean;
  currentIndex: number;
  currentStep?: ContractAtlasWorkflowStep;
  onStart: (index?: number) => void;
  onExit: () => void;
  onMove: (delta: number) => void;
  onSelectStep: (index: number) => void;
  onTogglePlaying: () => void;
  onToggleExpanded: () => void;
}) {
  const steps = atlas.workflow.steps;
  if (!active) {
    return (
      <div className="contract-atlas-workflow contract-atlas-workflow--intro">
        <div className="contract-atlas-workflow__intro-icon">
          <Sparkles className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <span>GUIDED DATA TRACE</span>
          <strong>{atlas.workflow.label}</strong>
          <p>{atlas.workflow.summary}</p>
        </div>
        <button type="button" className="contract-atlas-workflow__start" onClick={() => onStart(0)}>
          <Play className="h-4 w-4 fill-current" />
          Walk the {steps.length} steps
        </button>
      </div>
    );
  }
  if (!currentStep) return null;
  return (
    <div className={`contract-atlas-workflow contract-atlas-workflow--active ${expanded ? "is-expanded" : ""}`}>
      <div className="contract-atlas-workflow__controls">
        <button type="button" onClick={() => onMove(-1)} disabled={currentIndex === 0} aria-label="Previous workflow step">
          <ChevronLeft className="h-5 w-5" />
        </button>
        <button type="button" className="contract-atlas-workflow__play" onClick={onTogglePlaying} aria-label={playing ? "Pause workflow" : "Play workflow"}>
          {playing ? <Pause className="h-4 w-4 fill-current" /> : <Play className="h-4 w-4 fill-current" />}
        </button>
        <button type="button" onClick={() => onMove(1)} disabled={currentIndex >= steps.length - 1} aria-label="Next workflow step">
          <ChevronRight className="h-5 w-5" />
        </button>
      </div>
      <div className="contract-atlas-workflow__story">
        <div className="contract-atlas-workflow__step-meta">
          <span>
            STEP {currentStep.number} / {steps.length}
          </span>
          <b>{prettyToken(currentStep.phase)}</b>
          <button type="button" onClick={onToggleExpanded}>
            {expanded ? "Hide payload" : "Show payload"}
          </button>
        </div>
        <strong>{currentStep.title}</strong>
        <p>{currentStep.summary}</p>
        {currentStep.transformations.length > 0 && (
          <div className="contract-atlas-workflow__transforms">
            {currentStep.transformations.slice(0, expanded ? 6 : 2).map((transformation) => (
              <span key={transformation}>{transformation}</span>
            ))}
          </div>
        )}
        {expanded && (
          <div className="contract-atlas-workflow__payloads">
            <PayloadPreview label="Input" value={currentStep.input} />
            <div className="contract-atlas-workflow__payload-arrow">
              <ChevronRight className="h-5 w-5" />
            </div>
            <PayloadPreview label="Output" value={currentStep.output} />
          </div>
        )}
      </div>
      <div className="contract-atlas-workflow__timeline" aria-label="Workflow steps">
        {steps.map((step, index) => (
          <button
            key={step.id}
            type="button"
            className={`${index === currentIndex ? "is-current" : ""} ${index < currentIndex ? "is-complete" : ""}`}
            onClick={() => onSelectStep(index)}
            title={`${step.number}. ${step.title}`}
          >
            {index < currentIndex ? <Check className="h-3 w-3" /> : step.number}
          </button>
        ))}
      </div>
      <button type="button" className="contract-atlas-workflow__exit" onClick={onExit}>
        <X className="h-4 w-4" />
        Exit trace
      </button>
    </div>
  );
}

function AtlasUnavailable({ busy, error, onRefresh }: { busy: boolean; error?: string; onRefresh: () => void }) {
  return (
    <div className="contract-atlas contract-atlas--unavailable">
      <div className="contract-atlas__unavailable-card">
        <div className="contract-atlas__identity-icon">
          <Network className="h-6 w-6" />
        </div>
        <span>SYSTEM CONTRACT ATLAS</span>
        <h2>{busy ? "Building the verified system map…" : "Contract atlas unavailable"}</h2>
        <p>{error || "The backend did not return the verified atlas model. Refresh after the adapter is ready."}</p>
        <Button type="button" variant="outline" onClick={onRefresh} disabled={busy}>
          <RefreshCw className={`h-4 w-4 ${busy ? "animate-spin" : ""}`} />
          {busy ? "Building atlas" : "Refresh atlas"}
        </Button>
      </div>
    </div>
  );
}

function FlowHandles({ ports }: { ports: FlowPort[] }) {
  return (
    <>
      {ports.map((port) => {
        const verticalSide = port.position === Position.Left || port.position === Position.Right;
        return (
          <Handle
            key={port.id}
            id={port.id}
            type={port.type}
            position={port.position}
            className="contract-atlas-handle"
            style={verticalSide ? { top: `${port.offsetPercent}%` } : { left: `${port.offsetPercent}%` }}
          />
        );
      })}
    </>
  );
}

function ComponentIcon({ component }: { component: ContractAtlasComponent }) {
  const normalized = `${component.id} ${component.kind} ${component.tags.join(" ")}`.toLowerCase();
  const className = "h-5 w-5";
  if (normalized.includes("operator") || normalized.includes("browser") || normalized.includes("ui")) return <Globe2 className={className} />;
  if (normalized.includes("mongo") || normalized.includes("data")) return <Database className={className} />;
  if (normalized.includes("ros") || normalized.includes("edge") || normalized.includes("autonomy")) return <RadioTower className={className} />;
  if (normalized.includes("planner") || normalized.includes("mission")) return <Network className={className} />;
  return <Server className={className} />;
}

function InspectorHero({
  icon,
  eyebrow,
  title,
  description,
  runtimeStatus,
}: {
  icon: ReactNode;
  eyebrow: string;
  title: string;
  description: string;
  runtimeStatus?: string;
}) {
  return (
    <div className="contract-atlas-inspector__hero">
      <div className="contract-atlas-inspector__hero-icon">{icon}</div>
      <div className="min-w-0">
        <span>{eyebrow}</span>
        <h3>{title}</h3>
        <p>{description}</p>
        {runtimeStatus && <RuntimePill status={runtimeStatus} />}
      </div>
    </div>
  );
}

function InspectorSection({ icon, title, children }: { icon: ReactNode; title: string; children: ReactNode }) {
  return (
    <section className="contract-atlas-inspector__section">
      <h4>
        {icon}
        {title}
      </h4>
      {children}
    </section>
  );
}

function InspectorValue({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="contract-atlas-inspector__value">
      <span>{label}</span>
      <strong className={mono ? "font-mono" : ""}>{value}</strong>
    </div>
  );
}

function ActorButton({
  label,
  component,
  fallback,
  onClick,
}: {
  label: string;
  component?: ContractAtlasComponent;
  fallback: string;
  onClick: () => void;
}) {
  return (
    <button type="button" onClick={onClick}>
      <span>{label}</span>
      <strong>{component?.short_label ?? component?.label ?? fallback}</strong>
    </button>
  );
}

function FieldList({ title, fields }: { title: string; fields: ContractField[] }) {
  return (
    <InspectorSection icon={<Braces className="h-4 w-4" />} title={`${title} · ${fields.length}`}>
      <div className="contract-atlas-inspector__fields">
        {fields.map((field, index) => (
          <div key={`${field.section}:${field.name}:${index}`}>
            <span>{field.section ?? "field"}</span>
            <code>{field.type ?? "unknown"}</code>
            <strong>{field.name}</strong>
          </div>
        ))}
      </div>
    </InspectorSection>
  );
}

function EvidenceList({ refs }: { refs: ContractEvidenceRef[] }) {
  const unique = uniqueEvidence(refs);
  if (!unique.length) return null;
  return (
    <InspectorSection icon={<FileCode2 className="h-4 w-4" />} title={`Evidence · ${unique.length}`}>
      <div className="contract-atlas-inspector__evidence">
        {unique.map((ref) => (
          <div key={`${ref.path}:${ref.line}:${ref.symbol ?? ""}`}>
            <div>
              <ProvenancePill kind={ref.verification ?? "source"} />
              {ref.symbol && <code>{ref.symbol}</code>}
            </div>
            <strong className="font-mono">
              {ref.path}:{ref.line}
            </strong>
            {ref.claim && <p>{ref.claim}</p>}
          </div>
        ))}
      </div>
    </InspectorSection>
  );
}

function PayloadPreview({ label, value }: { label: string; value: unknown }) {
  return (
    <div>
      <span>{label}</span>
      <pre>{value === undefined ? "—" : JSON.stringify(value, null, 2)}</pre>
    </div>
  );
}

function RuntimeDot({ status }: { status?: string }) {
  return <span className={`contract-atlas-runtime-dot contract-atlas-runtime-dot--${status ?? "not_checked"}`} title={`Runtime: ${prettyToken(status ?? "not checked")}`} />;
}

function RuntimePill({ status }: { status: string }) {
  return (
    <span className={`contract-atlas-runtime-pill contract-atlas-runtime-pill--${status}`}>
      <Activity className="h-3 w-3" />
      Runtime {prettyToken(status)}
    </span>
  );
}

function VerificationPill({ status }: { status: string }) {
  const normalized = normalizeToken(status);
  return (
    <span className={`contract-atlas-verification contract-atlas-verification--${normalized}`}>
      <ShieldCheck className="h-3.5 w-3.5" />
      {prettyToken(status)}
    </span>
  );
}

function ProvenancePill({ kind }: { kind: string }) {
  return <span className={`contract-atlas-provenance contract-atlas-provenance--${normalizeToken(kind)}`}>{prettyToken(kind)}</span>;
}

function ProvenanceDot({ kind }: { kind: string }) {
  return <span className={`contract-atlas-provenance-dot contract-atlas-provenance-dot--${normalizeToken(kind)}`} title={`Evidence: ${prettyToken(kind)}`} />;
}

function protocolTone(interaction: ContractAtlasInteraction): ProtocolTone {
  const value = `${interaction.channel} ${interaction.protocol}`.toLowerCase();
  if (value.includes("sse") || value.includes("event stream") || value.includes("websocket") || value.includes("rosbridge")) return PROTOCOL_TONES.sse;
  if (value.includes("http") || value.includes("rest")) return PROTOCOL_TONES.http;
  if (value.includes("topic") || value.includes("publish") || value.includes("subscribe")) return PROTOCOL_TONES.ros_topic;
  if (value.includes("service") || value.includes("srv") || value.includes("request/response")) return PROTOCOL_TONES.ros_service;
  if (value.includes("in-process") || value.includes("in_process") || value.includes("memory") || value.includes("timer") || value.includes("human interaction")) return PROTOCOL_TONES.in_process;
  return PROTOCOL_TONES.data;
}

// These long return/data routes need obstacle-free buses; a generic SmoothStep cuts through cards.
const ROUTE_POSITION_OVERRIDES: Record<string, { source: Position; target: Position }> = {
  planner_map: { source: Position.Top, target: Position.Right },
  planner_state_observe: { source: Position.Left, target: Position.Top },
  mission_feedback_topic: { source: Position.Bottom, target: Position.Top },
  edge_feedback_observe: { source: Position.Bottom, target: Position.Top },
  mission_status_response: { source: Position.Top, target: Position.Top },
};

type RouteEndpoint = {
  componentId: string;
  interactionId: string;
  oppositeId: string;
  role: "source" | "target";
  position: Position;
  order: number;
};

function buildRoutingPlan(interactions: ContractAtlasInteraction[]): RoutingPlan {
  const routes = new Map<string, EdgeRoute>();
  const portsByComponent = new Map<string, FlowPort[]>();
  const endpointsBySide = new Map<string, RouteEndpoint[]>();
  const pairMembers = new Map<string, ContractAtlasInteraction[]>();
  const stableOrder = new Map(
    [...interactions]
      .sort((left, right) => left.id.localeCompare(right.id))
      .map((interaction, index) => [interaction.id, index]),
  );

  interactions.forEach((interaction) => {
    const key = interactionPairKey(interaction);
    const members = pairMembers.get(key) ?? [];
    members.push(interaction);
    pairMembers.set(key, members);
  });
  for (const members of pairMembers.values()) members.sort((left, right) => left.id.localeCompare(right.id));

  interactions.forEach((interaction) => {
    const pair = pairMembers.get(interactionPairKey(interaction)) ?? [interaction];
    const pairIndex = pair.findIndex((member) => member.id === interaction.id);
    const positions = handlePositionsForInteraction(interaction);
    routes.set(interaction.id, {
      sourceHandle: "",
      targetHandle: "",
      pairIndex: Math.max(0, pairIndex),
      pairCount: pair.length,
    });

    const endpoints: RouteEndpoint[] = [
      {
        componentId: interaction.source,
        interactionId: interaction.id,
        oppositeId: interaction.target,
        role: "source",
        position: positions.source,
        order: stableOrder.get(interaction.id) ?? 0,
      },
      {
        componentId: interaction.target,
        interactionId: interaction.id,
        oppositeId: interaction.source,
        role: "target",
        position: positions.target,
        order: stableOrder.get(interaction.id) ?? 0,
      },
    ];

    for (const endpoint of endpoints) {
      const key = `${endpoint.componentId}:${endpoint.position}`;
      const group = endpointsBySide.get(key) ?? [];
      group.push(endpoint);
      endpointsBySide.set(key, group);
    }
  });

  for (const endpoints of endpointsBySide.values()) {
    endpoints.sort((left, right) => {
      const leftPeer = COMPONENT_LAYOUT[left.oppositeId];
      const rightPeer = COMPONENT_LAYOUT[right.oppositeId];
      const verticalSide = left.position === Position.Left || left.position === Position.Right;
      const leftCoordinate = verticalSide ? leftPeer?.y ?? 0 : leftPeer?.x ?? 0;
      const rightCoordinate = verticalSide ? rightPeer?.y ?? 0 : rightPeer?.x ?? 0;
      return leftCoordinate - rightCoordinate || left.order - right.order || left.interactionId.localeCompare(right.interactionId);
    });

    endpoints.forEach((endpoint, index) => {
      const offsetPercent = ((index + 1) / (endpoints.length + 1)) * 100;
      const handleId = `${endpoint.role === "source" ? "s" : "t"}-${endpoint.position}-${endpoint.interactionId}`;
      const route = routes.get(endpoint.interactionId);
      if (route) {
        if (endpoint.role === "source") route.sourceHandle = handleId;
        else route.targetHandle = handleId;
      }
      const ports = portsByComponent.get(endpoint.componentId) ?? [];
      ports.push({ id: handleId, type: endpoint.role, position: endpoint.position, offsetPercent });
      portsByComponent.set(endpoint.componentId, ports);
    });
  }

  return { routes, portsByComponent };
}

function interactionPairKey(interaction: ContractAtlasInteraction) {
  return [interaction.source, interaction.target].sort().join("::");
}

function handlePositionsForInteraction(interaction: ContractAtlasInteraction) {
  const override = ROUTE_POSITION_OVERRIDES[interaction.id];
  if (override) return override;
  const source = COMPONENT_LAYOUT[interaction.source];
  const target = COMPONENT_LAYOUT[interaction.target];
  if (!source || !target) return { source: Position.Right, target: Position.Left };
  const deltaX = target.x - source.x;
  const deltaY = target.y - source.y;
  if (Math.abs(deltaY) > Math.abs(deltaX) * 0.78) {
    return deltaY >= 0 ? { source: Position.Bottom, target: Position.Top } : { source: Position.Top, target: Position.Bottom };
  }
  return deltaX >= 0 ? { source: Position.Right, target: Position.Left } : { source: Position.Left, target: Position.Right };
}

type InteractionPathOptions = {
  interactionId: string;
  sourceX: number;
  sourceY: number;
  targetX: number;
  targetY: number;
  sourcePosition: Position;
  targetPosition: Position;
  routeOffset: number;
};

type RoutePoint = { x: number; y: number };

function interactionPath(options: InteractionPathOptions): [string, number, number] {
  const { interactionId, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, routeOffset } = options;
  const source = { x: sourceX, y: sourceY };
  const target = { x: targetX, y: targetY };
  const manualPoints: Record<string, RoutePoint[]> = {
    planner_map: [source, { x: sourceX, y: targetY }, target],
    planner_state_observe: [
      source,
      { x: ROUTING_CORRIDORS.adapterLegacyGutterX, y: sourceY },
      { x: ROUTING_CORRIDORS.adapterLegacyGutterX, y: ROUTING_CORRIDORS.plannerObserveY },
      { x: targetX, y: ROUTING_CORRIDORS.plannerObserveY },
      target,
    ],
    mission_feedback_topic: [
      source,
      { x: sourceX, y: ROUTING_CORRIDORS.missionFeedbackY },
      { x: targetX, y: ROUTING_CORRIDORS.missionFeedbackY },
      target,
    ],
    edge_feedback_observe: [
      source,
      { x: sourceX, y: ROUTING_CORRIDORS.edgeFeedbackY },
      { x: targetX, y: ROUTING_CORRIDORS.edgeFeedbackY },
      target,
    ],
    mission_status_response: [
      source,
      { x: sourceX, y: ROUTING_CORRIDORS.upperReturnY },
      { x: targetX, y: ROUTING_CORRIDORS.upperReturnY },
      target,
    ],
  };
  const points = manualPoints[interactionId];
  if (points) return roundedOrthogonalPath(points, 24);
  const [path, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
    borderRadius: 24,
    offset: routeOffset,
  });
  return [path, labelX, labelY];
}

function roundedOrthogonalPath(rawPoints: RoutePoint[], radius: number): [string, number, number] {
  const points: RoutePoint[] = [];
  for (const point of rawPoints) {
    const previous = points[points.length - 1];
    if (previous && previous.x === point.x && previous.y === point.y) continue;
    const beforePrevious = points[points.length - 2];
    if (beforePrevious && previous) {
      const collinear =
        (beforePrevious.x === previous.x && previous.x === point.x) ||
        (beforePrevious.y === previous.y && previous.y === point.y);
      if (collinear) points.pop();
    }
    points.push(point);
  }

  if (points.length < 2) {
    const point = points[0] ?? { x: 0, y: 0 };
    return [`M${point.x} ${point.y}`, point.x, point.y];
  }

  let path = `M${points[0].x} ${points[0].y}`;
  for (let index = 1; index < points.length - 1; index += 1) {
    path += roundedCorner(points[index - 1], points[index], points[index + 1], radius);
  }
  const last = points[points.length - 1];
  path += `L${last.x} ${last.y}`;

  const segments = points.slice(0, -1).map((start, index) => {
    const end = points[index + 1];
    return {
      start,
      end,
      horizontal: start.y === end.y,
      length: Math.abs(end.x - start.x) + Math.abs(end.y - start.y),
    };
  });
  const horizontalSegments = segments.filter((segment) => segment.horizontal && segment.length >= 160);
  const labelSegment = (horizontalSegments.length ? horizontalSegments : segments).reduce((longest, segment) =>
    segment.length > longest.length ? segment : longest,
  );
  return [path, (labelSegment.start.x + labelSegment.end.x) / 2, (labelSegment.start.y + labelSegment.end.y) / 2];
}

function roundedCorner(start: RoutePoint, corner: RoutePoint, end: RoutePoint, radius: number) {
  const incoming = Math.abs(start.x - corner.x) + Math.abs(start.y - corner.y);
  const outgoing = Math.abs(end.x - corner.x) + Math.abs(end.y - corner.y);
  const bend = Math.min(incoming / 2, outgoing / 2, radius);
  if (bend <= 0 || (start.x === corner.x && corner.x === end.x) || (start.y === corner.y && corner.y === end.y)) {
    return `L${corner.x} ${corner.y}`;
  }
  if (start.y === corner.y) {
    const incomingDirection = start.x < corner.x ? -1 : 1;
    const outgoingDirection = corner.y < end.y ? 1 : -1;
    return `L${corner.x + bend * incomingDirection},${corner.y}Q${corner.x},${corner.y} ${corner.x},${corner.y + bend * outgoingDirection}`;
  }
  const incomingDirection = start.y < corner.y ? -1 : 1;
  const outgoingDirection = corner.x < end.x ? 1 : -1;
  return `L${corner.x},${corner.y + bend * incomingDirection}Q${corner.x},${corner.y} ${corner.x + bend * outgoingDirection},${corner.y}`;
}

function fallbackZoneBox(index: number): LayoutBox {
  return { x: 900 + index * 1450, y: 5100, width: 1280, height: 850 };
}

function fallbackComponentPosition(zoneId: string, index: number) {
  const zone = ZONE_LAYOUT[zoneId] ?? fallbackZoneBox(0);
  const columns = Math.max(1, Math.floor((zone.width - 180) / (COMPONENT_SIZE.width + 100)));
  return {
    x: zone.x + 100 + (index % columns) * (COMPONENT_SIZE.width + 100),
    y: zone.y + 330 + Math.floor(index / columns) * (COMPONENT_SIZE.height + 120),
  };
}

function searchableText(values: unknown[]) {
  return values
    .filter((value) => value !== undefined && value !== null)
    .map((value) => String(value).toLowerCase())
    .join(" ");
}

function normalizeToken(value: string) {
  return value.trim().toLowerCase().replace(/[\s/-]+/g, "_");
}

function prettyToken(value: string) {
  return value
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function toggleSetValue<T>(current: Set<T>, value: T) {
  const next = new Set(current);
  if (next.has(value)) next.delete(value);
  else next.add(value);
  return next;
}

function evidenceKinds(refs: ContractEvidenceRef[]) {
  return [...new Set(refs.map((ref) => ref.verification ?? "source"))];
}

function uniqueEvidence(refs: ContractEvidenceRef[]) {
  const seen = new Set<string>();
  return refs.filter((ref) => {
    const key = `${ref.path}:${ref.line}:${ref.symbol ?? ""}:${ref.claim ?? ""}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function clamp(value: number, minimum: number, maximum: number) {
  return Math.max(minimum, Math.min(maximum, value));
}
