import type { Agent, GeometryLiteral, GeometryRef, LonLat, MapFeature, MissionConfig, TaskPlan } from "./types";

export function normalizeMission(input: unknown): MissionConfig {
  if (!isObject(input)) throw new Error("Mission must be a JSON object.");
  const data = structuredClone(input) as Record<string, unknown>;
  const objective = ensureObject(data.objective, "objective");

  if (!Array.isArray(objective.geometries)) {
    if (isObject(objective.geometry)) {
      objective.geometries = [normalizeGeometryRef(objective.geometry)];
      delete objective.geometry;
    } else if (typeof objective.feature_id === "string") {
      objective.geometries = [{ feature_id: objective.feature_id }];
      delete objective.feature_id;
    }
  }
  if (Array.isArray(objective.geometries)) {
    objective.geometries = objective.geometries.map((geometryRef) => (isObject(geometryRef) ? normalizeGeometryRef(geometryRef) : geometryRef));
  }
  if (hasOwn(objective, "maximize_area_coverage") && !hasOwn(objective, "maximize_coverage")) {
    objective.maximize_coverage = objective.maximize_area_coverage;
    delete objective.maximize_area_coverage;
  }
  if (typeof objective.vehicle_orientation === "number") {
    objective.vehicle_orientation = [objective.vehicle_orientation];
  }

  const transit = isObject(data.transit) ? data.transit : undefined;
  if (transit && hasOwn(transit, "optimalization") && !hasOwn(transit, "optimization")) {
    transit.optimization = transit.optimalization;
    delete transit.optimalization;
  }
  if (transit && hasOwn(transit, "vehicle_constraints") && !hasOwn(transit, "desired_vehicle_constraints")) {
    transit.desired_vehicle_constraints = transit.vehicle_constraints;
    delete transit.vehicle_constraints;
  }
  if (typeof transit?.desired_speed === "number") {
    const constraints = isObject(transit.desired_vehicle_constraints) ? transit.desired_vehicle_constraints : {};
    if (typeof constraints.max_speed !== "number") constraints.max_speed = transit.desired_speed;
    transit.desired_vehicle_constraints = constraints;
    delete transit.desired_speed;
  }

  for (const section of [data.start, data.transit, data.objective]) {
    if (!isObject(section)) continue;
    if (hasOwn(section, "vehicle_formation_distances") && !hasOwn(section, "vehicle_formation_distance")) {
      section.vehicle_formation_distance = section.vehicle_formation_distances;
      delete section.vehicle_formation_distances;
    }
    if (hasOwn(section, "maximize_coverage_distances") && !hasOwn(section, "maximum_coverage_distances")) {
      section.maximum_coverage_distances = section.maximize_coverage_distances;
      delete section.maximize_coverage_distances;
    }
  }

  if (transit && hasOwn(transit, "geofence_maximum_coverage") && !hasOwn(transit, "geofence_maximize_coverage")) {
    transit.geofence_maximize_coverage = transit.geofence_maximum_coverage;
    delete transit.geofence_maximum_coverage;
  }

  if (!hasOwn(data, "schema_version")) data.schema_version = "1.0";
  return data as MissionConfig;
}

