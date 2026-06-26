import {
  Boxes,
  Braces,
  Cable,
  CheckCircle2,
  Code2,
  Database,
  FileCode2,
  GitBranch,
  Globe2,
  Layers3,
  ListFilter,
  Minus,
  Move,
  Plus,
  RadioTower,
  RefreshCw,
  RotateCcw,
  Route,
  Search,
  Server,
  Workflow,
  XCircle,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState, type PointerEvent, type ReactNode } from "react";
import type { ContractEdge, ContractGraph, ContractNode, ContractScenario, ContractSourceRef } from "./api";
import { Badge } from "./components/ui/badge";
import { Button } from "./components/ui/button";
import { Tabs } from "./components/ui/tabs";
import { Textarea } from "./components/ui/textarea";

type ContractExplorerProps = {
  graph?: ContractGraph;
  busy: boolean;
  error?: string;
  onRefresh: () => void;
};

const LANE_DEFS = [
  { id: "ui", label: "UI", icon: <Globe2 className="h-4 w-4" />, match: (node: ContractNode) => node.id.includes(":ui") || node.id.includes("frontend") },
  { id: "adapter", label: "Adapter", icon: <Server className="h-4 w-4" />, match: (node: ContractNode) => node.id.includes(":api") || node.kind === "http_endpoint" },
  { id: "legacy", label: "Legacy ROS", icon: <RadioTower className="h-4 w-4" />, match: (node: ContractNode) => node.layer === "ros" || ["component:c2_rest", "component:centralized", "component:planner", "component:fleet"].includes(node.id) },
  { id: "edge", label: "Edge/Autonomy", icon: <Cable className="h-4 w-4" />, match: (node: ContractNode) => ["component:edge", "component:autonomy"].includes(node.id) || /edge|autonomy/i.test(node.label) },
  { id: "data", label: "Data", icon: <Database className="h-4 w-4" />, match: (node: ContractNode) => node.layer === "data" || node.id.includes("mongodb") },
];

const TYPE_TONE: Record<string, "default" | "ok" | "warn" | "error"> = {
  component: "ok",
  http_endpoint: "default",
  ros_topic: "warn",
  ros_service: "warn",
  ros_type: "default",
  json_schema: "ok",
  mongo_collection: "default",
  container: "default",
};

