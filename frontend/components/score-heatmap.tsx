import Link from "next/link";
import { LevelMark } from "@/components/level-mark";
import type { School, TopicDifficulty } from "@/lib/api";
import { SCORE_BANDS, formatPercent, formatScore, scoreBandClass } from "@/lib/format";
import { schoolHref } from "@/lib/school";
import { cn } from "@/lib/utils";

type Column = { key: number; label: string; note?: string; noteTitle?: string; href?: (topicId: number) => string };

const textbookLetter = (name: string) => name.replace("Учебник ", "");

function ScoreCell({ score, label, href }: { score: number | undefined; label: string; href?: string }) {
  if (score === undefined) {
    return <td className="rounded-sm px-2 py-1.5 text-center text-muted-foreground">—</td>;
  }
  const value = formatScore(score);
  if (!href) {
    return (
      <td title={`${label}: ${value}`} className={cn("rounded-sm px-2 py-1.5 text-center", scoreBandClass(score))}>
        {value}
      </td>
    );
  }
  return (
    <td className="p-0">
      <Link
        href={href}
        title={`${label}: ${value}. Открыть тему по этой школе`}
        aria-label={`${label}: ${value}. Открыть тему по этой школе`}
        className={cn(
          "block rounded-sm px-2 py-1.5 text-center transition-shadow duration-150 hover:ring-2 hover:ring-foreground/70 focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-foreground",
          scoreBandClass(score),
        )}
      >
        {value}
      </Link>
    </td>
  );
}

/**
 * Без фильтра — «тема × школа», клик по ячейке открывает тему по этой школе.
 * С выбранной школой — «тема × класс» и для сравнения столбец «Все школы».
 */
export function ScoreHeatmap({ topics, selected }: { topics: TopicDifficulty[]; selected?: School }) {
  const school = selected?.school_id;
  const columns: Column[] = selected
    ? (topics[0].by_class ?? []).map((row) => ({
        key: row.class_id,
        label: row.class,
        note: `уч. ${textbookLetter(row.textbook)}`,
        noteTitle: row.textbook,
      }))
    : topics[0].by_school.map((row) => ({
        key: row.school_id,
        label: row.school,
        href: (topicId: number) => schoolHref(`/topics/${topicId}`, row.school_id),
      }));
  const scoreFor = (topic: TopicDifficulty, key: number) =>
    selected
      ? topic.by_class?.find((row) => row.class_id === key)?.avg_score
      : topic.by_school.find((row) => row.school_id === key)?.avg_score;

  return (
    <section aria-labelledby="heatmap-title">
      <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-3">
        <div>
          <h2 id="heatmap-title" className="text-xl font-semibold">
            {selected ? `Средний балл: тема и класс, ${selected.school}` : "Средний балл: тема и школа"}
          </h2>
          <p className="mt-1 max-w-prose text-sm text-muted-foreground">
            {selected
              ? "Под названием класса — буква его учебника. Справа для сравнения — средний балл по всем школам."
              : "Темы идут от самой сложной к самой лёгкой. Нажмите на ячейку, чтобы открыть тему по этой школе."}
          </p>
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
              <th scope="col" className="sticky left-0 z-10 bg-background px-2 py-1 text-left align-bottom font-normal">
                Тема
              </th>
              {columns.map((column) => (
                <th key={column.key} scope="col" className="min-w-16 px-1 py-1 align-bottom font-normal whitespace-nowrap">
                  <span className={cn(column.note && "font-medium text-foreground")}>{column.label}</span>
                  {column.note && (
                    <abbr title={column.noteTitle} className="block no-underline">
                      {column.note}
                    </abbr>
                  )}
                </th>
              ))}
              <th scope="col" className="px-2 py-1 text-right align-bottom font-normal whitespace-nowrap">
                {selected ? selected.school : "Все школы"}
              </th>
              {selected && (
                <th scope="col" className="px-2 py-1 text-right align-bottom font-normal whitespace-nowrap">
                  Все школы
                </th>
              )}
              <th scope="col" className="px-2 py-1 text-right align-bottom font-normal whitespace-nowrap">
                Не справились
              </th>
              <th scope="col" className="px-2 py-1 text-left align-bottom font-normal">
                Уровень
              </th>
            </tr>
          </thead>
          <tbody>
            {topics.map((topic) => (
              <tr key={topic.topic_id} className="group">
                <th scope="row" className="sticky left-0 z-10 min-w-36 bg-background px-2 py-1 text-left font-normal">
                  <Link
                    href={schoolHref(`/topics/${topic.topic_id}`, school)}
                    className="rounded-sm underline-offset-4 group-hover:underline hover:text-primary focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
                  >
                    {topic.topic}
                  </Link>
                </th>
                {columns.map((column) => (
                  <ScoreCell
                    key={column.key}
                    score={scoreFor(topic, column.key)}
                    label={`${topic.topic}, ${column.label}`}
                    href={column.href?.(topic.topic_id)}
                  />
                ))}
                <td className="px-2 py-1.5 text-right font-medium">{formatScore(topic.avg_score)}</td>
                {selected && (
                  <td className="px-2 py-1.5 text-right text-muted-foreground">
                    {topic.avg_score_all === undefined ? "—" : formatScore(topic.avg_score_all)}
                  </td>
                )}
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
