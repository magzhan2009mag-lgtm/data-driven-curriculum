import { ArrowDown, ArrowRight, ArrowUp } from "lucide-react";
import Link from "next/link";
import { EmptyState } from "@/components/empty-state";
import { LevelMark } from "@/components/level-mark";
import { getRecommendations, type Recommendations } from "@/lib/api";
import { formatHours } from "@/lib/format";

type Item = Recommendations["items"][number];

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
      <h2 className="text-xl font-semibold">{title}</h2>
      <ul className="mt-3 divide-y border-y">
        {items.map((item) => (
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
            <p className="max-w-prose text-sm text-muted-foreground">{item.reason}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}

export default async function RecommendationsPage() {
  const { total_hours, hours_moved, items } = await getRecommendations();
  if (items.length === 0) return <EmptyState />;

  return (
    <div className="space-y-10">
      <section>
        <h1 className="max-w-3xl text-3xl leading-tight font-semibold sm:text-4xl">
          {hours_moved > 0 ? `Перенести ${formatHours(hours_moved)} с лёгких тем на сложные` : "Менять часы не требуется"}
        </h1>
        <p className="mt-3 max-w-prose text-muted-foreground">
          Сумма часов в программе не меняется: {formatHours(total_hours)}. Рекомендация основана на результатах тестов и
          не гарантирует рост баллов.
        </p>
      </section>
      <Group title="Добавить часы" items={items.filter((item) => item.delta > 0)} />
      <Group title="Можно сократить" items={items.filter((item) => item.delta < 0)} />
      <Group title="Без изменений" items={items.filter((item) => item.delta === 0)} />
    </div>
  );
}
