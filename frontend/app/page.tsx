import Link from "next/link";
import { AllSchools } from "@/components/all-schools";
import { DataVolume } from "@/components/data-volume";
import { EmptyState } from "@/components/empty-state";
import { OutlierNotice } from "@/components/outlier-notice";
import { RootCauses } from "@/components/root-causes";
import { ScoreHeatmap } from "@/components/score-heatmap";
import { SummaryCards } from "@/components/summary-cards";
import { TrendsList } from "@/components/trends-list";
import { getOutliers, getPrerequisites, getStats, getSummary, getTopics, getTrends } from "@/lib/api";
import { formatPercent, formatScore } from "@/lib/format";
import { inSchool, schoolHref } from "@/lib/school";
import { readScope } from "@/lib/scope";

export default async function HomePage({ searchParams }: PageProps<"/">) {
  const { school, selected } = await readScope(searchParams);
  const [topics, trends, outliers, prerequisites, summary, stats] = await Promise.all([
    getTopics(school),
    getTrends(school),
    getOutliers(school),
    getPrerequisites(school),
    getSummary(school),
    getStats(school),
  ]);
  if (topics.length === 0) return <EmptyState />;

  const hardest = topics[0];
  const attention = topics.filter((topic) => topic.level === "hard").slice(0, 3);

  return (
    <div className="space-y-12">
      <section>
        <h1 className="max-w-3xl text-3xl leading-tight font-semibold sm:text-4xl">
          {selected ? `${selected.school}: сложнее` : "Сложнее"} всего усваивается тема «{hardest.topic}»
        </h1>
        <DataVolume stats={stats} />
        <div className="mt-8">
          <SummaryCards cards={summary} school={school} />
        </div>

        {attention.length > 0 ? (
          <div className="mt-10">
            <h2 className="text-xl font-semibold">Требуют внимания</h2>
            <ol className="mt-3 divide-y border-y">
              {attention.map((topic, position) => (
                <li key={topic.topic_id}>
                  <Link
                    href={schoolHref(`/topics/${topic.topic_id}`, school)}
                    className="flex flex-wrap items-baseline gap-x-4 gap-y-1 py-3 transition-colors duration-150 hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none sm:px-2"
                  >
                    <span className="text-muted-foreground tabular-nums">{position + 1}</span>
                    <span className="font-medium">{topic.topic}</span>
                    <span className="text-sm text-muted-foreground tabular-nums sm:ml-auto">
                      балл {formatScore(topic.avg_score)}
                      <AllSchools value={topic.avg_score_all} format={formatScore} />, не справились{" "}
                      {formatPercent(topic.fail_rate)}
                    </span>
                  </Link>
                </li>
              ))}
            </ol>
            <Link
              href={schoolHref("/recommendations", school)}
              className="mt-3 inline-block text-sm text-primary underline underline-offset-4"
            >
              Как перераспределить часы
            </Link>
          </div>
        ) : (
          selected && (
            <p className="mt-6 max-w-prose border-l-2 border-primary pl-4">
              В {inSchool(selected.school)} сложных тем нет: даже самые трудные темы здесь средней сложности.
            </p>
          )
        )}
      </section>

      <RootCauses data={prerequisites} school={school} />
      <ScoreHeatmap topics={topics} selected={selected} />
      <TrendsList trends={trends} school={school} />
      <OutlierNotice data={outliers} school={school} />
    </div>
  );
}
