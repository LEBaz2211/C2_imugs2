import { Check, Hexagon, Layers, MousePointer2, Pencil, Trash2 } from "lucide-react";
import type { Feature, FeatureCollection } from "geojson";
import { Fragment, useMemo, useState } from "react";
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
  onSelectFeature: (featureId: string) => void;
};

export type DraftMapFeature = {
  name: string;
  feature_type: string;
  geometry_type: "Point" | "LineString" | "Polygon";
  coordinates: LonLat | LonLat[] | LonLat[][];
  use_as_objective: boolean;
};

const center: [number, number] = [50.8442, 4.3921];
const geometryOptions = ["Point", "LineString", "Polygon"] as const;
const featureTypeOptions = ["objective", "road", "geofence", "workspace", "risk", "custom"] as const;

export function MapView({ agents, features, geojson, osmRoads, mission, taskPlan, plannerState, selectedFeatureId, onCreateFeature, onSelectFeature }: MapViewProps) {
  const [drawing, setDrawing] = useState(false);
  const [draft, setDraft] = useState<LonLat[]>([]);
  const [geometryType, setGeometryType] = useState<DraftMapFeature["geometry_type"]>("Point");
  const [featureType, setFeatureType] = useState("objective");
  const [featureName, setFeatureName] = useState("");
  const [showOsmRoads, setShowOsmRoads] = useState(true);
  const osmRoadCount = osmRoads?.features.length ?? 0;

  const trajectories = useMemo(() => plannedTrajectories(agents, taskPlan, plannerState, mission?.mission_id), [agents, taskPlan, plannerState, mission?.mission_id]);
  const objectivePoints = useMemo(
    () => mission?.objective.geometries.flatMap((geometryRef) => destinationsForGeometryRef(geometryRef, features, mission.behavior)) ?? [],
    [features, mission],
  );

  function addDraftPoint(point: LonLat) {
    setDraft((points) => (geometryType === "Point" ? [point] : [...points, point]));
  }

  function completeDraft() {
    if (!draftIsComplete(draft, geometryType)) return;
    const coordinates = draftCoordinates(draft, geometryType);
    onCreateFeature({
      name: featureName.trim(),
      feature_type: featureType,
      geometry_type: geometryType,
      coordinates,
      use_as_objective: featureType === "objective",
    });
    setDraft([]);
    setFeatureName("");
    setDrawing(false);
  }

  return (
    <section className="flex min-h-0 flex-1 flex-col border-r border-border bg-panel">
      <div className="flex h-14 items-center justify-between border-b border-border px-4">
        <div className="flex items-center gap-2">
          <Hexagon className="h-5 w-5 text-primary" />
          <div>
            <h1 className="text-sm font-semibold">C2 iMUGS2 Mission Surface</h1>
            <p className="text-xs text-muted-foreground">Real map, legacy GeoJSON overlays, planned trajectories, and objective drawing.</p>
          </div>
        </div>
        <div className="flex min-w-0 items-center gap-2">
          <Badge tone={drawing ? "warn" : mission ? "ok" : "default"}>{drawing ? `${draft.length} pt` : mission ? "mission loaded" : "no mission"}</Badge>
          <Button variant={showOsmRoads ? "secondary" : "outline"} size="icon" onClick={() => setShowOsmRoads((value) => !value)} title="Toggle OSM road overlay">
            <Layers className="h-4 w-4" />
          </Button>
          <Badge tone={showOsmRoads && osmRoadCount > 0 ? "ok" : "default"} className="hidden whitespace-nowrap lg:inline-flex">
            {osmRoadCount > 0 ? `${osmRoadCount} OSM roads` : "roads loading"}
          </Badge>
          <select className="h-9 rounded-md border border-border bg-panel px-2 text-xs outline-none focus:ring-2 focus:ring-ring" value={geometryType} onChange={(event) => { setGeometryType(event.target.value as DraftMapFeature["geometry_type"]); setDraft([]); }}>
            {geometryOptions.map((option) => <option key={option}>{option}</option>)}
          </select>
          <select className="h-9 rounded-md border border-border bg-panel px-2 text-xs outline-none focus:ring-2 focus:ring-ring" value={featureType} onChange={(event) => setFeatureType(event.target.value)}>
            {featureTypeOptions.map((option) => <option key={option}>{option}</option>)}
          </select>
          <input className="h-9 w-32 rounded-md border border-border bg-panel px-2 text-xs outline-none focus:ring-2 focus:ring-ring" value={featureName} onChange={(event) => setFeatureName(event.target.value)} placeholder="name" />
          <Button variant={drawing ? "secondary" : "outline"} size="sm" onClick={() => setDrawing((value) => !value)} title="Draw feature">
            {drawing ? <MousePointer2 className="h-4 w-4" /> : <Pencil className="h-4 w-4" />}
            Draw
          </Button>
          <Button variant="outline" size="icon" onClick={() => setDraft([])} title="Clear draft polygon">
            <Trash2 className="h-4 w-4" />
          </Button>
          <Button variant="default" size="sm" disabled={!draftIsComplete(draft, geometryType)} onClick={completeDraft} title="Add feature">
            <Check className="h-4 w-4" />
            Add
          </Button>
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