export function validateMission(mission: MissionConfig, agents: Agent[], features: MapFeature[]) {
  const errors: string[] = [];
  const featureIds = new Set(features.map((feature) => feature.feature_id));
  const agentIds = new Set(agents.map((agent) => agent.agent_id));

  if (!mission.mission_id || typeof mission.mission_id !== "string") errors.push("mission_id must be a string.");
  if (!Number.isInteger(Number(mission.behavior)) || ![0, 1, 2].includes(Number(mission.behavior))) errors.push("behavior must be 0, 1, or 2.");
  if (mission.phase !== undefined && (!Number.isInteger(mission.phase) || mission.phase < 0)) errors.push("phase must be an integer greater than or equal to 0.");
  if (!Array.isArray(mission.vehicles) || mission.vehicles.length === 0) errors.push("vehicles must be a non-empty array.");

  if (Array.isArray(mission.vehicles)) {
    for (const vehicle of mission.vehicles) {
      if (typeof vehicle !== "string" || !vehicle) errors.push("vehicles must contain non-empty string ids.");
      else if (!agentIds.has(vehicle)) errors.push(`vehicle '${vehicle}' is not in the agent registry.`);
    }
  }

  const objective = isObject(mission.objective) ? mission.objective : undefined;
  const geometries = Array.isArray(objective?.geometries) ? objective.geometries : [];
  if (!objective) errors.push("objective must be a JSON object.");
  if (geometries.length === 0) {
    errors.push("objective.geometries must be a non-empty array.");
  }

  for (const [index, geometry] of geometries.entries()) {
    if (!isObject(geometry)) {
      errors.push(`objective.geometries[${index}] must be a JSON object.`);
      continue;
    }
    const hasFeature = typeof geometry.feature_id === "string";
    const hasGeometry = isObject(geometry.geometry);
    if (hasFeature === hasGeometry) errors.push(`objective.geometries[${index}] must contain exactly one of feature_id or geometry.`);
    if (hasFeature && !featureIds.has(geometry.feature_id as string)) errors.push(`feature '${geometry.feature_id}' was not found.`);
    if (hasGeometry) {
      const literal = geometry.geometry as Record<string, unknown>;
      if (typeof literal.geometry_type !== "string") errors.push(`objective.geometries[${index}].geometry.geometry_type must be a string.`);
      if (literal.coordinates === undefined) errors.push(`objective.geometries[${index}].geometry.coordinates is required.`);
    }
  }

  const formation = objective?.vehicle_formation;
  if (formation !== undefined && ![0, 1, 2, 3, 4, 5, 6].includes(Number(formation))) errors.push("objective.vehicle_formation must be one of 0, 1, 2, 3, 4, 5, or 6.");
  if (objective?.vehicle_formation_distance !== undefined && typeof objective.vehicle_formation_distance !== "number") errors.push("objective.vehicle_formation_distance must be a number.");
  if (objective?.vehicle_orientation !== undefined && (!Array.isArray(objective.vehicle_orientation) || !objective.vehicle_orientation.every((value) => typeof value === "number"))) {
    errors.push("objective.vehicle_orientation must be an array of numbers.");
  }
  if (
    objective?.maximum_coverage_distances !== undefined &&
    (!Array.isArray(objective.maximum_coverage_distances) ||
      objective.maximum_coverage_distances.length === 0 ||
      !objective.maximum_coverage_distances.every((value) => typeof value === "number" && Number.isFinite(value) && value > 0))
  ) {
    errors.push("objective.maximum_coverage_distances must be a non-empty array of positive swath widths in metres.");
  }
  if (Number(mission.behavior) === 1 && !objective?.maximum_coverage_distances?.length) {
    errors.push("coverage behavior requires objective.maximum_coverage_distances (for example [6.0] metres).");
  }
  if (
    objective?.maximum_coverage_distances?.length &&
    Array.isArray(mission.vehicles) &&
    ![1, mission.vehicles.length].includes(objective.maximum_coverage_distances.length)
  ) {
    errors.push("maximum_coverage_distances must contain one shared width or one width per mission vehicle.");
  }

  return errors;
}

export function createTaskPlan(mission: MissionConfig, agents: Agent[], features: MapFeature[]): TaskPlan {
  const selected = agents.filter((agent) => mission.vehicles.includes(agent.agent_id));
  const targets = missionDestinationPoints(mission, features);
  const speed = speedForMission(mission, selected);
  const tasks: TaskPlan["tasks"] = {};

  targets.forEach((target, index) => {
    const agent = selected[index % Math.max(selected.length, 1)];
    if (!agent) return;
    const primitiveId = `prim-${mission.mission_id}-${agent.agent_id}-${index}`;
    const objectiveId = `obj-${mission.mission_id}-${agent.agent_id}-${index}`;
    const existing = tasks[agent.agent_id] ?? {
      task_id: `task-${mission.mission_id}-${agent.agent_id}`,
      primitives: [
        {
          primitive_id: primitiveId,
          primitive_type: "waypoint",
          continuous: false,
          primitive_inputs: [],
          primitive_outputs: [],
          completion: {
            ends_objective: true,
            ends_task: false,
            followed_by_primitives: [],
            inherit_other_primitives: false,
            resume_after: false,
          },
        },
      ],
      objectives: [],
    };
    existing.objectives.push({
      objective_id: objectiveId,
      objective_type: "combined_primitives",
      parallel_execution: true,
      primitives: [
        {
          primitive_id: primitiveId,
          parameters: {
            coordinates: target,
            speed,
            max_speed: speed,
            mobility_profile: 0,
            wait_time: 0,
          },
        },
      ],
    });
    tasks[agent.agent_id] = existing;
  });

  return { mission_id: mission.mission_id, tasks };
}

