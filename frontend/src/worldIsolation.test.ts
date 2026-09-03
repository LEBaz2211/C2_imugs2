import type { Feature, FeatureCollection } from "geojson";
import { describe, expect, it } from "vitest";
import type { WorldLaunchResult } from "./api";
import type { MapFeature } from "./types";
import {
  deploymentIdentity,
  projectActiveDeploymentGeojson,
  projectDefinitionGeojson,
  projectDefinitionMapFeatures,
  sameActiveWorldProjection,
  sameWorldBinding,
  worldBindingFromActiveWorld,
} from "./worldIsolation";

function point(featureId: string, deploymentId?: string): Feature {
  return {
    type: "Feature",
    id: featureId,
    properties: {
      feature_id: featureId,
      feature_type: "objective",
      ...(deploymentId ? { deployment_id: deploymentId } : {}),
    },
    geometry: { type: "Point", coordinates: [4, 50] },
  };
}

function active(
  deploymentId: string,
  snapshotFeatures: Feature[],
  liveFeatures: Feature[] = [],
  status: WorldLaunchResult["status"] = "ready",
): WorldLaunchResult {
  return {
    status,
    ready: status === "ready",
    message: status,
    world_id: "world-a",
    world_version: "version-a",
    deployment_id: deploymentId,
    launch_id: `launch-${deploymentId}`,
    map_collection: "snapshot-a",
    map_snapshot_token: `token-${deploymentId}`,
    snapshot: { type: "FeatureCollection", features: snapshotFeatures },
    live_features: { type: "FeatureCollection", features: liveFeatures },
  };
}

describe("world isolation projections", () => {
  const mapFeatures: MapFeature[] = ["objective-a", "objective-b", "risk-a"].map(
    (featureId) => ({
      feature_id: featureId,
      name: featureId,
      feature_type: featureId.startsWith("risk") ? "risk" : "objective",
      geometry: { type: "Point", coordinates: [4, 50] },
      properties: {},
    }),
  );
  const geojson: FeatureCollection = {
    type: "FeatureCollection",
    features: mapFeatures.map((feature) => point(feature.feature_id)),
  };

  it("projects only attached builder assets and switches cleanly from A to B", () => {
    expect(projectDefinitionMapFeatures(mapFeatures, ["objective-a", "risk-a"]).map((item) => item.feature_id))
      .toEqual(["objective-a", "risk-a"]);
    expect(projectDefinitionGeojson(geojson, ["objective-b"])?.features.map((item) => item.id))
      .toEqual(["objective-b"]);
  });

  it("uses only the active immutable snapshot and current-deployment overlays", () => {
    const runtime = active("deployment-b", [point("objective-b")], [
      point("overlay-b", "deployment-b"),
      point("overlay-from-a", "deployment-a"),
    ]);

    expect(projectActiveDeploymentGeojson(runtime).features.map((item) => item.id))
      .toEqual(["objective-b", "overlay-b"]);
  });

  it.each(["stale", "failed"] as const)("preserves the exact known snapshot while %s", (status) => {
    const runtime = active("deployment-a", [point("objective-a"), point("risk-a")], [], status);
    expect(projectActiveDeploymentGeojson(runtime).features.map((item) => item.id))
      .toEqual(["objective-a", "risk-a"]);
  });

  it("shows an empty runtime map when authoritative identity is incomplete", () => {
    const runtime = active("deployment-a", [point("objective-a")]);
    delete runtime.map_snapshot_token;
    expect(deploymentIdentity(runtime)).toBe("");
    expect(projectActiveDeploymentGeojson(runtime).features).toEqual([]);
  });

  it("changes the layer-reset key for a different deployment and a same-world redeployment", () => {
    const first = active("deployment-a", [point("objective-a")]);
    const second = active("deployment-b", [point("objective-b")]);
    const redeployed = active("deployment-c", [point("objective-a")]);

    expect(deploymentIdentity(first)).not.toBe(deploymentIdentity(second));
    expect(deploymentIdentity(first)).not.toBe(deploymentIdentity(redeployed));
  });

  it("keeps an unchanged active projection stable but accepts live-overlay and readiness changes", () => {
    const first = active("deployment-a", [point("objective-a")]);
    const identical = structuredClone(first);
    const withOverlay = active("deployment-a", [point("objective-a")], [point("overlay-a", "deployment-a")]);
    const stale = active("deployment-a", [point("objective-a")], [], "stale");

    expect(sameActiveWorldProjection(first, identical)).toBe(true);
    expect(sameActiveWorldProjection(first, withOverlay)).toBe(false);
    expect(sameActiveWorldProjection(first, stale)).toBe(false);
  });

  it("binds missions to the complete deployment identity", () => {
    const first = active("deployment-a", [point("objective-a")]);
    first.content_hash = "content-a";
    first.map_feature_hash = "features-a";
    const binding = worldBindingFromActiveWorld(first);

    expect(binding?.world_id).toBe("world-a");
    expect(sameWorldBinding(binding, binding)).toBe(true);
    expect(sameWorldBinding(binding, { ...binding!, deployment_id: "deployment-b" })).toBe(false);
    delete first.content_hash;
    expect(worldBindingFromActiveWorld(first)).toBeUndefined();
  });
});
