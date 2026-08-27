import { Braces, Check, ChevronRight, Copy } from "lucide-react";
import { useMemo, useState } from "react";

import { cn } from "../lib/utils";
import { Button } from "./ui/button";

type JsonExplorerProps = {
  value: unknown;
  className?: string;
  maxHeightClassName?: string;
  initialExpandedDepth?: number;
};

export function JsonExplorer({
  value,
  className,
  maxHeightClassName = "max-h-80",
  initialExpandedDepth = 2,
}: JsonExplorerProps) {
  const [treeRevision, setTreeRevision] = useState(0);
  const [expandedDepth, setExpandedDepth] = useState(initialExpandedDepth);
  const [copied, setCopied] = useState(false);
  const serialized = useMemo(() => safeStringify(value), [value]);

  function resetTree(depth: number) {
    setExpandedDepth(depth);
    setTreeRevision((current) => current + 1);
  }

  async function copyJson() {
    if (typeof navigator === "undefined" || !navigator.clipboard) return;
    await navigator.clipboard.writeText(serialized);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1200);
  }

  return (
    <div className={cn("overflow-hidden rounded-md border border-border bg-background", className)}>
      <div className="flex items-center justify-between gap-2 border-b border-border bg-muted/50 px-2 py-1">
        <div className="flex min-w-0 items-center gap-1.5 text-[10px] text-muted-foreground">
          <Braces className="h-3.5 w-3.5 shrink-0" />
          <span className="truncate">{jsonValueSummary(value)}</span>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <Button type="button" size="sm" variant="ghost" className="h-6 px-1.5 text-[10px]" onClick={() => resetTree(0)}>
            Collapse
          </Button>
          <Button type="button" size="sm" variant="ghost" className="h-6 px-1.5 text-[10px]" onClick={() => resetTree(3)}>
            Expand
          </Button>
          <Button
            type="button"
            size="icon"
            variant="ghost"
            className="h-6 w-6"
            onClick={() => copyJson().catch(() => undefined)}
            title="Copy redacted JSON"
            aria-label="Copy redacted JSON"
          >
            {copied ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5" />}
          </Button>
        </div>
      </div>
      <div className={cn("overflow-auto p-2 font-mono text-[10px] leading-4", maxHeightClassName)}>
        <JsonTreeNode
          key={treeRevision}
          value={value}
          depth={0}
          initialExpandedDepth={expandedDepth}
        />
      </div>
    </div>
  );
}

function JsonTreeNode({
  label,
  value,
  depth,
  initialExpandedDepth,
}: {
  label?: string;
  value: unknown;
  depth: number;
  initialExpandedDepth: number;
}) {
  const entries = jsonEntries(value);
  const expandable = entries !== undefined;
  const [expanded, setExpanded] = useState(expandable && depth < initialExpandedDepth);

  if (expandable) {
    const array = Array.isArray(value);
    return (
      <div>
        <button
          type="button"
          className="flex max-w-full items-center gap-1 rounded-sm py-0.5 text-left outline-none hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring"
          aria-expanded={expanded}
          onClick={() => setExpanded((current) => !current)}
        >
          <ChevronRight className={cn("h-3 w-3 shrink-0 transition-transform", expanded && "rotate-90")} />
          {label !== undefined && <JsonKey value={label} />}
          <span className="text-muted-foreground">
            {array ? `[${entries.length}]` : `{${entries.length}}`}
          </span>
        </button>
        {expanded && entries.length > 0 && (
          <div className="ml-1.5 space-y-0.5 border-l border-border pl-2">
            {entries.map(([key, item]) => (
              <JsonTreeNode
                key={key}
                label={key}
                value={item}
                depth={depth + 1}
                initialExpandedDepth={initialExpandedDepth}
              />
            ))}
          </div>
        )}
      </div>
    );
  }

  if (typeof value === "string") {
    return <JsonStringNode label={label} value={value} depth={depth} initialExpandedDepth={initialExpandedDepth} />;
  }

  return (
    <div className="flex min-w-0 items-start gap-1 py-0.5 pl-4">
      {label !== undefined && <JsonKey value={label} />}
      <JsonPrimitive value={value} />
    </div>
  );
}

