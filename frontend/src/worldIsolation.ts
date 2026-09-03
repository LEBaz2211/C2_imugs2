import type { Feature, FeatureCollection } from "geojson";
import type { WorldBinding, WorldLaunchResult } from "./api";
import type { MapFeature } from "./types";

const EMPTY_COLLECTION: FeatureCollection = { type: "FeatureCollection", features: [] };
const WORLD_BINDING_IDENTITY_FIELDS = [
  "world_id",
  "world_version",
  "deployment_id",
  "map_collection",
  "content_hash",
  "map_feature_hash",
  "launch_id",
  "map_snapshot_token",
] as const;

export function geoJsonFeatureId(feature: Feature): string | undefined {
  const featureId = feature.properties?.feature_id ?? feature.id;
  return typeof featureId === "string" ? featureId : undefined;
}

export function projectDefinitionMapFeatures(
  features: MapFeature[],
  attachedFeatureIds: Iterable<string>,
): MapFeature[] {
  const attached = new Set(attachedFeatureIds);
  return features.filter((feature) => attached.has(feature.feature_id));
}

export function projectDefinitionGeojson(
  collection: FeatureCollection | undefined,
  attachedFeatureIds: Iterable<string>,
): FeatureCollection | undefined {
  if (!collection) return collection;
  const attached = new Set(attachedFeatureIds);
  return {
    ...collection,
    features: collection.features.filter((feature) => {
      const featureId = geoJsonFeatureId(feature);
      return featureId !== undefined && attached.has(featureId);
    }),
  };
}

export function deploymentIdentity(active: WorldLaunchResult | undefined): string {
  if (
    !active?.world_id
    || !active.deployment_id
    || !active.launch_id
    || !active.map_collection
    || !active.map_snapshot_token
  ) return "";
  return [
    active.deployment_id,
    active.launch_id,
    active.map_collection,
    active.map_snapshot_token,
  ].join(":");
}

export function worldBindingFromActiveWorld(active: WorldLaunchResult | undefined): WorldBinding | undefined {
  if (!active || WORLD_BINDING_IDENTITY_FIELDS.some((field) => !active[field])) return undefined;
  return {
    world_id: active.world_id ?? null,
    world_version: active.world_version ?? null,
    deployment_id: active.deployment_id ?? null,
    map_collection: active.map_collection ?? null,
    content_hash: active.content_hash ?? null,
    map_feature_hash: active.map_feature_hash ?? null,
    launch_id: active.launch_id ?? null,
    map_snapshot_token: active.map_snapshot_token ?? null,
    status: active.status,
    ready: active.ready,
  };
}

export function sameWorldBinding(left: WorldBinding | undefined, right: WorldBinding | undefined): boolean {
  if (!left || !right) return false;
  return WORLD_BINDING_IDENTITY_FIELDS.every((field) => left[field] === right[field]);
}

export function sameActiveWorldProjection(
  left: WorldLaunchResult | undefined,
  right: WorldLaunchResult | undefined,
): boolean {
  if (left === right) return true;
  if (!left || !right) return false;
  const leftIdentity = deploymentIdentity(left);
  const rightIdentity = deploymentIdentity(right);
  if (!leftIdentity || !rightIdentity) return JSON.stringify(left) === JSON.stringify(right);
  return leftIdentity === rightIdentity
    && left.status === right.status
    && left.ready === right.ready
    && left.message === right.message
    && left.error === right.error
    && JSON.stringify(left.map_view ?? null) === JSON.stringify(right.map_view ?? null)
    && JSON.stringify(left.live_features ?? null) === JSON.stringify(right.live_features ?? null);
}

export function projectActiveDeploymentGeojson(
  active: WorldLaunchResult | undefined,
): FeatureCollection {
  if (!deploymentIdentity(active)) return EMPTY_COLLECTION;
  const deploymentId = active?.deployment_id;
  const liveFeatures = (active?.live_features?.features ?? []).filter(
    (feature) => feature.properties?.deployment_id === deploymentId,
  );
  return {
    type: "FeatureCollection",
    features: [
      ...(active?.snapshot?.features ?? []),
      ...liveFeatures,
    ],
  };
}

export function mapFeaturesFromGeojson(collection: FeatureCollection): MapFeature[] {
  return collection.features.flatMap((feature) => {
    const featureId = geoJsonFeatureId(feature);
    if (!featureId || !feature.geometry || !("coordinates" in feature.geometry)) return [];
    const properties = { ...(feature.properties ?? {}) } as Record<string, unknown>;
    if (properties.source === "authoring") properties.source = "snapshot_authoring";
    return [{
      feature_id: featureId,
      name: typeof properties.name === "string" ? properties.name : featureId,
      feature_type: typeof properties.feature_type === "string" ? properties.feature_type : "custom",
      geometry: { type: feature.geometry.type, coordinates: feature.geometry.coordinates },
      properties,
    }];
  });
}
