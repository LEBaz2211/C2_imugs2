import { ChevronRight, Eraser, Lock, RefreshCw, ScanEye } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import {
  previewAssistantOperationalPicture,
  type AssistantOperationalPictureOptions,
  type AssistantOperationalPicturePreview,
} from "./api";
import { JsonExplorer } from "./components/JsonExplorer";
import { Badge } from "./components/ui/badge";
import { Button } from "./components/ui/button";
import { cn } from "./lib/utils";
import type { MissionConfig } from "./types";

const ALL_SECTIONS = ["agents", "missions", "plans", "health", "warnings"] as const;
const PROTECTED_TOP_LEVEL_KEYS = new Set(["context_schema", "picture_revision", "observed_at"]);
const MAX_ARRAY_ROWS = 160;

export function normalizeExcludePaths(paths: string[]): string[] {
  const unique = [...new Set(paths.map((path) => path.trim()).filter(Boolean))].sort();
  const kept: string[] = [];
  for (const path of unique) {
    const covered = kept.some(
      (existing) => path === existing || path.startsWith(`${existing}.`) || path.startsWith(`${existing}[`),
    );
    if (!covered) kept.push(path);
  }
  return kept;
}

function applyPathToggle(paths: string[], path: string, exclude: boolean): string[] {
  if (exclude) return normalizeExcludePaths([...paths, path]);
  return paths.filter((candidate) => candidate !== path);
}

function asRecord(value: unknown): Record<string, unknown> | undefined {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : undefined;
}

function scalarSummary(value: unknown): string {
  if (typeof value === "string") return value.length > 90 ? `${value.slice(0, 90)}…` : value;
  const text = JSON.stringify(value);
  return text === undefined ? String(value) : text.length > 90 ? `${text.slice(0, 90)}…` : text;
}

type ContextNode = {
  label: string;
  path: string;
  childBase: string;
  value: unknown;
  depth: number;
  hidden: boolean;
};

function childrenOf(node: ContextNode, excluded: Set<string>): ContextNode[] {
  const hidden = node.hidden || excluded.has(node.path);
  const record = asRecord(node.value);
  if (record) {
    return Object.entries(record).map(([key, value]) => ({
      label: key,
      path: `${node.childBase}.${key}`,
      childBase: `${node.childBase}.${key}`,
      value,
      depth: node.depth + 1,
      hidden,
    }));
  }
  if (Array.isArray(node.value)) {
    return node.value.map((value, index) => ({
      label: `[${index}]`,
      path: `${node.childBase}[${index}]`,
      childBase: `${node.childBase}[*]`,
      value,
      depth: node.depth + 1,
      hidden: hidden || excluded.has(`${node.childBase}[${index}]`) || excluded.has(`${node.childBase}[*]`),
    }));
  }
  return [];
}

function isContainer(node: ContextNode): boolean {
  return asRecord(node.value) !== undefined || Array.isArray(node.value);
}