function JsonStringNode({
  label,
  value,
  depth,
  initialExpandedDepth,
}: {
  label?: string;
  value: string;
  depth: number;
  initialExpandedDepth: number;
}) {
  const structured = splitStructuredString(value);
  const multiline = value.includes("\n") || value.length > 120;

  if (!structured && !multiline) {
    return (
      <div className="flex min-w-0 items-start gap-1 py-0.5 pl-4">
        {label !== undefined && <JsonKey value={label} />}
        <span className="break-all text-emerald-700">{JSON.stringify(value)}</span>
      </div>
    );
  }

  return (
    <div className="py-0.5 pl-4">
      {label !== undefined && <JsonKey value={label} />}
      <div className="mt-1 overflow-hidden rounded-sm border border-border bg-muted/30">
        {structured?.before ? <ReadableString value={structured.before} /> : null}
        {structured ? (
          <div className="border-y border-border bg-background p-1.5">
            <div className="mb-1 text-[9px] font-sans font-medium uppercase tracking-wide text-muted-foreground">Embedded JSON</div>
            <JsonTreeNode value={structured.value} depth={depth + 1} initialExpandedDepth={initialExpandedDepth} />
          </div>
        ) : (
          <ReadableString value={value} />
        )}
        {structured?.after ? <ReadableString value={structured.after} /> : null}
      </div>
    </div>
  );
}

function ReadableString({ value }: { value: string }) {
  return (
    <pre className="max-h-56 overflow-auto whitespace-pre-wrap break-words p-1.5 font-mono text-[10px] leading-4 text-emerald-800">
      {value.trim()}
    </pre>
  );
}

function JsonKey({ value }: { value: string }) {
  return <span className="shrink-0 text-sky-700">{JSON.stringify(value)}:</span>;
}

function JsonPrimitive({ value }: { value: unknown }) {
  if (value === null) return <span className="text-violet-600">null</span>;
  if (typeof value === "boolean") return <span className="text-amber-700">{String(value)}</span>;
  if (typeof value === "number") return <span className="text-blue-700">{String(value)}</span>;
  if (value === undefined) return <span className="text-muted-foreground">undefined</span>;
  return <span className="break-all text-muted-foreground">{String(value)}</span>;
}

function jsonEntries(value: unknown): [string, unknown][] | undefined {
  if (Array.isArray(value)) return value.map((item, index) => [String(index), item]);
  if (value !== null && typeof value === "object") return Object.entries(value as Record<string, unknown>);
  return undefined;
}

function jsonValueSummary(value: unknown) {
  if (Array.isArray(value)) return `Array · ${value.length} item${value.length === 1 ? "" : "s"}`;
  if (value !== null && typeof value === "object") {
    const count = Object.keys(value as Record<string, unknown>).length;
    return `Object · ${count} field${count === 1 ? "" : "s"}`;
  }
  return typeof value;
}

function splitStructuredString(value: string): { before: string; value: unknown; after: string } | undefined {
  const trimmed = value.trim();
  const exact = parseJsonContainer(trimmed);
  if (exact !== undefined) return { before: "", value: exact, after: "" };

  const fenced = /```(?:json)?\s*([\s\S]*?)```/i.exec(value);
  if (!fenced) return undefined;
  const parsed = parseJsonContainer(fenced[1].trim());
  if (parsed === undefined) return undefined;
  return {
    before: value.slice(0, fenced.index),
    value: parsed,
    after: value.slice(fenced.index + fenced[0].length),
  };
}

function parseJsonContainer(value: string): unknown | undefined {
  if (!(value.startsWith("{") || value.startsWith("["))) return undefined;
  try {
    const parsed = JSON.parse(value) as unknown;
    return parsed !== null && typeof parsed === "object" ? parsed : undefined;
  } catch {
    return undefined;
  }
}

function safeStringify(value: unknown) {
  try {
    return JSON.stringify(value, null, 2) ?? "null";
  } catch {
    return "[Unserializable JSON value]";
  }
}