export function ContractExplorer({ graph, busy, error, onRefresh }: ContractExplorerProps) {
  const [view, setView] = useState("map");
  const [layer, setLayer] = useState("all");
  const [query, setQuery] = useState("");
  const [selectedNodeId, setSelectedNodeId] = useState<string | undefined>();
  const [focusedNodeId, setFocusedNodeId] = useState<string | undefined>();
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | undefined>();
  const [selectedScenarioId, setSelectedScenarioId] = useState<string | undefined>("mission_lifecycle");

  const nodeById = useMemo(() => new Map((graph?.nodes ?? []).map((node) => [node.id, node])), [graph]);
  const edgeById = useMemo(() => new Map((graph?.edges ?? []).map((edge) => [edge.id, edge])), [graph]);
  const selectedNode = selectedNodeId ? nodeById.get(selectedNodeId) : undefined;
  const selectedEdge = selectedEdgeId ? edgeById.get(selectedEdgeId) : undefined;
  const selectedScenario = useMemo(() => {
    const scenarios = graph?.scenarios ?? [];
    return scenarios.find((scenario) => scenario.id === selectedScenarioId) ?? scenarios[0];
  }, [graph?.scenarios, selectedScenarioId]);

  const filteredNodes = useMemo(() => {
    return (graph?.nodes ?? []).filter((node) => matchesFilter(node, layer, query));
  }, [graph?.nodes, layer, query]);

  const filteredEdges = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return (graph?.edges ?? []).filter((edge) => {
      if (layer !== "all" && edge.layer !== layer) return false;
      if (!normalizedQuery) return true;
      return [edge.label, edge.kind, edge.protocol, edge.contract, edge.source, edge.target].some((value) => String(value ?? "").toLowerCase().includes(normalizedQuery));
    });
  }, [graph?.edges, layer, query]);

  if (!graph) {
    return (
      <div className="space-y-3">
        <ContractHeader busy={busy} graph={graph} onRefresh={onRefresh} />
        <div className="rounded-md border border-border bg-panel p-4 text-sm text-muted-foreground">
          {error || "Contract graph unavailable."}
        </div>
      </div>
    );
  }

  const inspectorPayload = selectedEdge ?? selectedNode ?? selectedScenario;

  return (
    <div className="space-y-4">
      <ContractHeader busy={busy} graph={graph} onRefresh={onRefresh} />
      {error && <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">{error}</div>}

      <div className="grid grid-cols-4 gap-2">
        <Metric icon={<Boxes className="h-4 w-4" />} label="Nodes" value={String(graph.summary.nodes)} />
        <Metric icon={<GitBranch className="h-4 w-4" />} label="Edges" value={String(graph.summary.edges)} />
        <Metric icon={<Route className="h-4 w-4" />} label="Traces" value={String(graph.summary.scenarios)} />
        <Metric icon={<Code2 className="h-4 w-4" />} label="Digest" value={graph.source_digest} compact />
      </div>

      <div className="grid grid-cols-[minmax(0,1fr)_360px] gap-4">
        <div className="space-y-3">
          <div className="flex items-center justify-between gap-3 rounded-md border border-border bg-panel p-3">
            <Tabs
              value={view}
              onValueChange={setView}
              items={[
                { value: "map", label: "Map" },
                { value: "edges", label: "Edges" },
                { value: "scenarios", label: "Traces" },
                { value: "raw", label: "Raw" },
              ]}
            />
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-2 rounded-md border border-border bg-background px-2">
                <Search className="h-4 w-4 text-muted-foreground" />
                <input className="h-8 w-44 bg-transparent text-sm outline-none" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="search contracts" />
              </div>
              <select className="h-8 rounded-md border border-border bg-background px-2 text-sm" value={layer} onChange={(event) => setLayer(event.target.value)}>
                <option value="all">all layers</option>
                {graph.layers.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {view === "map" && (
            <ContractMap
              nodes={graph.nodes}
              edges={filteredEdges}
              selectedNodeId={selectedNodeId}
              focusedNodeId={focusedNodeId}
              selectedEdgeId={selectedEdgeId}
              query={query}
              layer={layer}
              onSelectNode={(nodeId) => {
                setSelectedNodeId(nodeId);
                if (nodeById.get(nodeId)?.kind === "component") setFocusedNodeId(nodeId);
                setSelectedEdgeId(undefined);
              }}
              onSelectEdge={(edgeId) => setSelectedEdgeId(edgeId)}
            />
          )}

          {view === "edges" && (
            <EdgeList
              edges={filteredEdges}
              nodeById={nodeById}
              selectedEdgeId={selectedEdgeId}
              onSelectEdge={(edgeId) => {
                setSelectedEdgeId(edgeId);
                const edge = edgeById.get(edgeId);
                if (edge) setSelectedNodeId(edge.target);
              }}
            />
          )}

          {view === "scenarios" && (
            <ScenarioTraceList
              scenarios={graph.scenarios}
              nodeById={nodeById}
              selectedScenario={selectedScenario}
              onSelectScenario={(scenario) => {
                setSelectedScenarioId(scenario.id);
                setSelectedEdgeId(undefined);
              }}
              onSelectStage={(component) => setSelectedNodeId(component)}
            />
          )}

          {view === "raw" && (
            <div className="space-y-3">
              <div className="rounded-md border border-border bg-panel p-3 text-sm">
                <div className="flex items-center gap-2 font-semibold">
                  <Code2 className="h-4 w-4 text-primary" />
                  Raw Contract Payload
                </div>
                <div className="mt-1 text-xs text-muted-foreground">
                  This is the generated JSON returned by <span className="font-mono">GET /api/contracts</span>. It is built from source scanners for FastAPI routes, frontend API calls, ROS .msg/.srv files, ROS pub/sub/service/client calls, schemas, Docker Compose services, Mongo collections, and hand-curated scenario traces. It is not a packet capture of live ROS messages.
                </div>
              </div>
              <Textarea className="h-[640px] resize-none font-mono text-xs" value={JSON.stringify(graph, null, 2)} readOnly spellCheck={false} />
            </div>
          )}
        </div>

        <Inspector payload={inspectorPayload} graph={graph} nodeById={nodeById} />
      </div>
    </div>
  );
}

function ContractHeader({ graph, busy, onRefresh }: { graph?: ContractGraph; busy: boolean; onRefresh: () => void }) {
  return (
    <div className="flex items-start justify-between gap-4 rounded-md border border-border bg-panel p-4">
      <div className="min-w-0">
        <div className="flex items-center gap-2 text-sm font-semibold">
          <Workflow className="h-4 w-4 text-primary" />
          Legacy Contract Explorer
        </div>
        <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <span>{graph ? `${graph.source_file_count} source files` : "source graph pending"}</span>
          {graph?.generated_at && <span>{new Date(graph.generated_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</span>}
          {graph?.runtime && <span>{graph.runtime.ros_topics?.length ?? 0} runtime topics</span>}
        </div>
      </div>
      <Button size="sm" variant="outline" onClick={onRefresh} disabled={busy}>
        <RefreshCw className={`h-4 w-4 ${busy ? "animate-spin" : ""}`} />
        {busy ? "Refreshing" : "Refresh"}
      </Button>
    </div>
  );
}

function ContractMap({
  nodes,
  edges,
  selectedNodeId,
  focusedNodeId,
  selectedEdgeId,
  query,
  layer,
  onSelectNode,
  onSelectEdge,
}: {
  nodes: ContractNode[];
  edges: ContractEdge[];
  selectedNodeId?: string;
  focusedNodeId?: string;
  selectedEdgeId?: string;
  query: string;
  layer: string;
  onSelectNode: (nodeId: string) => void;
  onSelectEdge: (edgeId: string) => void;
}) {
  const graphLayout = useMemo(() => buildGraphLayout(nodes, edges, focusedNodeId, query, layer), [nodes, edges, focusedNodeId, query, layer]);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [dragStart, setDragStart] = useState<{ pointerId: number; clientX: number; clientY: number; panX: number; panY: number } | null>(null);
  const [hoveredEdgeId, setHoveredEdgeId] = useState<string | undefined>();
  const canvasRef = useRef<SVGSVGElement | null>(null);
  const relatedEdgeIds = new Set(
    focusedNodeId
      ? edges.filter((edge) => edge.source === focusedNodeId || edge.target === focusedNodeId).map((edge) => edge.id)
      : [],
  );

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const handleNativeWheel = (event: globalThis.WheelEvent) => {
      event.preventDefault();
      event.stopPropagation();
      const direction = event.deltaY > 0 ? -1 : 1;
      setZoom((current) => clamp(current + direction * 0.08, 0.52, 1.75));
    };
    canvas.addEventListener("wheel", handleNativeWheel, { passive: false });
    return () => canvas.removeEventListener("wheel", handleNativeWheel);
  }, []);

  function resetCanvas() {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }

  function zoomCanvas(direction: 1 | -1) {
    setZoom((current) => clamp(current + direction * 0.12, 0.52, 1.75));
  }

  function handlePointerDown(event: PointerEvent<SVGSVGElement>) {
    if (event.button !== 0) return;
    setDragStart({ pointerId: event.pointerId, clientX: event.clientX, clientY: event.clientY, panX: pan.x, panY: pan.y });
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function handlePointerMove(event: PointerEvent<SVGSVGElement>) {
    if (!dragStart) return;
    const scale = graphLayout.width / Math.max(1, canvasRef.current?.clientWidth ?? graphLayout.width);
    setPan({
      x: dragStart.panX + (event.clientX - dragStart.clientX) * scale,
      y: dragStart.panY + (event.clientY - dragStart.clientY) * scale,
    });
  }

  function handlePointerUp(event: PointerEvent<SVGSVGElement>) {
    if (dragStart?.pointerId === event.pointerId) {
      setDragStart(null);
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  }

  return (
    <div className="overflow-hidden rounded-md border border-border bg-panel">
      <div className="flex items-center justify-between gap-3 border-b border-border px-3 py-2">
        <div className="flex items-center gap-2 text-sm font-semibold">
          <Workflow className="h-4 w-4 text-primary" />
          Contract Canvas
          <Badge>{graphLayout.nodes.length} nodes</Badge>
          <Badge>{graphLayout.edges.length} arrows</Badge>
        </div>
        <div className="flex items-center gap-2">
          <div className="hidden items-center gap-1 lg:flex">
            <EdgeToneBadge tone="system" />
            <EdgeToneBadge tone="http" />
            <EdgeToneBadge tone="ros" />
            <EdgeToneBadge tone="data" />
          </div>
          <div className="flex items-center gap-1 rounded-md border border-border bg-background p-1">
            <span className="grid h-9 w-9 place-items-center text-muted-foreground" title="Pan canvas">
              <Move className="h-4 w-4" />
            </span>
            <Button type="button" size="icon" variant="ghost" title="Zoom out" onClick={() => zoomCanvas(-1)}>
              <Minus className="h-4 w-4" />
            </Button>
            <span className="min-w-10 text-center text-xs font-medium text-muted-foreground">{Math.round(zoom * 100)}%</span>
            <Button type="button" size="icon" variant="ghost" title="Zoom in" onClick={() => zoomCanvas(1)}>
              <Plus className="h-4 w-4" />
            </Button>
            <Button type="button" size="icon" variant="ghost" title="Reset canvas" onClick={resetCanvas}>
              <RotateCcw className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
      <div className="relative h-[calc(100vh-360px)] min-h-[620px] overflow-hidden bg-[#f8fafc]">
        <svg
          ref={canvasRef}
          className={`block h-full w-full touch-none ${dragStart ? "cursor-grabbing" : "cursor-grab"}`}
          viewBox={`0 0 ${graphLayout.width} ${graphLayout.height}`}
          preserveAspectRatio="xMinYMin meet"
          role="img"
          aria-label="Directed contract graph"
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerCancel={handlePointerUp}
        >
          <defs>
            <pattern id="contract-grid" width="28" height="28" patternUnits="userSpaceOnUse">
              <path d="M 28 0 L 0 0 0 28" fill="none" stroke="#e2e8f0" strokeWidth="0.8" />
            </pattern>
            {Object.values(EDGE_TONES).map((tone) => (
              <marker key={tone.id} id={`contract-arrow-${tone.id}`} markerWidth="11" markerHeight="11" refX="10" refY="3.5" orient="auto" markerUnits="strokeWidth">
                <path d="M0,0 L0,7 L10,3.5 z" fill={tone.color} />
              </marker>
            ))}
            <marker id="contract-arrow-active" markerWidth="12" markerHeight="12" refX="11" refY="4" orient="auto" markerUnits="strokeWidth">
              <path d="M0,0 L0,6 L9,3 z" fill="#0f766e" />
            </marker>
          </defs>
          <rect x="0" y="0" width={graphLayout.width} height={graphLayout.height} fill="url(#contract-grid)" />

          <g transform={`translate(${pan.x} ${pan.y}) scale(${zoom})`}>
            {graphLayout.lanes.map((lane) => (
              <g key={lane.id}>
                <rect x={lane.x - 24} y={0} width={lane.width} height={graphLayout.height} fill={lane.fill} opacity="0.62" />
                <text x={lane.x} y={34} fontSize="14" fontWeight="800" fill="#334155">
                  {lane.label}
                </text>
              </g>
            ))}

            {graphLayout.edges.map((edge) => {
              const source = graphLayout.nodeById.get(edge.source);
              const target = graphLayout.nodeById.get(edge.target);
              if (!source || !target) return null;
              const route = graphLayout.edgeRoutes.get(edge.id);
              if (!route) return null;
              const path = route.path;
              const tone = edgeTone(edge);
              const active = edge.id === selectedEdgeId || relatedEdgeIds.has(edge.id) || (!focusedNodeId && edge.kind === "system_flow");
              const hovered = edge.id === hoveredEdgeId;
              return (
                <g key={edge.id}>
                  <path d={path} fill="none" stroke="#ffffff" strokeWidth={active || hovered ? 8 : 6} strokeLinecap="round" opacity="0.9" />
                  <path
                    d={path}
                    fill="none"
                    stroke={active || hovered ? tone.color : tone.muted}
                    strokeWidth={active || hovered ? 3.8 : 2.5}
                    strokeLinecap="round"
                    markerEnd={`url(#contract-arrow-${active || hovered ? tone.id : tone.id})`}
                    opacity={active || hovered ? 0.98 : 0.74}
                  />
                  <path
                    data-graph-edge
                    d={path}
                    fill="none"
                    stroke="transparent"
                    strokeWidth="22"
                    className="cursor-pointer"
                    onPointerDown={(event) => event.stopPropagation()}
                    onMouseEnter={() => setHoveredEdgeId(edge.id)}
                    onMouseLeave={() => setHoveredEdgeId(undefined)}
                    onClick={() => onSelectEdge(edge.id)}
                  >
                    <title>{edge.label}</title>
                  </path>
                </g>
              );
            })}

            {graphLayout.nodes.map((node) => {
              const selected = node.id === selectedNodeId;
              const tone = nodeTone(node);
              const lines = labelLines(node.label, node.kind === "http_endpoint" ? 28 : 24);
              return (
                <g
                  key={node.id}
                  data-graph-node
                  data-node-id={node.id}
                  className="cursor-pointer"
                  onPointerDown={(event) => event.stopPropagation()}
                  onClick={() => onSelectNode(node.id)}
                >
                  <rect x={node.x} y={node.y} width={node.width} height={node.height} rx="8" fill={selected ? tone.selectedFill : tone.fill} stroke={selected ? tone.color : tone.border} strokeWidth={selected ? 2.6 : 1.35} />
                  <rect x={node.x} y={node.y} width="7" height={node.height} rx="4" fill={tone.color} opacity={selected ? 1 : 0.82} />
                  <circle cx={node.x + 19} cy={node.y + 20} r="4.5" fill={tone.color} />
                  {node.runtime_status && <circle cx={node.x + node.width - 17} cy={node.y + 19} r="5" fill={node.runtime_status === "visible" ? "#10b981" : "#f59e0b"} />}
                  <text x={node.x + 32} y={node.y + 20} fontSize="12.5" fontWeight="800" fill="#0f172a">
                    {lines[0]}
                  </text>
                  {lines[1] && (
                    <text x={node.x + 32} y={node.y + 36} fontSize="12.5" fontWeight="800" fill="#0f172a">
                      {lines[1]}
                    </text>
                  )}
                  <text x={node.x + 18} y={node.y + node.height - 15} fontSize="10.5" fill="#64748b">
                    {node.kind}
                  </text>
                  <text x={node.x + node.width - 16} y={node.y + node.height - 15} textAnchor="end" fontSize="10.5" fill="#64748b">
                    {node.layer}
                  </text>
                  <title>{`${node.label}\n${node.kind}\n${node.id}`}</title>
                </g>
              );
            })}

            <g className="pointer-events-none">
              {graphLayout.edges.map((edge) => {
                if (edge.id !== selectedEdgeId && edge.id !== hoveredEdgeId) return null;
                const route = graphLayout.edgeRoutes.get(edge.id);
                if (!route) return null;
                const tone = edgeTone(edge);
                const label = clipLabel(edge.label, 30);
                const labelWidth = Math.max(82, Math.min(190, label.length * 6.8 + 22));
                return (
                  <g key={`label:${edge.id}`}>
                    <rect x={route.midpoint.x - labelWidth / 2} y={route.midpoint.y - 13} width={labelWidth} height="26" rx="6" fill="#ffffff" stroke={tone.color} strokeWidth="1.6" />
                    <text x={route.midpoint.x} y={route.midpoint.y + 4} textAnchor="middle" fontSize="11" fontWeight="700" fill="#0f172a">
                      {label}
                    </text>
                  </g>
                );
              })}
            </g>
          </g>
        </svg>
      </div>
      <div className="flex items-center justify-between gap-3 border-t border-border px-3 py-2">
        <div className="flex flex-wrap gap-2">
          {Object.values(EDGE_TONES).map((tone) => (
            <EdgeToneBadge key={tone.id} tone={tone.id} />
          ))}
        </div>
        <div className="flex flex-wrap justify-end gap-1">
          <Badge tone="ok">node</Badge>
          <Badge tone="warn">runtime</Badge>
        </div>
      </div>
    </div>
  );
}

function NodeButton({ node, selected, onClick }: { node: ContractNode; selected: boolean; onClick: () => void }) {
  return (
    <button className={`w-full rounded-md border p-2 text-left text-xs transition hover:border-primary ${selected ? "border-primary bg-secondary" : "border-border bg-background"}`} onClick={onClick}>
      <div className="flex items-center justify-between gap-2">
        <span className="truncate font-semibold">{node.label}</span>
        <StatusIcon node={node} />
      </div>
      <div className="mt-1 flex items-center gap-1">
        <Badge tone={TYPE_TONE[node.kind] ?? "default"}>{node.kind}</Badge>
        {node.runtime_status && <Badge tone={node.runtime_status === "visible" ? "ok" : "warn"}>{node.runtime_status}</Badge>}
      </div>
    </button>
  );
}

function StatusIcon({ node }: { node: ContractNode }) {
  if (!node.runtime_status) return null;
  if (node.runtime_status === "visible") return <CheckCircle2 className="h-4 w-4 text-emerald-700" />;
  return <XCircle className="h-4 w-4 text-amber-700" />;
}

function EdgeList({
  edges,
  nodeById,
  selectedEdgeId,
  onSelectEdge,
  dense = false,
}: {
  edges: ContractEdge[];
  nodeById?: Map<string, ContractNode>;
  selectedEdgeId?: string;
  onSelectEdge: (edgeId: string) => void;
  dense?: boolean;
}) {
  if (!edges.length) {
    return <div className="rounded-md border border-border bg-panel p-4 text-sm text-muted-foreground">No matching edges.</div>;
  }
  return (
    <div className={dense ? "grid grid-cols-2 gap-2" : "space-y-2"}>
      {edges.map((edge) => (
        <button key={edge.id} className={`w-full rounded-md border p-3 text-left text-xs hover:border-primary ${edge.id === selectedEdgeId ? "border-primary bg-secondary" : "border-border bg-panel"}`} onClick={() => onSelectEdge(edge.id)}>
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="truncate text-sm font-semibold">{edge.label}</div>
              <div className="mt-1 truncate text-muted-foreground">
                {nodeById?.get(edge.source)?.label ?? edge.source} {"->"} {nodeById?.get(edge.target)?.label ?? edge.target}
              </div>
            </div>
            <Badge>{edge.protocol ?? edge.kind}</Badge>
          </div>
          {!dense && (
            <div className="mt-2 flex flex-wrap gap-1">
              <Badge tone="default">{edge.layer}</Badge>
              <Badge tone="default">{edge.kind}</Badge>
              {edge.contract && <Badge tone="warn">{shortLabel(edge.contract)}</Badge>}
            </div>
          )}
        </button>
      ))}
    </div>
  );
}

function ScenarioTraceList({
  scenarios,
  nodeById,
  selectedScenario,
  onSelectScenario,
  onSelectStage,
}: {
  scenarios: ContractScenario[];
  nodeById: Map<string, ContractNode>;
  selectedScenario?: ContractScenario;
  onSelectScenario: (scenario: ContractScenario) => void;
  onSelectStage: (component: string) => void;
}) {
  return (
    <div className="grid grid-cols-[230px_1fr] gap-4">
      <div className="space-y-2">
        {scenarios.map((scenario) => (
          <button key={scenario.id} className={`w-full rounded-md border p-3 text-left text-xs hover:border-primary ${selectedScenario?.id === scenario.id ? "border-primary bg-secondary" : "border-border bg-panel"}`} onClick={() => onSelectScenario(scenario)}>
            <div className="font-semibold">{scenario.label}</div>
            <div className="mt-1 text-muted-foreground">{scenario.stages.length} stages</div>
          </button>
        ))}
      </div>
      <div className="rounded-md border border-border bg-panel p-4">
        {selectedScenario ? (
          <div className="space-y-3">
            <div>
              <div className="flex items-center gap-2 text-sm font-semibold">
                <Route className="h-4 w-4" />
                {selectedScenario.label}
              </div>
              <div className="mt-1 text-xs text-muted-foreground">{selectedScenario.summary}</div>
            </div>
            <div className="space-y-2">
              {selectedScenario.stages.map((stage, index) => (
                <button key={stage.id} className="w-full rounded-md border border-border bg-background p-3 text-left text-xs hover:border-primary" onClick={() => onSelectStage(stage.component)}>
                  <div className="flex items-start gap-3">
                    <div className="grid h-7 w-7 shrink-0 place-items-center rounded-md bg-muted font-semibold">{index + 1}</div>
                    <div className="min-w-0 flex-1">
                      <div className="font-semibold">{stage.label}</div>
                      <div className="mt-1 text-muted-foreground">{nodeById.get(stage.component)?.label ?? stage.component}</div>
                      <StagePills label="In" values={stage.inputs} />
                      <StagePills label="Out" values={stage.outputs} />
                      <SourceRefs refs={stage.source_refs} />
                    </div>
                  </div>
                </button>
              ))}
            </div>
            {selectedScenario.risks?.map((risk) => (
              <div key={risk} className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
                {risk}
              </div>
            ))}
          </div>
        ) : (
          <div className="text-sm text-muted-foreground">No scenario selected.</div>
        )}
      </div>
    </div>
  );
}

function StagePills({ label, values }: { label: string; values?: string[] }) {
  if (!values?.length) return null;
  return (
    <div className="mt-2 flex flex-wrap items-center gap-1">
      <Badge tone="default">{label}</Badge>
      {values.map((value) => (
        <span key={value} className="rounded-sm border border-border bg-panel px-2 py-1 text-muted-foreground">
          {value}
        </span>
      ))}
    </div>
  );
}

function Inspector({
  payload,
  graph,
  nodeById,
}: {
  payload?: ContractNode | ContractEdge | ContractScenario;
  graph: ContractGraph;
  nodeById: Map<string, ContractNode>;
}) {
  if (!payload) {
    return <div className="rounded-md border border-border bg-panel p-4 text-sm text-muted-foreground">Select a node, edge, or trace.</div>;
  }
  const kind = "source" in payload && "target" in payload ? "edge" : "stages" in payload ? "scenario" : "node";
  const title = payload.label;
  return (
    <div className="sticky top-0 max-h-[calc(100vh-160px)] space-y-3 overflow-auto rounded-md border border-border bg-panel p-4">
      <div>
        <div className="flex items-center gap-2 text-sm font-semibold">
          {kind === "edge" ? <GitBranch className="h-4 w-4" /> : kind === "scenario" ? <Route className="h-4 w-4" /> : <FileCode2 className="h-4 w-4" />}
          {title}
        </div>
        <div className="mt-2 flex flex-wrap gap-1">
          <Badge>{kind}</Badge>
          {"kind" in payload && <Badge tone={TYPE_TONE[payload.kind] ?? "default"}>{payload.kind}</Badge>}
          {"layer" in payload && <Badge>{payload.layer}</Badge>}
          {"runtime_status" in payload && payload.runtime_status && <Badge tone={payload.runtime_status === "visible" ? "ok" : "warn"}>{payload.runtime_status}</Badge>}
        </div>
      </div>

      {"description" in payload && payload.description && <InfoBlock label="Description" value={payload.description} />}

      {"source" in payload && "target" in payload && (
        <div className="grid grid-cols-2 gap-2 text-xs">
          <InfoBlock label="Source" value={nodeById.get(payload.source)?.label ?? payload.source} />
          <InfoBlock label="Target" value={nodeById.get(payload.target)?.label ?? payload.target} />
          <InfoBlock label="Protocol" value={payload.protocol ?? payload.kind} />
          <InfoBlock label="Contract" value={payload.contract ?? "n/a"} />
        </div>
      )}

      {"summary" in payload && <InfoBlock label="Summary" value={payload.summary} />}

      {"fields" in payload && payload.fields && payload.fields.length > 0 && <FieldTable fields={payload.fields} />}
      {"source_refs" in payload && <SourceRefs refs={payload.source_refs} />}

      {"details" in payload && payload.details && (
        <div>
          <SectionTitle icon={<Braces className="h-4 w-4" />} label="Details" />
          <Textarea className="mt-2 h-36 resize-none font-mono text-xs" value={JSON.stringify(payload.details, null, 2)} readOnly spellCheck={false} />
        </div>
      )}

      <div>
        <SectionTitle icon={<Code2 className="h-4 w-4" />} label="Raw Payload" />
        <Textarea className="mt-2 h-48 resize-none font-mono text-xs" value={JSON.stringify(payload, null, 2)} readOnly spellCheck={false} />
      </div>

      <div>
        <SectionTitle icon={<Layers3 className="h-4 w-4" />} label="Graph Digest" />
        <div className="mt-2 rounded-md border border-border bg-background p-2 text-xs text-muted-foreground">
          {graph.source_digest} from {graph.source_file_count} files
        </div>
      </div>
    </div>
  );
}

function FieldTable({ fields }: { fields: { section?: string; type?: string; name: string }[] }) {
  return (
    <div>
      <SectionTitle icon={<ListFilter className="h-4 w-4" />} label="Fields" />
      <div className="mt-2 max-h-52 overflow-auto rounded-md border border-border">
        {fields.map((field, index) => (
          <div key={`${field.section}-${field.name}-${index}`} className="grid grid-cols-[80px_1fr_1fr] gap-2 border-b border-border bg-background px-2 py-1 text-xs last:border-b-0">
            <span className="text-muted-foreground">{field.section ?? "field"}</span>
            <span className="font-mono">{field.type ?? "unknown"}</span>
            <span className="font-semibold">{field.name}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function SourceRefs({ refs }: { refs?: ContractSourceRef[] }) {
  const uniqueRefs = uniqueSourceRefs(refs);
  if (!uniqueRefs.length) return null;
  return (
    <div className="mt-3">
      <SectionTitle icon={<FileCode2 className="h-4 w-4" />} label="Source" />
      <div className="mt-2 space-y-1">
        {uniqueRefs.slice(0, 8).map((ref) => (
          <div key={`${ref.path}:${ref.line}`} className="rounded-sm border border-border bg-background px-2 py-1 font-mono text-[11px] text-muted-foreground">
            {ref.path}:{ref.line}
          </div>
        ))}
      </div>
    </div>
  );
}

function uniqueSourceRefs(refs?: ContractSourceRef[]) {
  const seen = new Set<string>();
  const result: ContractSourceRef[] = [];
  for (const ref of refs ?? []) {
    const key = `${ref.path}:${ref.line}`;
    if (seen.has(key)) continue;
    seen.add(key);
    result.push(ref);
  }
  return result;
}

function Metric({ icon, label, value, compact = false }: { icon: ReactNode; label: string; value: string; compact?: boolean }) {
  return (
    <div className="rounded-md border border-border bg-panel p-3">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        {icon}
        {label}
      </div>
      <div className={`mt-1 font-semibold ${compact ? "font-mono text-sm" : "text-2xl"}`}>{value}</div>
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

function InfoBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border bg-background p-2">
      <div className="text-[11px] uppercase text-muted-foreground">{label}</div>
      <div className="mt-1 break-words text-xs font-medium">{value}</div>
    </div>
  );
}

function matchesFilter(node: ContractNode, layer: string, query: string) {
  if (layer !== "all" && node.layer !== layer) return false;
  const normalized = query.trim().toLowerCase();
  if (!normalized) return true;
  return [node.id, node.label, node.kind, node.layer, node.description].some((value) => String(value ?? "").toLowerCase().includes(normalized));
}

function shortLabel(value: string) {
  const parts = value.split("/");
  return parts.length > 1 ? parts.slice(-2).join("/") : value;
}

type EdgeToneId = "system" | "http" | "ros" | "data" | "deploy";

type EdgeTone = {
  id: EdgeToneId;
  label: string;
  color: string;
  muted: string;
  bg: string;
  border: string;
};

const EDGE_TONES: Record<EdgeToneId, EdgeTone> = {
  system: { id: "system", label: "System", color: "#0f766e", muted: "#5eead4", bg: "#ecfdf5", border: "#a7f3d0" },
  http: { id: "http", label: "HTTP/API", color: "#2563eb", muted: "#93c5fd", bg: "#eff6ff", border: "#bfdbfe" },
  ros: { id: "ros", label: "ROS", color: "#d97706", muted: "#fbbf24", bg: "#fffbeb", border: "#fde68a" },
  data: { id: "data", label: "Data", color: "#475569", muted: "#94a3b8", bg: "#f8fafc", border: "#cbd5e1" },
  deploy: { id: "deploy", label: "Deploy", color: "#7c3aed", muted: "#c4b5fd", bg: "#f5f3ff", border: "#ddd6fe" },
};

function EdgeToneBadge({ tone }: { tone: EdgeToneId }) {
  const value = EDGE_TONES[tone];
  return (
    <span className="inline-flex h-6 items-center gap-1 rounded-sm border px-2 text-xs font-medium" style={{ borderColor: value.border, backgroundColor: value.bg, color: value.color }}>
      <span className="h-1.5 w-5 rounded-full" style={{ backgroundColor: value.color }} />
      {value.label}
    </span>
  );
}

type GraphLayoutNode = ContractNode & {
  x: number;
  y: number;
  width: number;
  height: number;
  lane: number;
};

type GraphEdgeRoute = {
  path: string;
  midpoint: { x: number; y: number };
};

type GraphLane = {
  id: string;
  label: string;
  x: number;
  width: number;
  fill: string;
};

const LANE_FILLS = ["#f8fafc", "#eef6ff", "#fff9ed", "#eefbf5", "#f8fafc"];
const CANVAS_VIEW_HEIGHT = 1100;
const COMPONENT_ORDER = [
  "component:ui",
  "component:api",
  "component:c2_rest",
  "component:centralized",
  "component:planner",
  "component:fleet",
  "component:edge",
  "component:autonomy",
  "component:rosbridge",
  "component:mongodb",
  "component:schemas",
];

function buildGraphLayout(nodes: ContractNode[], edges: ContractEdge[], selectedNodeId: string | undefined, query: string, layer: string) {
  const normalizedQuery = query.trim().toLowerCase();
  const focused = normalizedQuery.length > 0 || layer !== "all";
  const sourceNodes = new Map(nodes.map((node) => [node.id, node]));
  const displayNodeIds = new Set<string>();

  for (const node of nodes) {
    if (node.kind === "component") displayNodeIds.add(node.id);
  }
  for (const edge of edges) {
    if (edge.kind === "system_flow") {
      displayNodeIds.add(edge.source);
      displayNodeIds.add(edge.target);
    }
  }
  if (selectedNodeId && sourceNodes.has(selectedNodeId)) {
    displayNodeIds.add(selectedNodeId);
  }

  const selectedIncidentEdges = prioritizeEdges(edges, selectedNodeId)
    .filter((edge) => edge.source === selectedNodeId || edge.target === selectedNodeId)
    .slice(0, focused ? 48 : 12);
  for (const edge of selectedIncidentEdges) {
    displayNodeIds.add(edge.source);
    displayNodeIds.add(edge.target);
  }

  if (focused) {
    const matchedNodes = nodes.filter((node) => matchesFilter(node, layer, query)).slice(0, 90);
    for (const node of matchedNodes) displayNodeIds.add(node.id);
    for (const edge of prioritizeEdges(edges, selectedNodeId).slice(0, 140)) {
      displayNodeIds.add(edge.source);
      displayNodeIds.add(edge.target);
    }
  }

  const displayEdges = prioritizeEdges(edges, selectedNodeId)
    .filter((edge) => {
      if (edge.kind === "system_flow") {
        if (selectedNodeId) return edge.source === selectedNodeId || edge.target === selectedNodeId;
        return displayNodeIds.has(edge.source) && displayNodeIds.has(edge.target);
      }
      if (selectedIncidentEdges.some((selectedEdge) => selectedEdge.id === edge.id)) return true;
      if (focused) return displayNodeIds.has(edge.source) && displayNodeIds.has(edge.target);
      return false;
    })
    .slice(0, focused ? 180 : 70);

  for (const edge of displayEdges) {
    displayNodeIds.add(edge.source);
    displayNodeIds.add(edge.target);
  }

  const visibleNodes = Array.from(displayNodeIds)
    .map((nodeId) => sourceNodes.get(nodeId))
    .filter((node): node is ContractNode => Boolean(node));

  const laneCount = LANE_DEFS.length;
  const laneGap = 700;
  const laneStartX = 60;
  const nodeWidth = 280;
  const nodeHeight = 74;
  const rowGap = 116;
  const subcolumnGap = 340;
  const top = 72;
  const lanes: GraphLane[] = LANE_DEFS.map((lane, index) => ({
    id: lane.id,
    label: lane.label,
    x: laneStartX + index * laneGap,
    width: 640,
    fill: LANE_FILLS[index] ?? "#f8fafc",
  }));

  const grouped = Array.from({ length: laneCount }, () => [[], []] as [ContractNode[], ContractNode[]]);
  for (const node of visibleNodes) {
    grouped[laneIndexForNode(node)][nodeSubcolumnIndex(node)].push(node);
  }
  for (const laneColumns of grouped) {
    for (const laneNodes of laneColumns) {
      laneNodes.sort((left, right) => nodePriority(left) - nodePriority(right) || left.label.localeCompare(right.label) || left.id.localeCompare(right.id));
    }
  }

  const layoutNodes: GraphLayoutNode[] = [];
  grouped.forEach((laneColumns, laneIndex) => {
    laneColumns.forEach((laneNodes, subcolumnIndex) => {
      laneNodes.forEach((node, rowIndex) => {
        layoutNodes.push({
          ...node,
          lane: laneIndex,
          x: lanes[laneIndex].x + subcolumnIndex * subcolumnGap,
          y: top + rowIndex * rowGap + subcolumnIndex * 20,
          width: nodeWidth,
          height: nodeHeight,
        });
      });
    });
  });

  const nodeById = new Map(layoutNodes.map((node) => [node.id, node]));
  const finalEdges = displayEdges.filter((edge) => nodeById.has(edge.source) && nodeById.has(edge.target));
  return {
    nodes: layoutNodes,
    edges: finalEdges,
    edgeRoutes: buildEdgeRoutes(finalEdges, nodeById),
    nodeById,
    lanes,
    width: laneStartX * 2 + (laneCount - 1) * laneGap + subcolumnGap + nodeWidth + 80,
    height: CANVAS_VIEW_HEIGHT,
  };
}

function prioritizeEdges(edges: ContractEdge[], selectedNodeId?: string) {
  return [...edges].sort((left, right) => edgePriority(left, selectedNodeId) - edgePriority(right, selectedNodeId) || left.label.localeCompare(right.label));
}

function edgePriority(edge: ContractEdge, selectedNodeId?: string) {
  if (selectedNodeId && (edge.source === selectedNodeId || edge.target === selectedNodeId)) return 0;
  if (edge.kind === "system_flow") return 1;
  if (edge.kind === "http_call" || edge.kind === "http_handler") return 2;
  if (edge.kind === "ros_usage") return 3;
  if (edge.kind === "ros_type_link") return 4;
  if (edge.kind === "schema_definition") return 5;
  if (edge.kind === "persistence" || edge.kind === "mongo_read") return 6;
  return 7;
}

function laneIndexForNode(node: ContractNode) {
  const index = LANE_DEFS.findIndex((lane) => lane.match(node));
  if (index >= 0) return index;
  if (node.layer === "http") return 1;
  if (node.layer === "ros") return 2;
  if (node.layer === "data") return 4;
  return 2;
}

function nodeSubcolumnIndex(node: ContractNode) {
  if (node.kind === "component" || node.kind === "container") return 0;
  return 1;
}

function nodePriority(node: ContractNode) {
  const componentIndex = COMPONENT_ORDER.indexOf(node.id);
  if (componentIndex >= 0) return componentIndex;
  if (node.kind === "component") return 20;
  if (node.kind === "http_endpoint") return 40;
  if (node.kind === "ros_topic" || node.kind === "ros_service") return 60;
  if (node.kind === "ros_type") return 80;
  if (node.kind === "json_schema") return 90;
  if (node.kind === "mongo_collection") return 100;
  if (node.kind === "container") return 110;
  return 120;
}

function buildEdgeRoutes(edges: ContractEdge[], nodeById: Map<string, GraphLayoutNode>) {
  const sourceGroups = new Map<string, ContractEdge[]>();
  const targetGroups = new Map<string, ContractEdge[]>();
  const bundleGroups = new Map<string, ContractEdge[]>();

  for (const edge of edges) {
    const source = nodeById.get(edge.source);
    const target = nodeById.get(edge.target);
    if (!source || !target) continue;
    const sourceSide = sourcePortSide(source, target);
    const targetSide = targetPortSide(source, target);
    pushGrouped(sourceGroups, `${source.id}:${sourceSide}`, edge);
    pushGrouped(targetGroups, `${target.id}:${targetSide}`, edge);
    pushGrouped(bundleGroups, `${source.id}:${target.lane}:${sourceSide}:${targetSide}`, edge);
  }

  for (const group of [...sourceGroups.values(), ...targetGroups.values(), ...bundleGroups.values()]) {
    group.sort((left, right) => {
      const leftTarget = nodeById.get(left.target);
      const rightTarget = nodeById.get(right.target);
      const leftSource = nodeById.get(left.source);
      const rightSource = nodeById.get(right.source);
      return (leftTarget?.y ?? 0) - (rightTarget?.y ?? 0) || (leftSource?.y ?? 0) - (rightSource?.y ?? 0) || left.label.localeCompare(right.label);
    });
  }

  const routes = new Map<string, GraphEdgeRoute>();
  for (const edge of edges) {
    const source = nodeById.get(edge.source);
    const target = nodeById.get(edge.target);
    if (!source || !target) continue;
    const sourceSide = sourcePortSide(source, target);
    const targetSide = targetPortSide(source, target);
    const sourceGroup = sourceGroups.get(`${source.id}:${sourceSide}`) ?? [edge];
    const targetGroup = targetGroups.get(`${target.id}:${targetSide}`) ?? [edge];
    const bundleGroup = bundleGroups.get(`${source.id}:${target.lane}:${sourceSide}:${targetSide}`) ?? [edge];
    const sourcePoint = portPoint(source, sourceSide, sourceGroup, edge.id);
    const targetPoint = portPoint(target, targetSide, targetGroup, edge.id);
    const trackOffset = distributeOffset(bundleGroup.findIndex((item) => item.id === edge.id), bundleGroup.length, Math.min(96, Math.max(34, Math.abs(targetPoint.y - sourcePoint.y) * 0.16 + 34)));
    const route = routeBetweenPorts(sourcePoint, targetPoint, sourceSide, targetSide, trackOffset);
    routes.set(edge.id, route);
  }
  return routes;
}

function pushGrouped(groups: Map<string, ContractEdge[]>, key: string, edge: ContractEdge) {
  const group = groups.get(key) ?? [];
  group.push(edge);
  groups.set(key, group);
}

function sourcePortSide(source: GraphLayoutNode, target: GraphLayoutNode): "left" | "right" {
  if (target.lane > source.lane) return "right";
  if (target.lane < source.lane) return "left";
  return target.y >= source.y ? "right" : "left";
}

function targetPortSide(source: GraphLayoutNode, target: GraphLayoutNode): "left" | "right" {
  if (target.lane > source.lane) return "left";
  if (target.lane < source.lane) return "right";
  return target.y >= source.y ? "right" : "left";
}

function portPoint(node: GraphLayoutNode, side: "left" | "right", group: ContractEdge[], edgeId: string) {
  const index = Math.max(0, group.findIndex((edge) => edge.id === edgeId));
  const offset = distributeOffset(index, group.length, Math.max(16, node.height - 28));
  return {
    x: side === "right" ? node.x + node.width : node.x,
    y: node.y + node.height / 2 + offset,
  };
}

function routeBetweenPorts(
  source: { x: number; y: number },
  target: { x: number; y: number },
  sourceSide: "left" | "right",
  targetSide: "left" | "right",
  trackOffset: number,
): GraphEdgeRoute {
  const sourceDirection = sourceSide === "right" ? 1 : -1;
  const targetDirection = targetSide === "right" ? 1 : -1;
  const distance = Math.abs(target.x - source.x);
  const lead = clamp(distance * 0.28, 70, 150);
  const sourceLeadX = source.x + sourceDirection * (lead + Math.max(0, trackOffset));
  const targetLeadX = target.x + targetDirection * (lead - Math.min(0, trackOffset));

  if (sourceSide === targetSide) {
    const loopDirection = sourceSide === "right" ? 1 : -1;
    const outerX = (sourceSide === "right" ? Math.max(source.x, target.x) : Math.min(source.x, target.x)) + loopDirection * (120 + Math.abs(trackOffset));
    return {
      path: `M ${source.x} ${source.y} L ${outerX} ${source.y} L ${outerX} ${target.y} L ${target.x} ${target.y}`,
      midpoint: { x: outerX, y: (source.y + target.y) / 2 },
    };
  }

  return {
    path: `M ${source.x} ${source.y} C ${sourceLeadX} ${source.y}, ${targetLeadX} ${target.y}, ${target.x} ${target.y}`,
    midpoint: { x: (sourceLeadX + targetLeadX) / 2, y: (source.y + target.y) / 2 },
  };
}

function distributeOffset(index: number, total: number, spread: number) {
  if (total <= 1) return 0;
  return -spread / 2 + (spread * index) / (total - 1);
}

function edgePath(source: GraphLayoutNode, target: GraphLayoutNode) {
  const sourceY = source.y + source.height / 2;
  const targetY = target.y + target.height / 2;
  if (source.lane === target.lane) {
    const sourceX = source.x + source.width;
    const targetX = target.x + target.width;
    const bendX = sourceX + 42 + Math.min(80, Math.abs(targetY - sourceY) * 0.18);
    return `M ${sourceX} ${sourceY} C ${bendX} ${sourceY}, ${bendX} ${targetY}, ${targetX} ${targetY}`;
  }
  if (target.x > source.x) {
    const sourceX = source.x + source.width;
    const targetX = target.x;
    const control = Math.max(60, (targetX - sourceX) * 0.45);
    return `M ${sourceX} ${sourceY} C ${sourceX + control} ${sourceY}, ${targetX - control} ${targetY}, ${targetX} ${targetY}`;
  }
  const sourceX = source.x;
  const targetX = target.x + target.width;
  const control = Math.max(70, (sourceX - targetX) * 0.45);
  return `M ${sourceX} ${sourceY} C ${sourceX - control} ${sourceY}, ${targetX + control} ${targetY}, ${targetX} ${targetY}`;
}

function pathMidpoint(source: GraphLayoutNode, target: GraphLayoutNode) {
  const y = (source.y + source.height / 2 + target.y + target.height / 2) / 2;
  if (source.lane === target.lane) {
    return { x: source.x + source.width + 48, y };
  }
  return { x: (source.x + source.width / 2 + target.x + target.width / 2) / 2, y };
}

function edgeTone(edge: ContractEdge): EdgeTone {
  const protocol = String(edge.protocol ?? "").toLowerCase();
  if (edge.kind === "deployment") return EDGE_TONES.deploy;
  if (edge.layer === "http" || protocol.includes("http")) return EDGE_TONES.http;
  if (edge.layer === "ros" || protocol.includes("ros")) return EDGE_TONES.ros;
  if (edge.layer === "data" || protocol.includes("mongo") || protocol.includes("json")) return EDGE_TONES.data;
  return EDGE_TONES.system;
}

function nodeTone(node: ContractNode) {
  if (node.kind === "http_endpoint") return { color: EDGE_TONES.http.color, border: "#bfdbfe", fill: "#ffffff", selectedFill: EDGE_TONES.http.bg };
  if (node.kind === "ros_topic" || node.kind === "ros_service" || node.kind === "ros_type") return { color: EDGE_TONES.ros.color, border: "#fde68a", fill: "#ffffff", selectedFill: EDGE_TONES.ros.bg };
  if (node.kind === "json_schema" || node.kind === "mongo_collection") return { color: EDGE_TONES.data.color, border: "#cbd5e1", fill: "#ffffff", selectedFill: EDGE_TONES.data.bg };
  if (node.kind === "container") return { color: EDGE_TONES.deploy.color, border: "#ddd6fe", fill: "#ffffff", selectedFill: EDGE_TONES.deploy.bg };
  if (node.layer === "data") return { color: EDGE_TONES.data.color, border: "#cbd5e1", fill: "#ffffff", selectedFill: EDGE_TONES.data.bg };
  return { color: EDGE_TONES.system.color, border: "#cbd5e1", fill: "#ffffff", selectedFill: EDGE_TONES.system.bg };
}

function nodeColor(node: ContractNode) {
  if (node.kind === "component") return "#0f766e";
  if (node.kind === "http_endpoint") return "#2563eb";
  if (node.kind === "ros_topic" || node.kind === "ros_service") return "#d97706";
  if (node.kind === "ros_type") return "#64748b";
  if (node.kind === "json_schema") return "#059669";
  if (node.kind === "mongo_collection") return "#475569";
  if (node.kind === "container") return "#7c3aed";
  return "#64748b";
}

function clipLabel(value: string, maxLength: number) {
  if (value.length <= maxLength) return value;
  return `${value.slice(0, Math.max(0, maxLength - 3))}...`;
}

function labelLines(value: string, maxLength: number) {
  const normalized = value.replace(/\s+/g, " ").trim();
  if (normalized.length <= maxLength) return [normalized];
  const firstBreak = bestBreak(normalized, maxLength);
  const first = normalized.slice(0, firstBreak).trim();
  const rest = normalized.slice(firstBreak).replace(/^[\s/]+/, "").trim();
  if (!rest) return [clipLabel(first, maxLength)];
  return [clipLabel(first, maxLength), clipLabel(rest, maxLength)];
}

function bestBreak(value: string, maxLength: number) {
  const candidates = [value.lastIndexOf(" ", maxLength), value.lastIndexOf("/", maxLength), value.lastIndexOf("_", maxLength), value.lastIndexOf("-", maxLength)].filter((index) => index > 8);
  if (candidates.length) return Math.max(...candidates);
  return maxLength;
}

function clamp(value: number, minimum: number, maximum: number) {
  return Math.max(minimum, Math.min(maximum, value));
}
