import { StrictMode, act, useCallback, useState } from "react";
import TestRenderer, { type ReactTestRenderer } from "react-test-renderer";
import { afterEach, describe, expect, it } from "vitest";
import { WorldBuilder, type WorldContextLibrary } from "./WorldBuilder";

const noop = () => undefined;

function WorldBuilderHarness() {
  const [, setLibrary] = useState<WorldContextLibrary>({ active_world_id: "", worlds: [] });
  const handleLibraryChange = useCallback((library: WorldContextLibrary) => setLibrary(library), []);

  return (
    <WorldBuilder
      mapFeatures={[]}
      mapFeaturesReady={false}
      catalogWorlds={[]}
      onWorldAgentsChange={noop}
      onActiveWorldFeaturesChange={noop}
      onWorldRoadsChange={noop}
      onWorldLibraryChange={handleLibraryChange}
      onSelectFeature={noop}
      onDeleteAuthoringFeature={async () => undefined}
      onLaunchWorld={async () => { throw new Error("not used"); }}
      onWorldContextReset={noop}
      onBeginPlaceAgent={noop}
      onCancelPlaceAgent={noop}
    />
  );
}

describe("WorldBuilder initial render", () => {
  let renderer: ReactTestRenderer | undefined;

  afterEach(() => {
    if (renderer) act(() => renderer?.unmount());
    renderer = undefined;
  });

  it("does not loop while the server world catalog is still loading", () => {
    expect(() => {
      act(() => {
        renderer = TestRenderer.create(
          <StrictMode>
            <WorldBuilderHarness />
          </StrictMode>,
        );
      });
    }).not.toThrow();

    const output = JSON.stringify(renderer?.toJSON());
    expect(output).toContain("World Builder");
    expect(output).toContain("Blank world");
  });
});
