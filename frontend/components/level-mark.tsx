import type { Level } from "@/lib/api";
import { LEVEL_LABELS } from "@/lib/format";
import { cn } from "@/lib/utils";

const DOT_CLASS: Record<Level, string> = {
  hard: "bg-score-1",
  medium: "bg-muted-foreground",
  easy: "bg-score-5",
};

export function LevelMark({ level }: { level: Level }) {
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap">
      <span aria-hidden className={cn("size-2 rounded-full", DOT_CLASS[level])} />
      {LEVEL_LABELS[level]}
    </span>
  );
}
