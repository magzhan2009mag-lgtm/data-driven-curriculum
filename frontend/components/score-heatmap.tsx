import Link from "next/link";
import { LevelMark } from "@/components/level-mark";
import type { TopicDifficulty } from "@/lib/api";
import { SCORE_BANDS, formatPercent, formatScore, scoreBandClass } from "@/lib/format";
import { cn } from "@/lib/utils";

export function ScoreHeatmap({ topics }: { topics: TopicDifficulty[] }) {
  const schools = topics[0].by_school;
  return (
    <section aria-labelledby="heatmap-title">
      <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-3">
        <div>
          <h2 id="heatmap-title" className="text-xl font-semibold">
            Средний балл: тема и школа
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">Темы идут от самой сложной к самой лёгкой.</p>
        </div>
        <ul aria-label="Шкала цвета" className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground">
          {SCORE_BANDS.map((band) => (
            <li key={band.label} className="flex items-center gap-1.5">
              <span aria-hidden className={cn("size-3 rounded-sm", band.className)} />
              {band.label}
            </li>
          ))}
        </ul>
      </div>

      <div className="mt-4 overflow-x-auto">
        <table className="w-full border-separate border-spacing-0.5 text-sm tabular-nums">
          <thead>
            <tr className="text-xs text-muted-foreground">
              <th scope="col" className="sticky left-0 bg-background px-2 py-1 text-left font-normal">
                Тема
              </th>
              {schools.map((school) => (
                <th key={school.school_id} scope="col" className="min-w-16 px-1 py-1 font-normal whitespace-nowrap">
                  {school.school}
                </th>
              ))}
              <th scope="col" className="px-2 py-1 text-right font-normal">
                Все школы
              </th>
              <th scope="col" className="px-2 py-1 text-right font-normal whitespace-nowrap">
                Не справились
              </th>
              <th scope="col" className="px-2 py-1 text-left font-normal">
                Уровень
              </th>
            </tr>
          </thead>
          <tbody>
            {topics.map((topic) => (
              <tr key={topic.topic_id} className="group">
                <th scope="row" className="sticky left-0 min-w-36 bg-background px-2 py-1 text-left font-normal">
                  <Link
                    href={`/topics/${topic.topic_id}`}
                    className="underline-offset-4 group-hover:underline hover:text-primary focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
                  >
                    {topic.topic}
                  </Link>
                </th>
                {schools.map((school) => {
                  const score = topic.by_school.find((row) => row.school_id === school.school_id)?.avg_score;
                  return (
                    <td
                      key={school.school_id}
                      title={score === undefined ? undefined : `${topic.topic}, ${school.school}: ${formatScore(score)}`}
                      className={cn(
                        "rounded-sm px-2 py-1.5 text-center",
                        score === undefined ? "text-muted-foreground" : scoreBandClass(score),
                      )}
                    >
                      {score === undefined ? "—" : formatScore(score)}
                    </td>
                  );
                })}
                <td className="px-2 py-1.5 text-right font-medium">{formatScore(topic.avg_score)}</td>
                <td className="px-2 py-1.5 text-right">{formatPercent(topic.fail_rate)}</td>
                <td className="px-2 py-1.5">
                  <LevelMark level={topic.level} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