function ContextTreeRow({
  node,
  excluded,
  openMap,
  onTogglePath,
  onToggleOpen,
}: {
  node: ContextNode;
  excluded: Set<string>;
  openMap: Record<string, boolean>;
  onTogglePath: (path: string, exclude: boolean) => void;
  onToggleOpen: (path: string, open: boolean) => void;
}) {
  const container = isContainer(node);
  const selfExcluded = excluded.has(node.path);
  const checked = !node.hidden && !selfExcluded;
  const open = openMap[node.path] ?? node.depth < 2;
  const protectedKey = node.depth === 0 && PROTECTED_TOP_LEVEL_KEYS.has(node.path);
  const children = container && (open || node.hidden) ? childrenOf(node, excluded) : [];
  const childCount = container ? (Array.isArray(node.value) ? node.value.length : Object.keys(asRecord(node.value) ?? {}).length) : 0;

  return (
    <div>
      <div
        className={cn(
          "flex items-center gap-1 rounded-sm py-0.5 pr-1 hover:bg-muted",
          node.hidden && "opacity-45",
          selfExcluded && "bg-red-50",
        )}
        style={{ paddingLeft: `${node.depth * 14 + 2}px` }}
      >
        {container ? (
          <button
            type="button"
            className="flex h-4 w-4 shrink-0 items-center justify-center rounded-sm text-muted-foreground outline-none hover:bg-border focus-visible:ring-2 focus-visible:ring-ring"
            onClick={() => onToggleOpen(node.path, !open)}
            aria-label={open ? `Collapse ${node.label}` : `Expand ${node.label}`}
            aria-expanded={open}
          >
            <ChevronRight className={cn("h-3 w-3 transition-transform", open && "rotate-90")} />
          </button>
        ) : (
          <span className="w-4 shrink-0" />
        )}
        {protectedKey ? (
          <Lock className="h-3 w-3 shrink-0 text-muted-foreground" aria-label="Required by the prompt template" />
        ) : (
          <input
            type="checkbox"
            className="h-3.5 w-3.5 shrink-0 accent-primary"
            checked={checked}
            disabled={node.hidden}
            title={node.hidden ? "Hidden by an excluded ancestor" : checked ? `Keep ${node.path}` : `Remove ${node.path} from model context`}
            onChange={(event) => onTogglePath(node.path, !event.target.checked)}
          />
        )}
        <button
          type="button"
          className={cn("shrink-0 text-left font-mono text-[11px] font-semibold text-foreground", selfExcluded && "text-red-700 line-through")}
          onClick={container ? () => onToggleOpen(node.path, !open) : undefined}
        >
          {node.label}
        </button>
        {container ? (
          <span className="truncate font-mono text-[10px] text-muted-foreground">
            {Array.isArray(node.value) ? `array · ${childCount}` : `object · ${childCount}`}
          </span>
        ) : (
          <span className="min-w-0 flex-1 truncate font-mono text-[10px] text-muted-foreground" title={scalarSummary(node.value)}>
            {scalarSummary(node.value)}
          </span>
        )}
        {node.hidden && <span className="ml-auto shrink-0 text-[9px] uppercase tracking-wide text-muted-foreground">hidden</span>}
        {selfExcluded && !node.hidden && <span className="ml-auto shrink-0 text-[9px] uppercase tracking-wide text-red-600">removed</span>}
      </div>
      {children.length > 0 && (
        <div>
          {children.slice(0, MAX_ARRAY_ROWS).map((child) => (
            <ContextTreeRow
              key={`${child.path}`}
              node={child}
              excluded={excluded}
              openMap={openMap}
              onTogglePath={onTogglePath}
              onToggleOpen={onToggleOpen}
            />
          ))}
          {children.length > MAX_ARRAY_ROWS && (
            <div className="py-0.5 text-[10px] text-muted-foreground" style={{ paddingLeft: `${(node.depth + 1) * 14 + 20}px` }}>
              … {children.length - MAX_ARRAY_ROWS} more rows not rendered
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function AssistantContextPage({
  excludePaths,
  operatorMissions,
  onChange,
}: {
  excludePaths: string[];
  operatorMissions: MissionConfig[];
  onChange: (paths: string[]) => void;
}) {
  const [preview, setPreview] = useState<AssistantOperationalPicturePreview | undefined>();
  const [previewBusy, setPreviewBusy] = useState(false);
  const [previewError, setPreviewError] = useState("");
  const [refreshNonce, setRefreshNonce] = useState(0);
  const [openMap, setOpenMap] = useState<Record<string, boolean>>({});

  const optionsKey = useMemo(
    () => JSON.stringify({ excludePaths, operatorMissions }),
    [excludePaths, operatorMissions],
  );
  const excluded = useMemo(() => new Set(excludePaths), [excludePaths]);
  const available = preview?.available_operational_picture;
  const selected = preview?.operational_picture;
  const availableChars = useMemo(() => (available ? JSON.stringify(available).length : 0), [available]);
  const selectedChars = useMemo(() => (selected ? JSON.stringify(selected).length : 0), [selected]);
  const savedPercent = availableChars > 0 && selected !== undefined
    ? Math.max(0, Math.round((1 - selectedChars / availableChars) * 100))
    : undefined;

  useEffect(() => {
    let active = true;
    const timer = window.setTimeout(() => {
      setPreviewBusy(true);
      setPreviewError("");
      const options: AssistantOperationalPictureOptions = {
        sections: [...ALL_SECTIONS],
        operator_missions: operatorMissions,
        exclude_paths: excludePaths,
      };
      previewAssistantOperationalPicture(options)
        .then((result) => {
          if (!active) return;
          setPreview(result);
        })
        .catch((error) => {
          if (!active) return;
          setPreviewError(error instanceof Error ? error.message : String(error));
        })
        .finally(() => {
          if (active) setPreviewBusy(false);
        });
    }, refreshNonce === 0 ? 180 : 0);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [optionsKey, refreshNonce]);

  function togglePath(path: string, exclude: boolean) {
    onChange(applyPathToggle(excludePaths, path, exclude));
  }

  function toggleOpen(path: string, open: boolean) {
    setOpenMap((current) => ({ ...current, [path]: open }));
  }

  function setAllOpen(open: boolean) {
    const next: Record<string, boolean> = {};
    if (available && open) {
      const walk = (node: ContextNode) => {
        next[node.path] = true;
        if (node.depth < 6) childrenOf(node, excluded).forEach(walk);
      };
      Object.entries(available).forEach(([key, value]) =>
        walk({ label: key, path: key, childBase: key, value, depth: 0, hidden: false }),
      );
    }
    setOpenMap(next);
  }

  const rootNodes: ContextNode[] = useMemo(() => {
    if (!available) return [];
    return Object.entries(available).map(([key, value]) => ({
      label: key,
      path: key,
      childBase: key,
      value,
      depth: 0,
      hidden: false,
    }));
  }, [available]);

  return (
    <div className="grid min-h-0 flex-1 grid-cols-1 gap-3 overflow-hidden p-4 xl:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
      <section className="flex min-h-0 flex-col rounded-md border border-border bg-panel">
        <header className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-border px-3 py-2">
          <div className="min-w-0">
            <h3 className="text-xs font-semibold text-foreground">Model context tree</h3>
            <p className="text-[10px] leading-4 text-muted-foreground">
              Un-tick anything the assistant does not need. Field filters inside arrays apply to every item of that array; ticking a list row removes one item position.
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-1">
            <Button type="button" size="sm" variant="ghost" className="h-7 text-[10px]" onClick={() => setAllOpen(true)}>
              Expand
            </Button>
            <Button type="button" size="sm" variant="ghost" className="h-7 text-[10px]" onClick={() => setOpenMap({})}>
              Collapse
            </Button>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              className="h-7 text-[10px]"
              disabled={excludePaths.length === 0}
              onClick={() => onChange([])}
              title="Keep everything (clear all removed paths)"
            >
              <Eraser className="h-3.5 w-3.5" />
              Reset
            </Button>
          </div>
        </header>
        <div className="min-h-0 flex-1 overflow-auto p-1">
          {previewError && !available && (
            <div className="m-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-950">
              Live context unavailable: {previewError}
            </div>
          )}
          {available ? (
            rootNodes.map((node) => (
              <ContextTreeRow
                key={node.path}
                node={node}
                excluded={excluded}
                openMap={openMap}
                onTogglePath={togglePath}
                onToggleOpen={toggleOpen}
              />
            ))
          ) : !previewError ? (
            <p className="p-3 text-xs text-muted-foreground">Reading the live model context…</p>
          ) : null}
        </div>
        <footer className="flex shrink-0 items-center justify-between gap-2 border-t border-border px-3 py-1.5 text-[10px] text-muted-foreground">
          <span>{excludePaths.length} removed path{excludePaths.length === 1 ? "" : "s"}</span>
          <span>{savedPercent !== undefined ? `context size −${savedPercent}%` : "size pending"}</span>
        </footer>
      </section>

      <section className="flex min-h-0 flex-col gap-2">
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-border bg-panel px-3 py-2 text-xs">
          <div className="flex flex-wrap items-center gap-1.5">
            <ScanEye className="h-3.5 w-3.5 text-primary" />
            <span className="font-medium text-foreground">Exact context sent to the model</span>
            <Badge tone={savedPercent !== undefined && savedPercent > 0 ? "ok" : "default"}>
              {availableChars.toLocaleString()} → {selectedChars.toLocaleString()} chars
            </Badge>
            {previewBusy && <Badge>refreshing…</Badge>}
          </div>
          <Button type="button" size="sm" variant="ghost" className="h-7" disabled={previewBusy} onClick={() => setRefreshNonce((current) => current + 1)}>
            <RefreshCw className={cn("h-3.5 w-3.5", previewBusy && "animate-spin")} />
            Refresh
          </Button>
        </div>
        {previewError && available && (
          <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-950">
            Last preview is stale: {previewError}
          </div>
        )}
        <div className="min-h-0 flex-1 overflow-auto">
          {selected !== undefined ? (
            <JsonExplorer value={selected} className="h-full" maxHeightClassName="max-h-full" initialExpandedDepth={3} />
          ) : (
            <div className="rounded-md border border-dashed border-border p-3 text-xs text-muted-foreground">
              The exact model-facing JSON appears here after the first live read. Your removed paths are stored in this browser and applied to every assistant message.
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
