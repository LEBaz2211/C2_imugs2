import type { FeatureCollection } from "geojson";
import { Globe, Play } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { WorldCatalogEntry, WorldLaunchRequest, WorldLaunchResult } from "./api";
import { Badge } from "./components/ui/badge";
import { Button } from "./components/ui/button";
import type { WorldContext, WorldContextLibrary, WorldRoadImport } from "./WorldBuilder";

type WorldPickerProps = {
  catalogWorlds: WorldCatalogEntry[];
  activeWorldId?: string;
  onWorldContextChange: (library: WorldContextLibrary) => void;
  onLaunchWorld: (worldId: string, request: WorldLaunchRequest) => Promise<WorldLaunchResult>;
};

function worldContextFromEntry(world: WorldCatalogEntry): WorldContext {
  const roadImports = Array.isArray(world.road_imports) ? world.road_imports : [];
  return {
    world_id: world.world_id,
    name: world.name || world.world_id,
    map: world.map || "rma",
    notes: world.notes || "",
    agents: Array.isArray(world.agents) ? world.agents : [],
    feature_ids: Array.isArray(world.feature_ids) ? world.feature_ids : [],
    road_imports: roadImports,
    roads: roadImportsToFeatureCollection(roadImports),
    map_view: world.map_view ?? undefined,
  };
}

function roadImportsToFeatureCollection(roadImports: WorldRoadImport[]): FeatureCollection {
  return {
    type: "FeatureCollection",
    features: roadImports.flatMap((roadImport) =>
      roadImport.geojson.features.map((feature) => ({
        ...feature,
        properties: {
          ...(feature.properties ?? {}),
          feature_type: "world_osm_road",
          world_road_import_id: roadImport.import_id,
        },
      })),
    ),
  };
}

export function WorldPicker({ catalogWorlds, activeWorldId, onWorldContextChange, onLaunchWorld }: WorldPickerProps) {
  const [selectedWorldId, setSelectedWorldId] = useState<string>();
  const [launchBusy, setLaunchBusy] = useState(false);
  const [launchError, setLaunchError] = useState("");
  const [launchResult, setLaunchResult] = useState<WorldLaunchResult | undefined>();
  const worldContexts = useMemo(() => catalogWorlds.map(worldContextFromEntry), [catalogWorlds]);
  const selectedWorld = useMemo(
    () => (selectedWorldId ? catalogWorlds.find((world) => world.world_id === selectedWorldId) : undefined)
      ?? catalogWorlds.find((world) => world.runtime_active)
      ?? catalogWorlds[0],
    [catalogWorlds, selectedWorldId],
  );
  const selectedWorldIdKey = selectedWorld?.world_id;

  useEffect(() => {
    if (!selectedWorldIdKey || worldContexts.length === 0) return;
    onWorldContextChange({ active_world_id: selectedWorldIdKey, worlds: worldContexts });
  }, [onWorldContextChange, selectedWorldIdKey, worldContexts]);

  function selectWorld(world: WorldCatalogEntry) {
    setSelectedWorldId(world.world_id);
    setLaunchError("");
    setLaunchResult(undefined);
  }

  async function launchSelected() {
    if (!selectedWorld || launchBusy) return;
    setLaunchBusy(true);
    setLaunchError("");
    setLaunchResult(undefined);
    try {
      const result = await onLaunchWorld(selectedWorld.world_id, { revision: selectedWorld.revision });
      setLaunchResult(result);
    } catch (error) {
      setLaunchError(error instanceof Error ? error.message : String(error));
    } finally {
      setLaunchBusy(false);
    }
  }

  return (
    <div className="space-y-3">
      <div className="rounded-md border border-border bg-panel p-3">
        <div className="flex items-center gap-2">
          <Globe className="h-4 w-4 text-primary" />
          <h3 className="text-xs font-semibold">World picker</h3>
        </div>
        <p className="mt-1 text-[10px] text-muted-foreground">
          Select a saved world to inspect its definition on the map; launch it to make it the runtime active world.
        </p>
      </div>

      {catalogWorlds.length === 0 ? (
        <div className="rounded-md border border-border bg-panel px-3 py-4 text-xs text-muted-foreground">
          No saved world definitions found.
        </div>
      ) : (
        <div className="space-y-1.5" role="listbox" aria-label="Saved world definitions">
          {catalogWorlds.map((world) => {
            const selected = selectedWorldIdKey === world.world_id;
            const runtimeActive = world.runtime_active || world.world_id === activeWorldId;
            const stats = [
              world.map || "rma",
              `${(world.agents ?? []).length} vehicles`,
              `${world.feature_count ?? (world.feature_ids ?? []).length} assets`,
              `${world.road_count ?? (world.road_imports ?? []).length} road sections`,
            ];
            return (
              <button
                key={world.world_id}
                type="button"
                role="option"
                aria-selected={selected}
                onClick={() => selectWorld(world)}
                className={`flex w-full items-start justify-between gap-2 rounded-md border px-3 py-2 text-left transition-colors ${
                  selected ? "border-primary/50 bg-primary/5" : "border-border bg-background hover:bg-muted"
                }`}
              >
                <div className="min-w-0">
                  <p className="truncate text-xs font-medium">{world.name}</p>
                  <p className="truncate text-[10px] text-muted-foreground">{stats.join(" · ")}</p>
                </div>
                <div className="flex shrink-0 items-center gap-1.5">
                  {runtimeActive && <Badge tone="ok">active</Badge>}
                  {world.runtime_status && <Badge tone={runtimeActive ? "ok" : "default"}>{world.runtime_status}</Badge>}
                </div>
              </button>
            );
          })}
        </div>
      )}

      {selectedWorld && (
        <div className="flex items-center justify-between gap-2 rounded-md border border-border bg-panel px-3 py-2">
          <div className="min-w-0 text-xs">
            <p className="truncate font-medium">{selectedWorld.name}</p>
            <p className="text-[10px] text-muted-foreground">revision {selectedWorld.revision}</p>
          </div>
          <Button size="sm" onClick={launchSelected} disabled={launchBusy} title="Launch this saved definition as the runtime active world and verify its ROS vehicles">
            <Play className="h-4 w-4" />
            {launchBusy ? "Launching" : "Launch"}
          </Button>
        </div>
      )}

      {launchError && (
        <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-900">{launchError}</div>
      )}

      {launchResult && (
        <div className="rounded-md border border-border bg-panel px-3 py-2 text-xs">
          <div className="flex items-center gap-2">
            <Badge tone={launchResult.ready ? "ok" : "warn"}>{launchResult.status}</Badge>
            <span className="min-w-0 flex-1">{launchResult.message}</span>
          </div>
          {launchResult.error && <p className="mt-1 text-[10px] text-red-900">{launchResult.error}</p>}
        </div>
      )}
    </div>
  );
}
