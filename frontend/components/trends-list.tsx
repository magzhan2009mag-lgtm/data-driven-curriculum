import Link from "next/link";
import { TrendSparkline } from "@/components/trend-sparkline";
import type { Trend } from "@/lib/api";
import { formatScore } from "@/lib/format";

/** Темы, у которых результаты по годам заметно меняются; стабильные не показываем. */
export function TrendsList({ trends }: { trends: Trend[] }) {
  const changing = trends.filter((trend) => trend.direction !== "без заметных изменений");
  if (changing.length === 0) return null;
  const years = changing[0].by_year;

  return (
    <section aria-labelledby="trends-title">
      <h2 id="trends-title" className="text-xl font-semibold">
        Что меняется со временем
      </h2>
      <p className="mt-1 text-sm text-muted-foreground">
        Средний балл с {years[0].year} по {years[years.length - 1].year} год. Остальные темы заметно не меняются.
      </p>
      <ul className="mt-3 divide-y border-y">
        {changing.map((trend) => {
          const first = trend.by_year[0];
          const latest = trend.by_year[trend.by_year.length - 1];
          return (
            <li key={trend.topic_id} className="flex flex-wrap items-center gap-x-6 gap-y-2 py-3">
              <TrendSparkline trend={trend} />
              <div className="min-w-0 flex-1">
                <Link href={`/topics/${trend.topic_id}`} className="font-medium underline-offset-4 hover:underline">
                  {trend.topic}
                </Link>
                <p className="text-sm text-muted-foreground">{trend.text}</p>
              </div>
              <p className="text-sm tabular-nums whitespace-nowrap text-muted-foreground">
                {formatScore(first.avg_score)} → <span className="font-medium text-foreground">{formatScore(latest.avg_score)}</span>
              </p>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
