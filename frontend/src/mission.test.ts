import { describe, expect, it } from "vitest";
import { normalizeMission, relocateMissionInlineGeometry } from "./mission";

describe("mission example relocation", () => {
  it("moves every inline geometry together without changing non-coordinate arrays", () => {
    const mission = normalizeMission({
      mission_id: "example",
      behavior: 0,
      vehicles: ["robot-a"],
      start: { geometry: { geometry_type: "Point", coordinates: [4, 50] } },
      transit: {
        geofence: {
          geometry_type: "Polygon",
          coordinates: [[4, 50], [4.2, 50], [4.2, 50.2], [4, 50]],
        },
      },
      objective: {
        geometry: { geometry_type: "Point", coordinates: [4.2, 50.2] },
        vehicle_orientation: [45, 90],
        line_of_sight: { geometry_type: "Point", coordinates: [4.1, 50.1] },
      },
    });

    const relocated = relocateMissionInlineGeometry(mission, [3.7, 51.7]);

    expect((relocated.start?.geometry as { geometry: { coordinates: unknown } }).geometry.coordinates).toEqual([3.6, 51.6]);
    expect(relocated.objective.geometries[0].geometry?.coordinates).toEqual([3.8, 51.8]);
    expect(relocated.objective.line_of_sight?.geometry?.coordinates).toEqual([3.7, 51.7]);
    expect(relocated.objective.vehicle_orientation).toEqual([45, 90]);
  });
});
