import { Check, Hexagon, Layers, MousePointer2, Pencil, Target, Trash2, X } from "lucide-react";
import type { Feature, FeatureCollection } from "geojson";
import { Fragment, useEffect, useMemo, useState } from "react";
import { CircleMarker, GeoJSON, MapContainer, Marker, Pane, Polygon, Polyline, Popup, TileLayer, Tooltip, useMapEvents } from "react-leaflet";
import L from "leaflet";
import { Button } from "./components/ui/button";
import { Badge } from "./components/ui/badge";
import type { PlannerUpdateEvent } from "./api";
import type { Agent, LonLat, MapFeature, MissionConfig, TaskPlan } from "./types";
import { destinationsForGeometryRef } from "./mission";

type MapViewProps = {
  agents: Agent[];
  features: MapFeature[];
  geojson?: FeatureCollection;
  osmRoads?: FeatureCollection;
  mission?: MissionConfig;
  taskPlan?: TaskPlan;
  plannerState?: PlannerUpdateEvent;
  selectedFeatureId?: string;
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
  use_as_objective: boolean;
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

export function MapView({ agents, features, geojson, osmRoads, mission, taskPlan, plannerState, selectedFeatureId, onCreateFeature, onUpdateFeature, onRemoveFeature, onSetObjective, onAddFeatureToMission, missionComposerActive, onSelectFeature, onClearSelection }: MapViewProps) {
  const [drawing, setDrawing] = useState(false);
  const [draft, setDraft] = useState<LonLat[]>([]);
  const [featureType, setFeatureType] = useState<(typeof featureTypeOptions)[number]>("objective");
  const [featureName, setFeatureName] = useState("");
  const [redrawFeatureId, setRedrawFeatureId] = useState<string | undefined>();
  const [showOsmRoads, setShowOsmRoads] = useState(true);
  const osmRoadCount = osmRoads?.features.length ?? 0;
  const geometryType = geometryByFeatureType[featureType];
  const selectedFeature = features.find((feature) => feature.feature_id === selectedFeatureId);
  const selectedIsUser = selectedFeature?.properties?.source === "user";

  const trajectories = useMemo(() => plannedTrajectories(agents, taskPlan, plannerState, mission?.mission_id), [agents, taskPlan, plannerState, mission?.mission_id]);
  const objectivePoints = useMemo(
    () => mission?.objective.geometries.flatMap((geometryRef) => destinationsForGeometryRef(geometryRef, features, mission.behavior)) ?? [],
    [features, mission],
  );

  useEffect(() => {
    if (!selectedFeature) return;
    setFeatureName(selectedFeature.name);
    const type = selectedFeature.feature_type as (typeof featureTypeOptions)[number];
    if (featureTypeOptions.includes(type)) setFeatureType(type);
  }, [selectedFeature?.feature_id]);

  function addDraftPoint(point: LonLat) {
    setDraft((points) => (geometryType === "Point" ? [point] : [...points, point]));
  }

  function completeDraft() {
    if (!draftIsComplete(draft, geometryType)) return;
    const coordinates = draftCoordinates(draft, geometryType);
    const feature = {
      name: featureName.trim(),
      feature_type: featureType,
      geometry_type: geometryType,
      coordinates,
      use_as_objective: featureType === "objective",
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
    setRedrawFeatureId(selectedFeature.feature_id);
    setDrawing(true);
  }

  return (
    <section className="flex min-h-0 flex-1 flex-col border-r border-border bg-panel">
      <div className="flex h-14 items-center justify-between gap-3 border-b border-border px-4">
        <div className="flex min-w-[150px] items-center gap-2">
          <Hexagon className="h-5 w-5 text-primary" />
          <h1 className="whitespace-nowrap text-sm font-semibold">C2 iMUGS2</h1>
        </div>
        <div className="flex min-w-0 items-center gap-2 overflow-hidden">
          <div className="flex items-center gap-1 rounded-md border border-border bg-background p-1">
            <Badge tone={drawing ? "warn" : mission ? "ok" : "default"}>{drawing ? `${draft.length} pt` : mission ? "mission" : "empty"}</Badge>
            <Button variant={showOsmRoads ? "secondary" : "ghost"} size="icon" onClick={() => setShowOsmRoads((value) => !value)} title="Toggle OSM road overlay">
              <Layers className="h-4 w-4" />
            </Button>
            <Badge tone={showOsmRoads && osmRoadCount > 0 ? "ok" : "default"} className="hidden whitespace-nowrap xl:inline-flex">
              {osmRoadCount > 0 ? `${osmRoadCount} roads` : "roads"}
            </Badge>
          </div>
          {selectedFeature ? (
            <div className="flex min-w-0 items-center gap-1 rounded-md border border-border bg-background p-1">
              <Badge tone={selectedIsUser ? "ok" : "default"} className="max-w-[220px] truncate">{selectedFeature.name}</Badge>
              <Badge>{selectedFeature.feature_type}</Badge>
              {selectedIsUser && <input className="h-9 w-32 rounded-md border border-border bg-panel px-2 text-xs outline-none focus:ring-2 focus:ring-ring" value={featureName} onChange={(event) => setFeatureName(event.target.value)} placeholder="name" />}
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
              {selectedIsUser && (
                <>
                  <Button variant="outline" size="sm" onClick={() => onUpdateFeature(selectedFeature.feature_id, draftFromFeature(selectedFeature, featureName))} title="Save selected asset name">
                    <Check className="h-4 w-4" />
                    Save
                  </Button>
                  <Button variant={redrawFeatureId === selectedFeature.feature_id ? "secondary" : "outline"} size="sm" onClick={startRedrawSelectedFeature} title="Redraw selected asset geometry">
                    <Pencil className="h-4 w-4" />
                    Redraw
                  </Button>
                  {redrawFeatureId === selectedFeature.feature_id && (
                    <Button variant="default" size="sm" disabled={!draftIsComplete(draft, geometryType)} onClick={completeDraft} title="Apply redrawn geometry">
                      <Check className="h-4 w-4" />
                      Apply
                    </Button>
                  )}
                  <Button variant="outline" size="icon" onClick={() => onRemoveFeature(selectedFeature)} title="Remove selected asset">
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </>
              )}
              <Button variant="ghost" size="icon" onClick={onClearSelection} title="Clear selection">
                <X className="h-4 w-4" />
              </Button>
            </div>
          ) : (
            <div className="flex min-w-0 items-center gap-1 rounded-md border border-border bg-background p-1">
              <select className="h-9 rounded-md border border-border bg-panel px-2 text-xs outline-none focus:ring-2 focus:ring-ring" value={featureType} onChange={(event) => { setFeatureType(event.target.value as (typeof featureTypeOptions)[number]); setDraft([]); }}>
                {featureTypeOptions.map((option) => <option key={option}>{option}</option>)}
              </select>
              <Badge>{geometryType}</Badge>
              <input className="h-9 w-32 rounded-md border border-border bg-panel px-2 text-xs outline-none focus:ring-2 focus:ring-ring" value={featureName} onChange={(event) => setFeatureName(event.target.value)} placeholder="name" />
              <Button variant={drawing ? "secondary" : "outline"} size="sm" onClick={() => setDrawing((value) => !value)} title="Draw feature">
                {drawing ? <MousePointer2 className="h-4 w-4" /> : <Pencil className="h-4 w-4" />}
                Draw
              </Button>
              <Button variant="outline" size="icon" onClick={() => setDraft([])} title="Clear draft">
                <Trash2 className="h-4 w-4" />
              </Button>
              <Button variant="default" size="sm" disabled={!draftIsComplete(draft, geometryType)} onClick={completeDraft} title="Add feature">
                <Check className="h-4 w-4" />
                Add
              </Button>
            </div>
          )}
        </div>
      </div>

      <div className="relative min-h-0 flex-1">
        <MapContainer center={center} zoom={18} className="h-full w-full" scrollWheelZoom>
          <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          {showOsmRoads && osmRoads && (
            <Pane name="osm-road-reference" style={{ zIndex: 360 }}>
              <GeoJSON key={`osm-halo-${osmRoads.features.length}`} data={osmRoads} style={styleOsmRoadHalo} interactive={false} />
              <GeoJSON key={`osm-center-${osmRoads.features.length}`} data={osmRoads} style={styleOsmRoad} onEachFeature={onEachOsmRoad} />
            </Pane>
          )}
          {geojson && (
            <GeoJSON
              key={`${JSON.stringify(geojson).length}-${selectedFeatureId ?? "none"}`}
              data={geojson}
              style={(feature) => styleFeature(feature, selectedFeatureId)}
              pointToLayer={(feature, latlng) => pointToLayer(feature, latlng, selectedFeatureId)}
              onEachFeature={(feature, layer) => onEachFeature(feature, layer, onSelectFeature)}
            />
          )}
          <DraftClickLayer enabled={drawing} onAddPoint={addDraftPoint} />

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
      </div>
    </section>
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

function styleFeature(feature?: Feature, selectedFeatureId?: string): L.PathOptions {
  const type = String(feature?.properties?.feature_type ?? "custom");
  const selected = selectedFeatureId && String(feature?.properties?.feature_id ?? feature?.id ?? "") === selectedFeatureId;
  if (selected) return { color: "#0f172a", fillColor: "#fde047", fillOpacity: 0.34, weight: 7 };
  if (type === "risk") return { color: "#b91c1c", fillColor: "#ef4444", fillOpacity: 0.22, weight: 2 };
  if (type === "road") return { color: "#5b6472", weight: 5, opacity: 0.82 };
  if (type === "objective") return { color: "#b45309", fillColor: "#f59e0b", fillOpacity: 0.22, weight: 3 };
  if (type === "workspace" || type === "geofence") return { color: "#047857", fillColor: "#10b981", fillOpacity: 0.14, weight: 2 };
  return { color: "#2563eb", fillColor: "#60a5fa", fillOpacity: 0.18, weight: 2 };
}

function styleOsmRoad(feature?: Feature): L.PathOptions {
  const highway = String(feature?.properties?.highway ?? "");
  const major = /primary|secondary|tertiary|trunk/.test(highway);
  return { color: major ? "#0891b2" : "#06b6d4", weight: major ? 4 : 3, opacity: 0.38, dashArray: "8 7", lineCap: "round", lineJoin: "round" };
}

function styleOsmRoadHalo(feature?: Feature): L.PathOptions {
  const highway = String(feature?.properties?.highway ?? "");
  const major = /primary|secondary|tertiary|trunk/.test(highway);
  return { color: "#0f172a", weight: major ? 7 : 5, opacity: 0.16, lineCap: "round", lineJoin: "round" };
}

function pointToLayer(feature: Feature, latlng: L.LatLng, selectedFeatureId?: string) {
  const options = styleFeature(feature, selectedFeatureId);
  const selected = selectedFeatureId && String(feature.properties?.feature_id ?? feature.id ?? "") === selectedFeatureId;
  return L.circleMarker(latlng, { ...options, radius: selected ? 10 : 7 });
}

function onEachFeature(feature: Feature, layer: L.Layer, onSelectFeature: (featureId: string) => void) {
  const name = feature.properties?.name ?? feature.properties?.feature_id ?? "feature";
  const type = feature.properties?.feature_type ?? "custom";
  const featureId = String(feature.properties?.feature_id ?? feature.id ?? "");
  layer.bindTooltip(`${name} (${type})`);
  if (featureId) {
    layer.on("click", () => onSelectFeature(featureId));
  }
}

function onEachOsmRoad(feature: Feature, layer: L.Layer) {
  const name = feature.properties?.name ?? feature.properties?.highway ?? "OSM road";
  layer.bindTooltip(`OSM ${name}`);
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
    use_as_objective: false,
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
