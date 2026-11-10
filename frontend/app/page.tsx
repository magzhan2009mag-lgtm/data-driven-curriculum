import Link from "next/link";
import { EmptyState } from "@/components/empty-state";
import { OutlierNotice } from "@/components/outlier-notice";
import { RootCauses } from "@/components/root-causes";
import { ScoreHeatmap } from "@/components/score-heatmap";
import { TrendsList } from "@/components/trends-list";
import { getOutliers, getPrerequisites, getTopics, getTrends } from "@/lib/api";
import { formatPercent, formatScore } from "@/lib/format";

export default async function HomePage() {
  const [topics, trends, outliers, prerequisites] = await Promise.all([
    getTopics(),
    getTrends(),
    getOutliers(),
    getPrerequisites(),
  ]);
  if (topics.length === 0) return <EmptyState />;

  const hardest = topics[0];
  const attention = topics.filter((topic) => topic.level === "hard").slice(0, 3);

  return (
    <div className="space-y-12">
      <section>
        <h1 className="max-w-3xl text-3xl leading-tight font-semibold sm:text-4xl">
          Сложнее всего усваивается тема «{hardest.topic}»
        </h1>
        <p className="mt-3 max-w-prose text-muted-foreground">
          Средний балл {formatScore(hardest.avg_score)} из 100, не справились {formatPercent(hardest.fail_rate)}{" "}
          результатов. Ниже видно, в каких школах проблема острее.
        </p>

        {attention.length > 0 && (
          <div className="mt-8">
            <h2 className="text-xl font-semibold">Требуют внимания</h2>
            <ol className="mt-3 divide-y border-y">
              {attention.map((topic, position) => (
                <li key={topic.topic_id}>
                  <Link
                    href={`/topics/${topic.topic_id}`}
                    className="flex flex-wrap items-baseline gap-x-4 gap-y-1 py-3 transition-colors duration-150 hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none sm:px-2"
                  >
                    <span className="text-muted-foreground tabular-nums">{position + 1}</span>
                    <span className="font-medium">{topic.topic}</span>
                    <span className="text-sm text-muted-foreground sm:ml-auto">
                      балл {formatScore(topic.avg_score)}, не справились {formatPercent(topic.fail_rate)}
                    </span>
                  </Link>
                </li>
              ))}
            </ol>
            <Link href="/recommendations" className="mt-3 inline-block text-sm text-primary underline underline-offset-4">
              Как перераспределить часы
            </Link>
          </div>
        )}
      </section>

      <RootCauses data={prerequisites} />
      <ScoreHeatmap topics={topics} />
      <TrendsList trends={trends} />
      <OutlierNotice data={outliers} />
    </div>
  );
}
