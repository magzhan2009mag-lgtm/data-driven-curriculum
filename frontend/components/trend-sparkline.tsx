"use client";

import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Trend } from "@/lib/api";
import { formatScore } from "@/lib/format";

const STROKE: Record<Trend["direction"], string> = {
  ухудшается: "var(--score-1)",
  улучшается: "var(--score-5)",
  "без заметных изменений": "var(--muted-foreground)",
};

export function TrendSparkline({ trend }: { trend: Trend }) {
  const scores = trend.by_year.map((row) => row.avg_score);
  const low = Math.floor(Math.min(...scores) - 1);
  const high = Math.ceil(Math.max(...scores) + 1);
  const last = trend.by_year.length - 1;

  return (
    <div className="h-12 w-40 shrink-0" aria-hidden>
      <ResponsiveContainer width="100%" height="100%" initialDimension={{ width: 160, height: 48 }}>
        <LineChart data={trend.by_year} margin={{ top: 6, right: 6, bottom: 6, left: 6 }}>
          <XAxis dataKey="year" hide />
          <YAxis domain={[low, high]} hide />
          <Tooltip
            isAnimationActive={false}
            cursor={{ stroke: "var(--border)" }}
            labelFormatter={(year) => `${year} год`}
            formatter={(value) => [formatScore(Number(value)), "Средний балл"]}
            contentStyle={{
              background: "var(--popover)",
              border: "1px solid var(--border)",
              borderRadius: 4,
              fontSize: 13,
            }}
          />
          <Line
            dataKey="avg_score"
            stroke={STROKE[trend.direction]}
            strokeWidth={2}
            isAnimationActive={false}
            dot={(props) => {
              const { cx, cy, index } = props;
              if (index !== last || cx === undefined || cy === undefined) return <g key={index} />;
              return (
                <circle key={index} cx={cx} cy={cy} r={4} fill={STROKE[trend.direction]} stroke="var(--background)" strokeWidth={2} />
              );
            }}
            activeDot={{ r: 4, stroke: "var(--background)", strokeWidth: 2 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
