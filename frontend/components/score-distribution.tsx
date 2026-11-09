"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { TopicDifficulty } from "@/lib/api";

const AXIS_TICK = { fill: "var(--muted-foreground)", fontSize: 12 };

export function ScoreDistribution({ data }: { data: TopicDifficulty["score_distribution"] }) {
  const bars = data.map((row) => ({ ...row, fill: row.failing ? "var(--score-1)" : "var(--score-5)" }));
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%" initialDimension={{ width: 800, height: 256 }}>
        <BarChart data={bars} margin={{ top: 8, right: 0, bottom: 0, left: -16 }}>
          <CartesianGrid vertical={false} stroke="var(--border)" />
          <XAxis dataKey="range" tick={AXIS_TICK} tickLine={false} axisLine={{ stroke: "var(--border)" }} minTickGap={8} />
          <YAxis tick={AXIS_TICK} tickLine={false} axisLine={false} allowDecimals={false} tickCount={6} />
          <Tooltip
            cursor={{ fill: "var(--muted)" }}
            isAnimationActive={false}
            labelFormatter={(label) => `Баллы ${label}`}
            formatter={(value) => [value, "Результатов"]}
            contentStyle={{
              background: "var(--popover)",
              border: "1px solid var(--border)",
              borderRadius: 4,
              fontSize: 13,
            }}
          />
          <Bar dataKey="count" maxBarSize={24} radius={[4, 4, 0, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