export function missionDestinationPoints(mission: MissionConfig, features: MapFeature[]): LonLat[] {
  const geometries = mission.objective.geometries ?? [];
  const destinationGeometries =
    mission.behavior === 0 && geometries.some((geometryRef) => isPointDestinationRef(geometryRef, features))
      ? geometries.filter((geometryRef) => isPointDestinationRef(geometryRef, features))
      : geometries;
  return destinationGeometries.flatMap((geometryRef) => destinationsForGeometryRef(geometryRef, features, mission.behavior));
}

export function destinationsForGeometryRef(ref: GeometryRef, features: MapFeature[], behavior: number): LonLat[] {
  const geometry = geometryForRef(ref, features);
  if (!geometry) return [];
  const type = geometryType(geometry);
  const coords = geometry.coordinates;
  if (type === "MultiPoint" && Array.isArray(coords) && behavior === 0) return coords as LonLat[];
  return [representativePoint(geometry)];
}

function isPointDestinationRef(ref: GeometryRef, features: MapFeature[]) {
  const geometry = geometryForRef(ref, features);
  const type = geometry ? geometryType(geometry) : undefined;
  return type === "Point" || type === "MultiPoint";
}

function geometryForRef(ref: GeometryRef, features: MapFeature[]): GeometryLiteral | undefined {
  return (ref.feature_id ? features.find((feature) => feature.feature_id === ref.feature_id)?.geometry : ref.geometry) as GeometryLiteral | undefined;
}

export function representativePoint(geometry: GeometryLiteral): LonLat {
  const type = geometryType(geometry);
  const coords = geometry.coordinates;
  if (type === "Point") return coords as LonLat;
  const points = flattenPoints(coords);
  const lon = points.reduce((sum, point) => sum + point[0], 0) / Math.max(points.length, 1);
  const lat = points.reduce((sum, point) => sum + point[1], 0) / Math.max(points.length, 1);
  return [lon, lat];
}

export function polygonGeometry(points: LonLat[]): GeometryRef {
  const ring = [...points];
  if (ring.length > 0) ring.push(ring[0]);
  return {
    geometry: {
      geometry_type: "Polygon",
      coordinates: [ring],
    },
  };
}

function speedForMission(mission: MissionConfig, agents: Agent[]) {
  const transit = mission.transit as { desired_vehicle_constraints?: { max_speed?: number }; vehicle_constraints?: { max_speed?: number }; desired_speed?: number } | undefined;
  const configured = transit?.desired_vehicle_constraints?.max_speed ?? transit?.vehicle_constraints?.max_speed ?? transit?.desired_speed;
  if (typeof configured === "number") return configured;
  const speeds = agents.map((agent) => agent.constraints.max_speed).filter((speed): speed is number => typeof speed === "number");
  return speeds.length ? Math.min(...speeds) : 1;
}

function flattenPoints(value: unknown): LonLat[] {
  if (!Array.isArray(value)) return [];
  if (typeof value[0] === "number" && typeof value[1] === "number") return [[value[0], value[1]]];
  return value.flatMap((item) => flattenPoints(item));
}

function geometryType(geometry: GeometryLiteral) {
  return geometry.type ?? geometry.geometry_type;
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasOwn(value: Record<string, unknown>, key: string) {
  return Object.prototype.hasOwnProperty.call(value, key);
}

function normalizeGeometryRef(value: Record<string, unknown>): GeometryRef {
  if (typeof value.feature_id === "string" && !isObject(value.geometry)) return { feature_id: value.feature_id };
  if (isObject(value.geometry) && typeof value.geometry.feature_id === "string" && value.geometry.coordinates === undefined) return { feature_id: value.geometry.feature_id };
  if (typeof value.geometry_type === "string" || value.coordinates !== undefined) return { geometry: value as GeometryLiteral };
  return value as GeometryRef;
}

function ensureObject(value: unknown, name: string): Record<string, unknown> {
  if (!isObject(value)) throw new Error(`${name} must be a JSON object.`);
  return value;
}
