import { BoxSelect, Check, Hexagon, Layers, MousePointer2, Pencil, Target, Trash2, Undo2, X } from "lucide-react";
import type { Feature, FeatureCollection } from "geojson";
import { Fragment, useEffect, useMemo, useState } from "react";
import { CircleMarker, GeoJSON, MapContainer, Marker, Pane, Polygon, Polyline, Popup, TileLayer, Tooltip, useMap, useMapEvents } from "react-leaflet";
import L from "leaflet";
import { Button } from "./components/ui/button";
import { Badge } from "./components/ui/badge";
import type { PlannerUpdateEvent, PlanningScenario } from "./api";
import type { Agent, LonLat, MapFeature, MissionConfig, TaskPlan } from "./types";
import { missionDestinationPoints } from "./mission";

type MapViewProps = {
  agents: Agent[];
  features: MapFeature[];
  geojson?: FeatureCollection;
  osmRoads?: FeatureCollection;
  scenarioRoads?: FeatureCollection;
  mission?: MissionConfig;
  taskPlan?: TaskPlan;
  plannerState?: PlannerUpdateEvent;
  planningScenario?: PlanningScenario;
  selectedFeatureId?: string;
  focusFeatureIds?: string[];
  focusPoints?: LonLat[];
  focusNonce?: number;
  focusPointsNonce?: number;
  focusView?: { view: MapViewport; nonce: number };
  resetDraftNonce?: number;
  placingAgentName?: string;
  onPlaceAgent?: (point: LonLat) => void;
  onViewportChange?: (view: MapViewport) => void;
  onCreateFeature: (feature: DraftMapFeature) => void;
  onUpdateFeature: (featureId: string, feature: DraftMapFeature) => void;
  onRemoveFeature: (feature: MapFeature) => void;
  onSetObjective: (feature: MapFeature) => void;
  onAddFeatureToMission: (feature: MapFeature) => void;
  missionComposerActive: boolean;
  onSelectFeature: (featureId: string) => void;
  onClearSelection: () => void;
};

export type DraftMapFeature = {
  name: string;
  feature_type: string;
  geometry_type: "Point" | "LineString" | "Polygon";
  coordinates: LonLat | LonLat[] | LonLat[][];
};

type MapViewport = {
  center: LonLat;
  zoom: number;
};

const center: [number, number] = [50.8442, 4.3921];
const featureTypeOptions = ["objective", "road", "geofence", "workspace", "risk"] as const;
const geometryByFeatureType: Record<(typeof featureTypeOptions)[number], DraftMapFeature["geometry_type"]> = {
  objective: "Point",
  road: "LineString",
  geofence: "Polygon",
  workspace: "Polygon",
  risk: "Polygon",
};
type DrawingMode = "vertices" | "rectangle";
const OSM_ROAD_PANE_Z_INDEX = 320;
const MAP_ROAD_FEATURE_PANE_Z_INDEX = 340;
const MAP_FEATURE_PANE_Z_INDEX = 460;
const OSM_ROAD_STYLE = {
  majorColor: "#424d50",
  minorColor: "#90adb3",
  opacity: 0.38,
  importedOpacity: 0.92,
  scenarioOpacity: 0.82,
  haloColor: "#0f172a",
  haloOpacity: 0.16,
};
const OSM_ROAD_STYLE_KEY = Object.values(OSM_ROAD_STYLE).join("-");

