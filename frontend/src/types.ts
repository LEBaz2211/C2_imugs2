export type LonLat = [number, number];

export type GeometryLiteral = {
  geometry_type?: string;
  type?: string;
  coordinates: unknown;
};

export type GeometryRef = {
  feature_id?: string;
  geometry?: GeometryLiteral;
  geometry_type?: string;
  coordinates?: unknown;
};

export type MissionConfig = {
  schema_version?: string;
  mission_id: string;
  phase?: number;
  name?: string;
  behavior: 0 | 1 | 2;
  vehicles: string[];
  start?: Record<string, unknown>;
  transit?: Record<string, unknown>;
  objective: {
    geometries: GeometryRef[];
    minimum_distance?: number;
    maximum_distance?: number;
    vehicle_formation?: number;
    vehicle_formation_distance?: number;
    vehicle_orientation?: number[];
    vehicle_orientation_origin?: GeometryRef;
    vehicle_order?: boolean;
    line_of_sight?: GeometryRef;
    line_of_sight_propagation?: boolean;
    maximize_coverage?: boolean;
    maximum_coverage_distances?: number[];
    arrival_time?: {
      earliest: string;
      target: string;
      latest: string;
    };
  };
  mission_end_time?: string;
};

export type Agent = {
  agent_id: string;
  name: string;
  vehicle_type: string;
  status: string;
  current_location: LonLat;
  constraints: { max_speed?: number };
  capabilities: string[];
};

export type MapFeature = {
  feature_id: string;
  name: string;
  feature_type: string;
  geometry: {
    type: string;
    coordinates: unknown;
  };
  properties: Record<string, unknown>;
};

export type TaskPlan = {
  mission_id: string;
  tasks: Record<
    string,
    {
      task_id: string;
      primitives: unknown[];
      objectives: {
        objective_id: string;
        objective_type: string;
        parallel_execution: boolean;
        primitives: {
          primitive_id: string;
          parameters?: {
            coordinates?: LonLat;
            speed?: number;
            max_speed?: number;
            mobility_profile?: number;
            wait_time?: number;
          };
        }[];
      }[];
    }
  >;
};

export type DiagnosticsCheck = {
  id: string;
  status: "ok" | "error";
  message: string;
};
