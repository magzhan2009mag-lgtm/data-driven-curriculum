import Link from "next/link";
import { notFound } from "next/navigation";
import { AllSchools } from "@/components/all-schools";
import { ItemIssues } from "@/components/item-issues";
import { LevelMark } from "@/components/level-mark";
import { ScoreDistribution } from "@/components/score-distribution";
import { Term } from "@/components/term";
import { TopicLinks } from "@/components/topic-links";
import { TopicSwitcher } from "@/components/topic-switcher";
import { TrendSparkline } from "@/components/trend-sparkline";
import { getItemQuality, getPrerequisites, getRecommendations, getTopics, getTrends } from "@/lib/api";
import { formatHours, formatIndex, formatPercent, formatScore, scoreBandClass } from "@/lib/format";
import { schoolHref } from "@/lib/school";
import { readScope } from "@/lib/scope";
import { cn } from "@/lib/utils";

const signedHours = new Intl.NumberFormat("ru-RU", { signDisplay: "exceptZero" });

export default async function TopicPage({ params, searchParams }: PageProps<"/topics/[id]">) {
  const { id } = await params;
  const { school, selected } = await readScope(searchParams);
  const [topics, recommendations, trends, prerequisites] = await Promise.all([
    getTopics(school),
    getRecommendations(school),
    getTrends(school),
    getPrerequisites(school),
  ]);
  const topic = topics.find((item) => String(item.topic_id) === id);
  if (!topic) notFound();
  const recommendation = recommendations.items.find((item) => item.topic_id === topic.topic_id);
  const trend = trends.find((item) => item.topic_id === topic.topic_id);
  const itemQuality = await getItemQuality(topic.topic_id, school);
  // Номер темы и есть её место в программе: API отдаёт темы от сложной к лёгкой, здесь нужен порядок программы.
  const programOrder = topics
    .map(({ topic_id, topic: name }) => ({ topic_id, topic: name }))
    .sort((a, b) => a.topic_id - b.topic_id);

  return (
    <div className="space-y-12">
      <section>
        <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2">
          <Link
            href={schoolHref("/", school)}
            className="rounded-sm text-sm text-muted-foreground underline underline-offset-4 hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
          >
            Все темы
          </Link>
          <TopicSwitcher topics={programOrder} current={topic.topic_id} school={school} />
        </div>
        <h1 className="mt-3 text-3xl leading-tight font-semibold sm:text-4xl">{topic.topic}</h1>
        {selected && <p className="mt-1 text-lg text-muted-foreground">{selected.school}</p>}
        <div className="mt-6 flex flex-wrap items-end gap-x-10 gap-y-4 tabular-nums">
          <div>
            <p className="text-5xl font-semibold">{formatScore(topic.avg_score)}</p>
            <p className="mt-1 text-sm text-muted-foreground">
              средний балл из 100
              <AllSchools value={topic.avg_score_all} format={formatScore} />
            </p>
          </div>
          <dl className="flex flex-wrap gap-x-8 gap-y-3 text-sm">
            <div>
              <dt className="text-muted-foreground">Не справились</dt>
              <dd className="mt-0.5 text-lg font-medium">
                {formatPercent(topic.fail_rate)}
                <AllSchools value={topic.fail_rate_all} format={formatPercent} className="text-sm" />
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">
                <Term term="difficulty_index">Индекс сложности</Term>
              </dt>
              <dd className="mt-0.5 text-lg font-medium">
                {formatIndex(topic.difficulty_index)}
                <AllSchools value={topic.difficulty_index_all} format={formatIndex} className="text-sm" />
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">По плану</dt>
              <dd className="mt-0.5 text-lg font-medium">{formatHours(topic.hours_planned)}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Уровень</dt>
              <dd className="mt-0.5 text-lg font-medium">
                <LevelMark level={topic.level} />
              </dd>
            </div>
          </dl>
        </div>
      </section>

      {recommendation && (
        <section aria-labelledby="advice-title" className="max-w-prose border-l-2 border-primary pl-4">
          <h2 id="advice-title" className="text-xl font-semibold">
            Что делать
          </h2>
          <p className="mt-1">{recommendation.reason}</p>
          {recommendation.delta_all !== undefined && recommendation.hours_recommended_all !== undefined && (
            <p className="mt-1 text-sm text-muted-foreground tabular-nums">
              По всем школам:{" "}
              {recommendation.delta_all === 0
                ? "без изменений"
                : `${signedHours.format(recommendation.delta_all)} ч (${recommendation.hours_current} → ${recommendation.hours_recommended_all})`}
              .
            </p>
          )}
          {recommendation.by_textbook.some((row) => row.delta !== recommendation.delta) && (
            <ul className="mt-3 space-y-2 text-sm">
              {recommendation.by_textbook.map((row) => (
                <li key={row.textbook} className="grid gap-x-4 sm:grid-cols-[7rem_1fr]">
                  <span className="font-medium tabular-nums">
                    {row.textbook}
                    {row.delta !== null && row.delta !== 0 && ` ${signedHours.format(row.delta)} ч`}
                  </span>
                  <span className="text-muted-foreground">
                    {row.delta === null ? row.reason.replace(`${row.textbook}: `, "") : row.reason.replace(`${row.textbook}. `, "")}
                  </span>
                </li>
              ))}
            </ul>
          )}
          <Link
            href={schoolHref(`/textbooks?topic_id=${topic.topic_id}`, school)}
            className="mt-2 inline-block text-sm text-primary underline underline-offset-4"
          >
            Сравнить учебники по этой теме
          </Link>
        </section>
      )}

      <TopicLinks data={prerequisites} topicId={topic.topic_id} school={school} />

      {trend && trend.direction !== "без заметных изменений" && (
        <section aria-labelledby="trend-title" className="flex flex-wrap items-center gap-x-6 gap-y-2">
          <TrendSparkline trend={trend} />
          <div>
            <h2 id="trend-title" className="text-xl font-semibold">
              Динамика по годам
            </h2>
            <p className="text-sm text-muted-foreground">{trend.text}</p>
          </div>
        </section>
      )}

      <section aria-labelledby="distribution-title">
        <h2 id="distribution-title" className="text-xl font-semibold">
          Распределение баллов
        </h2>
        <ul className="mt-1 mb-4 flex flex-wrap gap-x-4 text-sm text-muted-foreground">
          <li className="flex items-center gap-1.5">
            <span aria-hidden className="size-3 rounded-sm bg-score-1" />
            ниже 50 баллов, не справились
          </li>
          <li className="flex items-center gap-1.5">
            <span aria-hidden className="size-3 rounded-sm bg-score-5" />
            50 баллов и выше
          </li>
        </ul>
        <ScoreDistribution data={topic.score_distribution} />
        <details className="mt-3 text-sm">
          <summary className="cursor-pointer text-muted-foreground hover:text-foreground">Показать таблицей</summary>
          <table className="mt-2 tabular-nums">
            <thead>
              <tr className="text-muted-foreground">
                <th scope="col" className="py-1 pr-8 text-left font-normal">
                  Баллы
                </th>
                <th scope="col" className="py-1 text-right font-normal">
                  Результатов
                </th>
              </tr>
            </thead>
            <tbody>
              {topic.score_distribution.map((row) => (
                <tr key={row.range} className="border-t">
                  <td className="py-1 pr-8">{row.range}</td>
                  <td className="py-1 text-right">{row.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      </section>

      <ItemIssues data={itemQuality} />

      {topic.by_class ? (
        <section aria-labelledby="classes-title">
          <h2 id="classes-title" className="text-xl font-semibold">
            По классам
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {selected?.school}: средний балл по теме
            <AllSchools value={topic.avg_score_all} format={formatScore} />.
          </p>
          <ul className="mt-3 max-w-md divide-y border-y tabular-nums">
            {topic.by_class.map((row) => (
              <li key={row.class_id} className="flex items-center justify-between gap-4 py-2">
                <span>
                  {row.class} <span className="text-sm text-muted-foreground">· {row.textbook}</span>
                </span>
                <span className={cn("rounded-sm px-2 py-0.5 text-sm", scoreBandClass(row.avg_score))}>
                  {formatScore(row.avg_score)}
                </span>
              </li>
            ))}
          </ul>
        </section>
      ) : (
        <section aria-labelledby="schools-title">
          <h2 id="schools-title" className="text-xl font-semibold">
            По школам
          </h2>
          <ul className="mt-3 max-w-md divide-y border-y tabular-nums">
            {topic.by_school.map((row) => (
              <li key={row.school_id}>
                <Link
                  href={schoolHref(`/topics/${topic.topic_id}`, row.school_id)}
                  className="flex items-center justify-between py-2 underline-offset-4 transition-colors duration-150 hover:bg-muted hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none sm:px-2"
                >
                  <span>{row.school}</span>
                  <span className={cn("rounded-sm px-2 py-0.5 text-sm", scoreBandClass(row.avg_score))}>
                    {formatScore(row.avg_score)}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