export function MapView({
  agents,
  features,
  geojson,
  osmRoads,
  scenarioRoads,
  mission,
  taskPlan,
  plannerState,
  planningScenario,
  selectedFeatureId,
  focusFeatureIds,
  focusPoints,
  focusNonce,
  focusPointsNonce,
  focusView,
  resetDraftNonce,
  placingAgentName,
  onPlaceAgent,
  onViewportChange,
  onCreateFeature,
  onUpdateFeature,
  onRemoveFeature,
  onSetObjective,
  onAddFeatureToMission,
  missionComposerActive,
  onSelectFeature,
  onClearSelection,
}: MapViewProps) {
  const [drawing, setDrawing] = useState(false);
  const [draft, setDraft] = useState<LonLat[]>([]);
  const [drawingMode, setDrawingMode] = useState<DrawingMode>("vertices");
  const [featureType, setFeatureType] = useState<(typeof featureTypeOptions)[number]>("objective");
  const [featureName, setFeatureName] = useState("");
  const [redrawFeatureId, setRedrawFeatureId] = useState<string | undefined>();
  const [showOsmRoads, setShowOsmRoads] = useState(true);
  const [featurePicker, setFeaturePicker] = useState<{ position: L.LatLng; features: MapFeature[] } | undefined>();
  const osmRoadCount = osmRoads?.features.length ?? 0;
  const scenarioRoadCount = scenarioRoads?.features.length ?? 0;
  const geometryType = geometryByFeatureType[featureType];
  const selectedFeature = features.find((feature) => feature.feature_id === selectedFeatureId);
  const selectedIsUser = selectedFeature?.properties?.source === "user";
  const placingVehicle = Boolean(onPlaceAgent);
  const rectangleDrawing = drawing && geometryType === "Polygon" && drawingMode === "rectangle";

  const trajectories = useMemo(() => plannedTrajectories(agents, taskPlan, plannerState, mission?.mission_id), [agents, taskPlan, plannerState, mission?.mission_id]);
  const scenarioRoute = useMemo(() => (planningScenario?.route ?? []).filter(isLonLat), [planningScenario]);
  const objectivePoints = useMemo(() => (mission ? missionDestinationPoints(mission, features) : []), [features, mission]);
  const roadGeojson = useMemo(() => filterGeojsonFeatures(geojson, isRoadFeature), [geojson]);
  const foregroundGeojson = useMemo(() => filterGeojsonFeatures(geojson, (feature) => !isRoadFeature(feature)), [geojson]);
  const geojsonRenderKey = useMemo(() => {
    const ids = geojson?.features.map((feature) => String(feature.properties?.feature_id ?? feature.id ?? "")).join("|") ?? "empty";
    return `${ids}-${selectedFeatureId ?? "none"}-${OSM_ROAD_STYLE_KEY}`;
  }, [geojson, selectedFeatureId]);

  useEffect(() => {
    if (!selectedFeature) return;
    setFeatureName(selectedFeature.name);
    const type = selectedFeature.feature_type as (typeof featureTypeOptions)[number];
    if (featureTypeOptions.includes(type)) setFeatureType(type);
  }, [selectedFeature?.feature_id]);

  useEffect(() => {
    setDrawing(false);
    setDraft([]);
    setRedrawFeatureId(undefined);
  }, [resetDraftNonce]);

  useEffect(() => {
    if (!placingVehicle) return;
    setDrawing(false);
    setDraft([]);
    setRedrawFeatureId(undefined);
    setFeaturePicker(undefined);
  }, [placingVehicle]);

  function addDraftPoint(point: LonLat) {
    setDraft((points) => (geometryType === "Point" ? [point] : [...points, point]));
  }

  function selectFeatureType(type: (typeof featureTypeOptions)[number]) {
    setFeatureType(type);
    setDraft([]);
    setDrawing(false);
    setRedrawFeatureId(undefined);
    setDrawingMode("vertices");
  }

  function selectDrawingMode(mode: DrawingMode) {
    setDrawingMode(mode);
    setDraft([]);
  }

  function startDrawing() {
    setFeaturePicker(undefined);
    setDraft([]);
    setDrawing(true);
  }

  function cancelDrawing() {
    setDrawing(false);
    setDraft([]);
    setRedrawFeatureId(undefined);
  }

  function undoDraftPoint() {
    setDraft((points) => points.slice(0, -1));
  }

  function completeDraft() {
    if (!draftIsComplete(draft, geometryType)) return;
    const coordinates = draftCoordinates(draft, geometryType);
    const feature = {
      name: featureName.trim(),
      feature_type: featureType,
      geometry_type: geometryType,
      coordinates,
    };
    if (redrawFeatureId) onUpdateFeature(redrawFeatureId, feature);
    else onCreateFeature(feature);
    setDraft([]);
    setFeatureName("");
    setDrawing(false);
    setRedrawFeatureId(undefined);
  }

  function startRedrawSelectedFeature() {
    if (!selectedFeature || !selectedIsUser) return;
    const type = selectedFeature.feature_type as (typeof featureTypeOptions)[number];
    if (featureTypeOptions.includes(type)) setFeatureType(type);
    setFeatureName(selectedFeature.name);
    setDraft([]);
    setDrawingMode("vertices");
    setRedrawFeatureId(selectedFeature.feature_id);
    setDrawing(true);
  }

  function selectFeatureFromStack(featureId: string) {
    onSelectFeature(featureId);
    setFeaturePicker(undefined);
  }

  return (
    <section className="flex min-h-0 min-w-0 flex-1 flex-col border-r border-border bg-panel">
      <div className="shrink-0 border-b border-border bg-panel">
        <div className="flex min-h-11 flex-wrap items-center justify-between gap-2 px-3 py-1.5">
          <div className="flex min-w-0 items-center gap-2">
            <Hexagon className="h-5 w-5 shrink-0 text-primary" />
            <h1 className="truncate text-sm font-semibold">C2 iMUGS2</h1>
            <Badge tone={placingVehicle || drawing ? "warn" : mission ? "ok" : "default"} className="shrink-0">
              {placingVehicle ? "placing" : drawing ? drawingStatus(draft, geometryType, drawingMode) : mission ? "mission" : "ready"}
            </Badge>
            {placingVehicle && placingAgentName && <span className="max-w-40 truncate text-xs text-muted-foreground">{placingAgentName}</span>}
          </div>
          <Button variant={showOsmRoads ? "secondary" : "ghost"} size="sm" onClick={() => setShowOsmRoads((value) => !value)} title="Toggle road overlay">
            <Layers className="h-4 w-4" />
            <span>Roads</span>
            {(osmRoadCount > 0 || scenarioRoadCount > 0) && <span className="text-[10px] opacity-70">{scenarioRoadCount || osmRoadCount}</span>}
          </Button>
        </div>

        <div className="flex min-h-12 flex-wrap items-center gap-1.5 border-t border-border bg-background/70 px-2 py-1.5">
          {selectedFeature ? (
            <>
              <div className="flex min-w-0 flex-1 basis-48 items-center gap-1.5">
                {selectedIsUser ? (
                  <input className="h-8 min-w-28 flex-1 rounded-md border border-border bg-panel px-2 text-xs outline-none focus:ring-2 focus:ring-ring" value={featureName} onChange={(event) => setFeatureName(event.target.value)} placeholder="Feature name" />
                ) : (
                  <span className="min-w-0 flex-1 truncate px-1 text-xs font-medium">{selectedFeature.name}</span>
                )}
                <Badge className="shrink-0">{selectedFeature.feature_type}</Badge>
              </div>
              {drawing && geometryType === "Polygon" && <DrawingModePicker mode={drawingMode} onChange={selectDrawingMode} />}
              {!missionComposerActive && canUseAsNavigationObjective(selectedFeature) && (
                <Button variant="outline" size="sm" onClick={() => onSetObjective(selectedFeature)} title="Use selected point as navigation objective">
                  <Target className="h-4 w-4" />
                  Objective
                </Button>
              )}
              {missionComposerActive && canAddFeatureToMission(selectedFeature) && (
                <Button variant="default" size="sm" onClick={() => onAddFeatureToMission(selectedFeature)} title={missionFeatureActionTitle(selectedFeature)}>
                  <Target className="h-4 w-4" />
                  {missionFeatureActionLabel(selectedFeature)}
                </Button>
              )}
              {selectedIsUser && !drawing && (
                <Button variant="outline" size="sm" onClick={() => onUpdateFeature(selectedFeature.feature_id, draftFromFeature(selectedFeature, featureName))} title="Save selected asset name">
                  <Check className="h-4 w-4" />
                  Save
                </Button>
              )}
              {selectedIsUser && (
                <Button variant={drawing ? "secondary" : "outline"} size="sm" onClick={drawing ? cancelDrawing : startRedrawSelectedFeature} title={drawing ? "Cancel redraw" : "Redraw selected asset geometry"}>
                  {drawing ? <X className="h-4 w-4" /> : <Pencil className="h-4 w-4" />}
                  {drawing ? "Cancel" : "Redraw"}
                </Button>
              )}
              {drawing && drawingMode === "vertices" && geometryType !== "Point" && (
                <Button variant="ghost" size="icon" disabled={draft.length === 0} onClick={undoDraftPoint} title="Undo last point">
                  <Undo2 className="h-4 w-4" />
                </Button>
              )}
              {redrawFeatureId === selectedFeature.feature_id && drawing && (
                <Button variant="default" size="sm" disabled={!draftIsComplete(draft, geometryType)} onClick={completeDraft} title="Apply redrawn geometry">
                  <Check className="h-4 w-4" />
                  Apply
                </Button>
              )}
              {selectedIsUser && !drawing && (
                <Button variant="outline" size="icon" onClick={() => onRemoveFeature(selectedFeature)} title="Remove selected asset">
                  <Trash2 className="h-4 w-4" />
                </Button>
              )}
              <Button variant="ghost" size="icon" onClick={() => { cancelDrawing(); onClearSelection(); }} title="Clear selection">
                <X className="h-4 w-4" />
              </Button>
            </>
          ) : (
            <>
              <select className="h-8 min-w-28 rounded-md border border-border bg-panel px-2 text-xs outline-none focus:ring-2 focus:ring-ring" value={featureType} onChange={(event) => selectFeatureType(event.target.value as (typeof featureTypeOptions)[number])} aria-label="Feature type">
                {featureTypeOptions.map((option) => <option key={option} value={option}>{featureTypeLabel(option)}</option>)}
              </select>
              <input className="h-8 min-w-28 flex-1 basis-32 rounded-md border border-border bg-panel px-2 text-xs outline-none focus:ring-2 focus:ring-ring" value={featureName} onChange={(event) => setFeatureName(event.target.value)} placeholder="Feature name" />
              {geometryType === "Polygon" && <DrawingModePicker mode={drawingMode} onChange={selectDrawingMode} />}
              <Button variant={drawing ? "secondary" : "outline"} size="sm" onClick={drawing ? cancelDrawing : startDrawing} title={drawing ? "Cancel drawing" : drawingActionHint(geometryType, drawingMode)}>
                {drawing ? <X className="h-4 w-4" /> : drawingMode === "rectangle" && geometryType === "Polygon" ? <BoxSelect className="h-4 w-4" /> : <Pencil className="h-4 w-4" />}
                {drawing ? "Cancel" : "Draw"}
              </Button>
              {drawing && drawingMode === "vertices" && geometryType !== "Point" && (
                <Button variant="ghost" size="icon" disabled={draft.length === 0} onClick={undoDraftPoint} title="Undo last point">
                  <Undo2 className="h-4 w-4" />
                </Button>
              )}
              {drawing && (
                <Button variant="ghost" size="icon" disabled={draft.length === 0} onClick={() => setDraft([])} title="Clear drawing">
                  <Trash2 className="h-4 w-4" />
                </Button>
              )}
              <Button variant="default" size="sm" disabled={!draftIsComplete(draft, geometryType)} onClick={completeDraft} title="Create feature">
                <Check className="h-4 w-4" />
                Create
              </Button>
            </>
          )}
        </div>
      </div>

      <div className="relative min-h-0 flex-1">
        <MapContainer center={center} zoom={18} maxZoom={22} className="h-full w-full" scrollWheelZoom>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            maxNativeZoom={19}
            maxZoom={22}
          />
          {showOsmRoads && osmRoads && (
            <Pane name="osm-road-reference" style={{ zIndex: OSM_ROAD_PANE_Z_INDEX }}>
              <GeoJSON key={`osm-halo-${osmRoads.features.length}-${OSM_ROAD_STYLE_KEY}`} data={osmRoads} style={styleOsmRoadHalo} interactive={false} />
              <GeoJSON key={`osm-center-${osmRoads.features.length}-${OSM_ROAD_STYLE_KEY}`} data={osmRoads} style={styleOsmRoad} interactive={false} onEachFeature={onEachOsmRoad} />
            </Pane>
          )}
          {roadGeojson && (
            <Pane name="map-road-features" style={{ zIndex: MAP_ROAD_FEATURE_PANE_Z_INDEX }}>
              <GeoJSON
                key={`road-${geojsonRenderKey}`}
                data={roadGeojson}
                style={(feature) => styleFeature(feature, selectedFeatureId)}
                pointToLayer={(feature, latlng) => pointToLayer(feature, latlng, selectedFeatureId)}
                onEachFeature={onEachFeature}
              />
            </Pane>
          )}
          {foregroundGeojson && (
            <Pane name="map-features" style={{ zIndex: MAP_FEATURE_PANE_Z_INDEX }}>
              <GeoJSON
                key={`foreground-${geojsonRenderKey}`}
                data={foregroundGeojson}
                style={(feature) => styleFeature(feature, selectedFeatureId)}
                pointToLayer={(feature, latlng) => pointToLayer(feature, latlng, selectedFeatureId)}
                onEachFeature={onEachFeature}
              />
            </Pane>
          )}
          {showOsmRoads && scenarioRoads && scenarioRoads.features.length > 0 && (
            <Pane name="scenario-road-section" style={{ zIndex: MAP_ROAD_FEATURE_PANE_Z_INDEX }}>
              <GeoJSON key={`scenario-roads-${scenarioRoads.features.length}-${OSM_ROAD_STYLE_KEY}`} data={scenarioRoads} style={styleScenarioRoad} onEachFeature={onEachScenarioRoad} />
            </Pane>
          )}
          <MapResizeBridge />
          <MapInteractionMode drawing={drawing} rectangleDrawing={rectangleDrawing} placingVehicle={placingVehicle} />
          <MapViewportBridge focusView={focusView} onViewportChange={onViewportChange} />
          <FitFeatureBounds features={features} focusFeatureIds={focusFeatureIds} focusPoints={focusPoints} focusNonce={focusNonce} focusPointsNonce={focusPointsNonce} />
          <PlaceAgentClickLayer enabled={placingVehicle} onPlaceAgent={onPlaceAgent ?? noopPlaceAgent} />
          <FeatureClickLayer
            enabled={!drawing && !placingVehicle}
            features={features}
            onSingleFeature={selectFeatureFromStack}
            onFeatureStack={(position, stack) => setFeaturePicker({ position, features: stack })}
            onEmpty={() => setFeaturePicker(undefined)}
          />
          <DraftClickLayer enabled={drawing && !rectangleDrawing && !placingVehicle} onAddPoint={addDraftPoint} />
          <RectangleDraftLayer enabled={rectangleDrawing && !placingVehicle} onDraftChange={setDraft} />

          {featurePicker && (
            <Popup position={featurePicker.position} eventHandlers={{ remove: () => setFeaturePicker(undefined) }}>
              <div className="w-56 space-y-2 text-xs">
                <div className="font-semibold">Select feature</div>
                <div className="max-h-56 space-y-1 overflow-auto">
                  {featurePicker.features.map((feature) => (
                    <button
                      key={feature.feature_id}
                      className={`w-full rounded-sm border px-2 py-1.5 text-left hover:bg-muted ${feature.feature_id === selectedFeatureId ? "border-primary bg-muted" : "border-border"}`}
                      onClick={(event) => {
                        event.stopPropagation();
                        selectFeatureFromStack(feature.feature_id);
                      }}
                    >
                      <div className="truncate font-medium">{feature.name}</div>
                      <div className="truncate text-muted-foreground">{feature.feature_type} · {feature.geometry.type}</div>
                    </button>
                  ))}
                </div>
              </div>
            </Popup>
          )}

          {draft.length === 1 && geometryType === "Point" && (
            <CircleMarker center={toLatLng(draft[0])} radius={7} pathOptions={{ color: "#0f766e", fillColor: "#14b8a6", fillOpacity: 0.9, weight: 2 }}>
              <Tooltip permanent>{featureType}</Tooltip>
            </CircleMarker>
          )}
          {draft.length > 1 && (
            <Polyline positions={draft.map(toLatLng)} pathOptions={{ color: "#0f766e", weight: 4, dashArray: "8 8" }}>
              <Tooltip permanent>{draft.length} points</Tooltip>
            </Polyline>
          )}
          {geometryType === "Polygon" && draft.length >= 3 && <Polygon positions={draft.map(toLatLng)} pathOptions={{ color: "#0f766e", fillColor: "#14b8a6", fillOpacity: 0.16, weight: 2 }} />}
          {drawing && geometryType !== "Point" && draft.map((point, index) => (
            <CircleMarker key={`draft-${index}`} center={toLatLng(point)} radius={4} pathOptions={{ color: "#0f766e", fillColor: "#ffffff", fillOpacity: 1, weight: 2 }} interactive={false} />
          ))}

          {objectivePoints.map((point, index) => (
            <CircleMarker key={`objective-${index}`} center={toLatLng(point)} radius={8} pathOptions={{ color: "#b45309", fillColor: "#f59e0b", fillOpacity: 0.9, weight: 3 }}>
              <Tooltip>Objective</Tooltip>
            </CircleMarker>
          ))}

          {trajectories.map((trajectory) => {
            return (
              <Fragment key={`route-${trajectory.agent.agent_id}`}>
                <Polyline positions={trajectory.path.map(toLatLng)} pathOptions={{ color: trajectory.color, weight: trajectory.source === "legacy" ? 5 : 4, dashArray: trajectory.source === "legacy" ? undefined : "10 8" }} />
                {trajectory.source === "legacy" &&
                  trajectory.path.map((point, index) => (
                    <CircleMarker key={`route-${trajectory.agent.agent_id}-${index}`} center={toLatLng(point)} radius={index === 0 || index === trajectory.path.length - 1 ? 5 : 3} pathOptions={{ color: trajectory.color, fillColor: "#ffffff", fillOpacity: 0.95, weight: 2 }}>
                      <Tooltip>{`Waypoint ${index + 1}`}</Tooltip>
                    </CircleMarker>
                  ))}
              </Fragment>
            );
          })}

          {planningScenario && scenarioRoute.length > 1 && (
            <Pane name="planning-scenario-debug" style={{ zIndex: 620 }}>
              <ScenarioRouteOverlay scenario={planningScenario} route={scenarioRoute} />
            </Pane>
          )}

          {agents.map((agent) => (
            <Marker key={agent.agent_id} position={toLatLng(agent.current_location)} icon={agentIcon("#1f2937")}>
              <Popup>
                <div className="text-sm">
                  <strong>{agent.name || agent.agent_id}</strong>
                  <br />
                  {agent.status}
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
        {drawing && (
          <div className="pointer-events-none absolute bottom-7 left-1/2 z-[700] max-w-[calc(100%-24px)] -translate-x-1/2 rounded-md border border-slate-700/20 bg-slate-950/85 px-3 py-2 text-center text-xs font-medium text-white shadow-lg backdrop-blur-sm">
            {drawingInstruction(geometryType, drawingMode)}
          </div>
        )}
      </div>
    </section>
  );
}

function DrawingModePicker({ mode, onChange }: { mode: DrawingMode; onChange: (mode: DrawingMode) => void }) {
  return (
    <div className="inline-flex h-8 shrink-0 items-center rounded-md border border-border bg-panel p-0.5" role="group" aria-label="Polygon drawing mode">
      <button
        type="button"
        className={`inline-flex h-7 items-center gap-1 rounded px-2 text-[11px] font-medium transition-colors ${mode === "vertices" ? "bg-muted text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"}`}
        aria-pressed={mode === "vertices"}
        onClick={() => onChange("vertices")}
        title="Place polygon corners one at a time"
      >
        <MousePointer2 className="h-3.5 w-3.5" />
        Points
      </button>
      <button
        type="button"
        className={`inline-flex h-7 items-center gap-1 rounded px-2 text-[11px] font-medium transition-colors ${mode === "rectangle" ? "bg-muted text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"}`}
        aria-pressed={mode === "rectangle"}
        onClick={() => onChange("rectangle")}
        title="Drag between opposite rectangle corners"
      >
        <BoxSelect className="h-3.5 w-3.5" />
        Rectangle
      </button>
    </div>
  );
}

function featureTypeLabel(type: (typeof featureTypeOptions)[number]) {
  if (type === "objective") return "Objective · point";
  if (type === "road") return "Road · line";
  return `${type[0].toUpperCase()}${type.slice(1)} · area`;
}

function drawingStatus(draft: LonLat[], geometryType: DraftMapFeature["geometry_type"], mode: DrawingMode) {
  if (geometryType === "Polygon" && mode === "rectangle") return draft.length ? "rectangle ready" : "drag rectangle";
  if (geometryType === "Point") return draft.length ? "point ready" : "place point";
  return `${draft.length} point${draft.length === 1 ? "" : "s"}`;
}

function drawingActionHint(geometryType: DraftMapFeature["geometry_type"], mode: DrawingMode) {
  if (geometryType === "Polygon" && mode === "rectangle") return "Draw a rectangle by dragging across the map";
  if (geometryType === "Point") return "Place a point on the map";
  return `Draw a ${geometryType.toLowerCase()} by placing points`;
}

function drawingInstruction(geometryType: DraftMapFeature["geometry_type"], mode: DrawingMode) {
  if (geometryType === "Polygon" && mode === "rectangle") return "Drag from one corner to the opposite corner";
  if (geometryType === "Point") return "Click the map to place the point";
  if (geometryType === "LineString") return "Click to add route points · use Undo to step back";
  return "Click each polygon corner · use Undo to step back";
}

function FitFeatureBounds({
  features,
  focusFeatureIds,
  focusPoints,
  focusNonce,
  focusPointsNonce,
}: {
  features: MapFeature[];
  focusFeatureIds?: string[];
  focusPoints?: LonLat[];
  focusNonce?: number;
  focusPointsNonce?: number;
}) {
  const map = useMap();
  useEffect(() => {
    if (!focusNonce && !focusPointsNonce) return;
    const focusIds = new Set(focusFeatureIds ?? []);
    const points = focusPoints?.length
      ? focusPoints
      : features
          .filter((feature) => focusIds.has(feature.feature_id))
          .flatMap((feature) => flattenLonLatPoints(feature.geometry.coordinates));
    if (!points.length) return;
    if (points.length === 1) {
      map.flyTo(toLatLng(points[0]), Math.max(map.getZoom(), 18), { duration: 0.35 });
      return;
    }
    const bounds = L.latLngBounds(points.map(toLatLng));
    if (bounds.isValid()) map.fitBounds(bounds, { padding: [44, 44], maxZoom: 19, animate: true, duration: 0.35 });
  }, [features, focusFeatureIds, focusNonce, focusPoints, focusPointsNonce, map]);
  return null;
}

function MapViewportBridge({
  focusView,
  onViewportChange,
}: {
  focusView?: { view: MapViewport; nonce: number };
  onViewportChange?: (view: MapViewport) => void;
}) {
  const map = useMap();

  function publishViewport() {
    if (!onViewportChange) return;
    const mapCenter = map.getCenter();
    onViewportChange({
      center: [Number(mapCenter.lng.toFixed(7)), Number(mapCenter.lat.toFixed(7))],
      zoom: map.getZoom(),
    });
  }

  useEffect(() => {
    publishViewport();
  }, [map, onViewportChange]);

  useEffect(() => {
    if (!focusView) return;
    map.flyTo(toLatLng(focusView.view.center), focusView.view.zoom, { duration: 0.35 });
  }, [focusView?.nonce, map]);

  useMapEvents({
    moveend: publishViewport,
    zoomend: publishViewport,
  });

  return null;
}

function MapResizeBridge() {
  const map = useMap();

  useEffect(() => {
    const container = map.getContainer();
    let frame: number | undefined;
    const observer = new ResizeObserver(() => {
      if (frame !== undefined) window.cancelAnimationFrame(frame);
      frame = window.requestAnimationFrame(() => map.invalidateSize({ animate: false, debounceMoveend: true }));
    });
    observer.observe(container);
    return () => {
      observer.disconnect();
      if (frame !== undefined) window.cancelAnimationFrame(frame);
    };
  }, [map]);

  return null;
}

function MapInteractionMode({ drawing, rectangleDrawing, placingVehicle }: { drawing: boolean; rectangleDrawing: boolean; placingVehicle: boolean }) {
  const map = useMap();

  useEffect(() => {
    const container = map.getContainer();
    container.classList.toggle("map-drawing-crosshair", drawing);
    container.classList.toggle("map-rectangle-drawing", rectangleDrawing);
    container.classList.toggle("map-placement-crosshair", placingVehicle);
    return () => {
      container.classList.remove("map-drawing-crosshair", "map-rectangle-drawing", "map-placement-crosshair");
    };
  }, [drawing, map, placingVehicle, rectangleDrawing]);

  return null;
}

function ScenarioRouteOverlay({ scenario, route }: { scenario: PlanningScenario; route: LonLat[] }) {
  const hasSelectedNodes = Boolean(scenario.selected_nodes) && route.length >= 3;
  const graphRoute = hasSelectedNodes ? route.slice(1, -1) : route;
  const startSnap = hasSelectedNodes ? route.slice(0, 2) : [];
  const endSnap = hasSelectedNodes ? route.slice(-2) : [];
  const metrics = scenario.metrics ?? {};
  return (
    <Fragment>
      {startSnap.length === 2 && (
        <Polyline positions={startSnap.map(toLatLng)} pathOptions={{ color: "#dc2626", weight: 6, opacity: 0.9, dashArray: "8 7", lineCap: "round", lineJoin: "round" }}>
          <Tooltip sticky>{`Start snap ${formatDebugMeters(metrics.start_snap_m)}`}</Tooltip>
        </Polyline>
      )}
      {graphRoute.length > 1 && (
        <Polyline positions={graphRoute.map(toLatLng)} pathOptions={{ color: "#7c3aed", weight: 6, opacity: 0.82, lineCap: "round", lineJoin: "round" }}>
          <Tooltip sticky>{`${scenario.label}: graph ${formatDebugMeters(metrics.graph_length_m ?? metrics.visible_length_m)}`}</Tooltip>
        </Polyline>
      )}
      {endSnap.length === 2 && (
        <Polyline positions={endSnap.map(toLatLng)} pathOptions={{ color: "#dc2626", weight: 6, opacity: 0.9, dashArray: "8 7", lineCap: "round", lineJoin: "round" }}>
          <Tooltip sticky>{`End snap ${formatDebugMeters(metrics.end_snap_m)}`}</Tooltip>
        </Polyline>
      )}
      {route.map((point, index) => {
        const endpoint = index === 0 || index === route.length - 1;
        return (
          <CircleMarker key={`scenario-${scenario.id}-${index}`} center={toLatLng(point)} radius={endpoint ? 7 : 4} pathOptions={{ color: endpoint ? "#111827" : "#7c3aed", fillColor: endpoint ? "#f97316" : "#ffffff", fillOpacity: 0.95, weight: 2 }}>
            <Tooltip>{endpoint ? (index === 0 ? "Scenario start" : "Scenario objective") : `Scenario graph node ${index}`}</Tooltip>
          </CircleMarker>
        );
      })}
    </Fragment>
  );
}

function DraftClickLayer({ enabled, onAddPoint }: { enabled: boolean; onAddPoint: (point: LonLat) => void }) {
  useMapEvents({
    click(event) {
      if (!enabled) return;
      onAddPoint([Number(event.latlng.lng.toFixed(7)), Number(event.latlng.lat.toFixed(7))]);
    },
  });
  return null;
}

function RectangleDraftLayer({ enabled, onDraftChange }: { enabled: boolean; onDraftChange: (points: LonLat[]) => void }) {
  const map = useMap();

  useEffect(() => {
    if (!enabled) return;
    const container = map.getContainer();
    const restoreDragging = map.dragging.enabled();
    let startLatLng: L.LatLng | undefined;
    let startPoint: L.Point | undefined;
    let pointerId: number | undefined;
    map.dragging.disable();

    function blockMapEvent(event: PointerEvent) {
      event.preventDefault();
      event.stopImmediatePropagation();
    }

    function pointerDown(event: PointerEvent) {
      if (!event.isPrimary || event.button !== 0) return;
      blockMapEvent(event);
      pointerId = event.pointerId;
      startPoint = map.mouseEventToContainerPoint(event);
      startLatLng = map.containerPointToLatLng(startPoint);
      onDraftChange([]);
      container.setPointerCapture?.(event.pointerId);
    }

    function pointerMove(event: PointerEvent) {
      if (pointerId !== event.pointerId || !startLatLng) return;
      blockMapEvent(event);
      const endLatLng = map.containerPointToLatLng(map.mouseEventToContainerPoint(event));
      onDraftChange(rectangleCorners(startLatLng, endLatLng));
    }

    function finishPointer(event: PointerEvent) {
      if (pointerId !== event.pointerId || !startLatLng || !startPoint) return;
      blockMapEvent(event);
      const endPoint = map.mouseEventToContainerPoint(event);
      const endLatLng = map.containerPointToLatLng(endPoint);
      onDraftChange(startPoint.distanceTo(endPoint) >= 5 ? rectangleCorners(startLatLng, endLatLng) : []);
      if (container.hasPointerCapture?.(event.pointerId)) container.releasePointerCapture(event.pointerId);
      startLatLng = undefined;
      startPoint = undefined;
      pointerId = undefined;
    }

    container.addEventListener("pointerdown", pointerDown, true);
    container.addEventListener("pointermove", pointerMove, true);
    container.addEventListener("pointerup", finishPointer, true);
    container.addEventListener("pointercancel", finishPointer, true);
    return () => {
      container.removeEventListener("pointerdown", pointerDown, true);
      container.removeEventListener("pointermove", pointerMove, true);
      container.removeEventListener("pointerup", finishPointer, true);
      container.removeEventListener("pointercancel", finishPointer, true);
      if (restoreDragging) map.dragging.enable();
    };
  }, [enabled, map, onDraftChange]);

  return null;
}

function rectangleCorners(start: L.LatLng, end: L.LatLng): LonLat[] {
  return [
    [start.lng, start.lat],
    [end.lng, start.lat],
    [end.lng, end.lat],
    [start.lng, end.lat],
  ].map(([lon, lat]) => [Number(lon.toFixed(7)), Number(lat.toFixed(7))]);
}

function PlaceAgentClickLayer({ enabled, onPlaceAgent }: { enabled: boolean; onPlaceAgent: (point: LonLat) => void }) {
  useMapEvents({
    click(event) {
      if (!enabled) return;
      onPlaceAgent([Number(event.latlng.lng.toFixed(7)), Number(event.latlng.lat.toFixed(7))]);
    },
  });
  return null;
}

function FeatureClickLayer({
  enabled,
  features,
  onSingleFeature,
  onFeatureStack,
  onEmpty,
}: {
  enabled: boolean;
  features: MapFeature[];
  onSingleFeature: (featureId: string) => void;
  onFeatureStack: (position: L.LatLng, features: MapFeature[]) => void;
  onEmpty: () => void;
}) {
  const map = useMapEvents({
    click(event) {
      if (!enabled) return;
      const hits = featuresAtLatLng(features, event.latlng, map);
      if (hits.length === 0) {
        onEmpty();
        return;
      }
      if (hits.length === 1) {
        onSingleFeature(hits[0].feature_id);
        return;
      }
      onFeatureStack(event.latlng, hits);
    },
  });
  return null;
}

function noopPlaceAgent() {
  // React-Leaflet hooks need a stable callable even while placement is inactive.
}

function filterGeojsonFeatures(collection: FeatureCollection | undefined, predicate: (feature: Feature) => boolean): FeatureCollection | undefined {
  if (!collection) return undefined;
  const features = collection.features.filter(predicate);
  return features.length ? { ...collection, features } : undefined;
}

function isRoadFeature(feature: Feature) {
  return String(feature.properties?.feature_type ?? "") === "road";
}

function styleFeature(feature?: Feature, selectedFeatureId?: string): L.PathOptions {
  const type = String(feature?.properties?.feature_type ?? "custom");
  const selected = selectedFeatureId && String(feature?.properties?.feature_id ?? feature?.id ?? "") === selectedFeatureId;
  const importedOsmRoad = feature?.properties?.import_source === "openstreetmap-overpass";
  if (selected) return { color: "#0f172a", fillColor: "#fde047", fillOpacity: 0.34, weight: 7 };
  if (type === "risk") return { color: "#b91c1c", fillColor: "#ef4444", fillOpacity: 0.22, weight: 2 };
  if (type === "road" && importedOsmRoad) return { color: OSM_ROAD_STYLE.majorColor, weight: 6, opacity: OSM_ROAD_STYLE.importedOpacity, lineCap: "round", lineJoin: "round" };
  if (type === "road") return { color: "#5b6472", weight: 5, opacity: 0.82 };
  if (type === "objective") return { color: "#b45309", fillColor: "#f59e0b", fillOpacity: 0.22, weight: 3 };
  if (type === "workspace" || type === "geofence") return { color: "#047857", fillColor: "#10b981", fillOpacity: 0.14, weight: 2 };
  return { color: "#2563eb", fillColor: "#60a5fa", fillOpacity: 0.18, weight: 2 };
}

function styleOsmRoad(feature?: Feature): L.PathOptions {
  const highway = String(feature?.properties?.highway ?? "");
  const major = /primary|secondary|tertiary|trunk/.test(highway);
  return { color: major ? OSM_ROAD_STYLE.majorColor : OSM_ROAD_STYLE.minorColor, weight: major ? 4 : 3, opacity: OSM_ROAD_STYLE.opacity, dashArray: "8 7", lineCap: "round", lineJoin: "round" };
}

function styleOsmRoadHalo(feature?: Feature): L.PathOptions {
  const highway = String(feature?.properties?.highway ?? "");
  const major = /primary|secondary|tertiary|trunk/.test(highway);
  return { color: OSM_ROAD_STYLE.haloColor, weight: major ? 7 : 5, opacity: OSM_ROAD_STYLE.haloOpacity, lineCap: "round", lineJoin: "round" };
}

function styleScenarioRoad(feature?: Feature): L.PathOptions {
  const highway = String(feature?.properties?.highway ?? "");
  const major = /primary|secondary|tertiary|trunk/.test(highway);
  return { color: major ? OSM_ROAD_STYLE.majorColor : OSM_ROAD_STYLE.minorColor, weight: major ? 5 : 4, opacity: OSM_ROAD_STYLE.scenarioOpacity, lineCap: "round", lineJoin: "round" };
}

function pointToLayer(feature: Feature, latlng: L.LatLng, selectedFeatureId?: string) {
  const options = styleFeature(feature, selectedFeatureId);
  const selected = selectedFeatureId && String(feature.properties?.feature_id ?? feature.id ?? "") === selectedFeatureId;
  return L.circleMarker(latlng, { ...options, radius: selected ? 10 : 7 });
}

function onEachFeature(feature: Feature, layer: L.Layer) {
  const name = feature.properties?.name ?? feature.properties?.feature_id ?? "feature";
  const type = feature.properties?.feature_type ?? "custom";
  layer.bindTooltip(`${name} (${type})`);
}

function onEachOsmRoad(feature: Feature, layer: L.Layer) {
  const name = feature.properties?.name ?? feature.properties?.highway ?? "OSM road";
  layer.bindTooltip(`OSM ${name}`);
}

function onEachScenarioRoad(feature: Feature, layer: L.Layer) {
  const name = feature.properties?.name ?? feature.properties?.highway ?? "road";
  layer.bindTooltip(`${name} (world road section)`);
}

function canUseAsNavigationObjective(feature: MapFeature) {
  return feature.feature_type === "objective" && feature.geometry.type === "Point";
}

function canAddFeatureToMission(feature: MapFeature) {
  if (feature.feature_type === "objective") return feature.geometry.type === "Point";
  if (feature.feature_type === "road") return feature.geometry.type === "LineString";
  if (feature.feature_type === "geofence" || feature.feature_type === "workspace" || feature.feature_type === "risk") return feature.geometry.type === "Polygon";
  return false;
}

function missionFeatureActionLabel(feature: MapFeature) {
  if (feature.feature_type === "objective") return "Set objective";
  if (feature.feature_type === "road") return "Use route";
  if (feature.feature_type === "risk") return "Use LOS";
  return "Use geofence";
}

function missionFeatureActionTitle(feature: MapFeature) {
  if (feature.feature_type === "objective") return "Write this point into objective.geometries";
  if (feature.feature_type === "road") return "Use this LineString as a route patrol objective";
  if (feature.feature_type === "risk") return "Write this polygon into objective.line_of_sight";
  return "Write this polygon into transit.geofence";
}

function draftFromFeature(feature: MapFeature, name: string): DraftMapFeature {
  const geometryType = feature.geometry.type as DraftMapFeature["geometry_type"];
  return {
    name: name.trim() || feature.name,
    feature_type: feature.feature_type,
    geometry_type: geometryType,
    coordinates: feature.geometry.coordinates as DraftMapFeature["coordinates"],
  };
}

function draftIsComplete(draft: LonLat[], geometryType: DraftMapFeature["geometry_type"]) {
  if (geometryType === "Point") return draft.length === 1;
  if (geometryType === "LineString") return draft.length >= 2;
  return draft.length >= 3;
}

function draftCoordinates(draft: LonLat[], geometryType: DraftMapFeature["geometry_type"]): DraftMapFeature["coordinates"] {
  if (geometryType === "Point") return draft[0];
  if (geometryType === "LineString") return draft;
  const ring = [...draft];
  if (ring.length > 0) ring.push(ring[0]);
  return [ring];
}

function plannedTrajectories(agents: Agent[], taskPlan?: TaskPlan, plannerState?: PlannerUpdateEvent, missionId?: string) {
  const colors = ["#0f766e", "#2563eb", "#9333ea", "#ca8a04"];

  if (plannerState?.paths && (!plannerState.mission_id || (missionId && plannerState.mission_id === missionId))) {
    return Object.entries(plannerState.paths).flatMap(([agentId, path], index) => {
      const agent = agents.find((candidate) => normalizeUuidish(candidate.agent_id) === normalizeUuidish(agentId));
      const cleanPath = path.filter(isLonLat);
      if (!agent || cleanPath.length === 0) return [];
      return [{ agent, path: cleanPath, color: colors[index % colors.length], source: "legacy" as const }];
    });
  }

  if (!taskPlan) return [];
  return Object.entries(taskPlan.tasks).flatMap(([agentId, task], index) => {
    const agent = agents.find((candidate) => candidate.agent_id === agentId);
    const target = task.objectives[0]?.primitives[0]?.parameters?.coordinates;
    if (!agent || !target) return [];
    return [{ agent, path: [agent.current_location, target], color: colors[index % colors.length], source: "preview" as const }];
  });
}

function toLatLng(point: LonLat): [number, number] {
  return [point[1], point[0]];
}

function isLonLat(value: unknown): value is LonLat {
  return Array.isArray(value) && value.length >= 2 && typeof value[0] === "number" && typeof value[1] === "number";
}

function flattenLonLatPoints(value: unknown): LonLat[] {
  if (!Array.isArray(value)) return [];
  if (isLonLat(value)) return [[value[0], value[1]]];
  return value.flatMap((item) => flattenLonLatPoints(item));
}

function featuresAtLatLng(features: MapFeature[], latlng: L.LatLng, map: L.Map) {
  const point = map.latLngToLayerPoint(latlng);
  const lonlat: LonLat = [latlng.lng, latlng.lat];
  return features
    .filter((feature) => featureContainsPoint(feature, lonlat, point, map))
    .sort((left, right) => featurePickPriority(left) - featurePickPriority(right));
}

function featureContainsPoint(feature: MapFeature, lonlat: LonLat, point: L.Point, map: L.Map) {
  if (feature.geometry.type === "Point") {
    const coordinate = feature.geometry.coordinates;
    if (!isLonLat(coordinate)) return false;
    return point.distanceTo(map.latLngToLayerPoint(toLatLng(coordinate))) <= 14;
  }
  if (feature.geometry.type === "LineString") {
    const points = flattenLonLatPoints(feature.geometry.coordinates);
    return lineStringsFromPoints(points).some((line) => pointNearLine(point, line, map, 12));
  }
  if (feature.geometry.type === "Polygon") {
    return polygonsFromCoordinates(feature.geometry.coordinates).some((polygon) => pointInPolygon(lonlat, polygon) || pointNearPolygonBoundary(point, polygon, map, 10));
  }
  return false;
}

function lineStringsFromPoints(points: LonLat[]) {
  return points.length >= 2 ? [points] : [];
}

function polygonsFromCoordinates(value: unknown): LonLat[][] {
  if (!Array.isArray(value)) return [];
  if (value.length > 0 && Array.isArray(value[0]) && isLonLat(value[0][0])) {
    return [value[0] as LonLat[]];
  }
  return [];
}

function pointNearLine(point: L.Point, line: LonLat[], map: L.Map, tolerancePx: number) {
  for (let index = 0; index < line.length - 1; index += 1) {
    const start = map.latLngToLayerPoint(toLatLng(line[index]));
    const end = map.latLngToLayerPoint(toLatLng(line[index + 1]));
    if (distanceToSegment(point, start, end) <= tolerancePx) return true;
  }
  return false;
}

function pointNearPolygonBoundary(point: L.Point, polygon: LonLat[], map: L.Map, tolerancePx: number) {
  if (polygon.length < 2) return false;
  for (let index = 0; index < polygon.length; index += 1) {
    const start = polygon[index];
    const end = polygon[(index + 1) % polygon.length];
    if (distanceToSegment(point, map.latLngToLayerPoint(toLatLng(start)), map.latLngToLayerPoint(toLatLng(end))) <= tolerancePx) return true;
  }
  return false;
}

function distanceToSegment(point: L.Point, start: L.Point, end: L.Point) {
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  if (dx === 0 && dy === 0) return point.distanceTo(start);
  const ratio = Math.max(0, Math.min(1, ((point.x - start.x) * dx + (point.y - start.y) * dy) / (dx * dx + dy * dy)));
  const projection = L.point(start.x + ratio * dx, start.y + ratio * dy);
  return point.distanceTo(projection);
}

function pointInPolygon(point: LonLat, polygon: LonLat[]) {
  let inside = false;
  const [lon, lat] = point;
  for (let index = 0, previous = polygon.length - 1; index < polygon.length; previous = index, index += 1) {
    const [lon1, lat1] = polygon[index];
    const [lon2, lat2] = polygon[previous];
    if ((lat1 > lat) !== (lat2 > lat)) {
      const intersectLon = ((lon2 - lon1) * (lat - lat1)) / ((lat2 - lat1) || 1e-12) + lon1;
      if (lon < intersectLon) inside = !inside;
    }
  }
  return inside;
}

function featurePickPriority(feature: MapFeature) {
  const geometryPriority = feature.geometry.type === "Point" ? 0 : feature.geometry.type === "LineString" ? 10 : 20;
  const typePriority = feature.feature_type === "objective" ? 0 : feature.feature_type === "road" ? 1 : feature.feature_type === "risk" ? 2 : feature.feature_type === "geofence" ? 3 : 4;
  return geometryPriority + typePriority;
}

function formatDebugMeters(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? `${value.toFixed(1)} m` : "n/a";
}

function normalizeUuidish(value: string) {
  return value.replace(/^agent_/, "").replace(/_/g, "-").toLowerCase();
}

function agentIcon(color: string) {
  return L.divIcon({
    className: "agent-marker",
    html: `<span style="background:${color}"></span>`,
    iconSize: [20, 20],
    iconAnchor: [10, 10],
  });
}
