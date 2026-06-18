import type { Agent, MapFeature, MissionConfig } from "../types";

const legacyAgentId = "f9992bb3-9871-451f-90a0-9207eb9fe6c5";

export const agents: Agent[] = [
  {
    agent_id: legacyAgentId,
    name: "Themis Fr",
    vehicle_type: "UGV",
    status: "available",
    current_location: [4.392588, 50.844317],
    constraints: { max_speed: 4.5 },
    capabilities: ["waypoint_navigation", "coverage"],
  },
];

export const missionExamples: { id: string; name: string; behavior: number; vehicles: string[]; config: MissionConfig }[] = [
  {
    id: "simple_navigation_themis",
    name: "Themis simple navigation",
    behavior: 0,
    vehicles: [legacyAgentId],
    config: {
      schema_version: "1.0",
      mission_id: "85b6dc76-774c-4db8-a208-48c68ac6237d",
      phase: 1,
      name: "Themis simple navigation",
      behavior: 0,
      vehicles: [legacyAgentId],
      transit: {
        geofence: { feature_id: "dbfd7aea-2f43-4653-b62a-aa0cd8ef9e0e" },
        optimization: {
          road_usage: 1.0,
          energy: 0.8,
        },
        desired_vehicle_constraints: {
          max_speed: 4.0,
        },
      },
      objective: {
        geometries: [{ geometry: { geometry_type: "Point", coordinates: [4.39167, 50.84417] } }],
        vehicle_formation: 0,
        maximize_coverage: false,
      },
    },
  },
  {
    id: "parade_coverage_themis",
    name: "Themis parade coverage",
    behavior: 1,
    vehicles: [legacyAgentId],
    config: {
      schema_version: "1.0",
      mission_id: "9f94003b-4559-4afc-b00a-e292bf17eb2d",
      phase: 1,
      name: "Themis parade coverage",
      behavior: 1,
      vehicles: [legacyAgentId],
      transit: {
        geofence: { feature_id: "dbfd7aea-2f43-4653-b62a-aa0cd8ef9e0e" },
        optimization: {
          road_usage: 0.4,
          energy: 0.8,
        },
        desired_vehicle_constraints: {
          max_speed: 3.0,
        },
      },
      objective: {
        geometries: [{ feature_id: "dbfd7aea-2f43-4653-b62a-aa0cd8ef9e0e" }],
        maximize_coverage: true,
      },
    },
  },
];

export const mapFeatures: MapFeature[] = [
  {
    feature_id: "staging-area",
    name: "Staging area",
    feature_type: "workspace",
    geometry: {
      type: "Polygon",
      coordinates: [[[4.389, 50.843], [4.394, 50.843], [4.394, 50.846], [4.389, 50.846], [4.389, 50.843]]],
    },
    properties: { feature_type: "workspace" },
  },
  {
    feature_id: "delivery-point-east",
    name: "East delivery point",
    feature_type: "objective",
    geometry: { type: "Point", coordinates: [4.396, 50.844] },
    properties: { feature_type: "objective" },
  },
  {
    feature_id: "pickup-points",
    name: "Pickup points",
    feature_type: "objective",
    geometry: { type: "MultiPoint", coordinates: [[4.391, 50.845], [4.393, 50.845], [4.395, 50.845]] },
    properties: { feature_type: "objective" },
  },
  {
    feature_id: "main-road",
    name: "Main road",
    feature_type: "road",
    geometry: { type: "LineString", coordinates: [[4.389, 50.844], [4.396, 50.844]] },
    properties: { feature_type: "road" },
  },
  {
    feature_id: "enemy-risk-zone",
    name: "Enemy risk zone",
    feature_type: "risk",
    geometry: {
      type: "Polygon",
      coordinates: [[[4.392, 50.8442], [4.393, 50.8442], [4.393, 50.8448], [4.392, 50.8448], [4.392, 50.8442]]],
    },
    properties: { feature_type: "risk" },
  },
];
