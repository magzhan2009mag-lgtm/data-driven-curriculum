import { ArrowDown, ArrowRight, ArrowUp } from "lucide-react";
import Link from "next/link";
import { Suspense } from "react";
import { AiExplanations, AiExplanationsSkeleton } from "@/components/ai-explanations";
import { EmptyState } from "@/components/empty-state";
import { HoursMatrix } from "@/components/hours-matrix";
import { LevelMark } from "@/components/level-mark";
import { getRecommendations, type Recommendations } from "@/lib/api";
import { formatHours } from "@/lib/format";

type Item = Recommendations["items"][number];
type Plan = Recommendations["textbook_plans"][number];

const signed = new Intl.NumberFormat("ru-RU", { signDisplay: "exceptZero" });
const list = new Intl.ListFormat("ru-RU", { type: "conjunction" });

function headline(plans: Plan[]): string {
  const busiest = plans.reduce<Plan | null>(
    (best, plan) => (plan.hours_moved > (best?.hours_moved ?? 0) ? plan : best),
    null,
  );
  if (!busiest) return "Менять часы не требуется";
  return `«${busiest.textbook}»: больше часов на ${list.format(busiest.added.map((item) => item.topic))}`;
}

function Change({ item }: { item: Item }) {
  if (item.delta === 0) {
    return <span className="text-xl font-semibold tabular-nums whitespace-nowrap">{item.hours_current} ч</span>;
  }
  const Icon = item.delta > 0 ? ArrowUp : ArrowDown;
  return (
    <span className="inline-flex items-center gap-2 text-xl font-semibold tabular-nums whitespace-nowrap">
      {item.hours_current}
      <ArrowRight className="size-4 text-muted-foreground" aria-label="станет" />
      {item.hours_recommended} ч
      <span className="inline-flex items-center text-sm font-normal text-muted-foreground">
        <Icon className="size-3.5" aria-hidden />
        {Math.abs(item.delta)}
      </span>
    </span>
  );
}

function Group({ title, items }: { title: string; items: Item[] }) {
  if (items.length === 0) return null;
  return (
    <section>
      <h3 className="text-lg font-semibold">{title}</h3>
      <ul className="mt-3 divide-y border-y">
        {items.map((item) => {
          const differs = item.by_textbook.filter((row) => row.delta !== item.delta);
          return (
            <li key={item.topic_id} className="grid gap-x-8 gap-y-1 py-4 sm:grid-cols-[14rem_9rem_1fr]">
              <div>
                <Link href={`/topics/${item.topic_id}`} className="font-medium underline-offset-4 hover:underline">
                  {item.topic}
                </Link>
                <div className="mt-0.5 text-sm text-muted-foreground">
                  <LevelMark level={item.level} />
                </div>
              </div>
              <Change item={item} />
              <div className="max-w-prose text-sm text-muted-foreground">
                <p>{item.reason}</p>
                {differs.length > 0 && (
                  <p className="mt-1 text-foreground tabular-nums">
                    По учебникам:{" "}
                    {item.by_textbook
                      .map((row) => `${row.textbook} ${row.delta === 0 ? "без изменений" : `${signed.format(row.delta)} ч`}`)
                      .join(", ")}
                    .
                  </p>
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

export default async function RecommendationsPage() {
  const { total_hours, items, textbook_plans } = await getRecommendations();
  if (items.length === 0) return <EmptyState />;

  return (
    <div className="space-y-12">
      <section>
        <h1 className="max-w-3xl text-3xl leading-tight font-semibold sm:text-4xl">{headline(textbook_plans)}</h1>
        <ul className="mt-4 max-w-prose space-y-1">
          {textbook_plans.map((plan) => (
            <li key={plan.textbook}>{plan.text}</li>
          ))}
        </ul>
        <p className="mt-2 max-w-prose text-sm text-muted-foreground">
          Учебники сравниваются так, будто они проходят в одинаковых школах.
        </p>
        <p className="mt-3 max-w-prose text-sm text-muted-foreground">
          Часы переносятся с лёгких тем на сложные, сумма в программе не меняется: {formatHours(total_hours)}. Чем
          сложнее тема, тем больше часов она получает; корень проблемы, от которого зависят сложные темы, получает ещё
          час. За раз тема меняется не больше чем на 30% плана (но всегда можно на 2 часа). Рекомендация основана на
          результатах тестов и не гарантирует рост баллов.
        </p>
      </section>

      <HoursMatrix items={items} />

      <Suspense fallback={<AiExplanationsSkeleton />}>
        <AiExplanations items={items} />
      </Suspense>

      <section className="space-y-8">
        <h2 className="text-xl font-semibold">Вся программа подробно</h2>
        <Group title="Добавить часы" items={items.filter((item) => item.delta > 0)} />
        <Group title="Можно сократить" items={items.filter((item) => item.delta < 0)} />
        <Group title="Без изменений" items={items.filter((item) => item.delta === 0)} />
      </section>
    </div>
  );
}
