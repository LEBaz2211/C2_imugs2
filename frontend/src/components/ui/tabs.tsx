import { cn } from "../../lib/utils";

type TabsProps = {
  value: string;
  onValueChange: (value: string) => void;
  items: { value: string; label: string }[];
};

export function Tabs({ value, onValueChange, items }: TabsProps) {
  return (
    <div className="inline-grid h-9 grid-flow-col rounded-md border border-border bg-muted p-1">
      {items.map((item) => (
        <button
          key={item.value}
          onClick={() => onValueChange(item.value)}
          className={cn(
            "rounded-sm px-3 text-xs font-medium text-muted-foreground transition-colors",
            value === item.value && "bg-panel text-foreground shadow-sm",
          )}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}

