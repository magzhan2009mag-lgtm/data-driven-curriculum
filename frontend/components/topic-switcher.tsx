"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { schoolHref } from "@/lib/school";
import { cn } from "@/lib/utils";

type Topic = { topic_id: number; topic: string };

const STEP_CLASS =
  "inline-flex h-9 items-center rounded-md px-2.5 text-sm whitespace-nowrap underline-offset-4 transition-colors duration-150 hover:bg-muted hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none";

/** Переход между темами в порядке программы: список всех тем и «← предыдущая / следующая →». Фильтр по школе сохраняется. */
export function TopicSwitcher({ topics, current, school }: { topics: Topic[]; current: number; school?: number }) {
  const router = useRouter();
  const index = topics.findIndex((topic) => topic.topic_id === current);
  const previous = index > 0 ? topics[index - 1] : undefined;
  const next = index >= 0 && index < topics.length - 1 ? topics[index + 1] : undefined;
  const items = topics.map((topic, position) => ({ value: String(topic.topic_id), label: `${position + 1}. ${topic.topic}` }));

  return (
    <nav aria-label="Другие темы программы" className="flex flex-wrap items-center gap-1">
      {previous ? (
        <Link
          href={schoolHref(`/topics/${previous.topic_id}`, school)}
          title={previous.topic}
          aria-label={`Предыдущая тема: ${previous.topic}`}
          className={STEP_CLASS}
        >
          ← предыдущая
        </Link>
      ) : (
        <span className={cn(STEP_CLASS, "pointer-events-none text-muted-foreground/60")} aria-hidden>
          ← предыдущая
        </span>
      )}
      <Select
        items={items}
        value={String(current)}
        onValueChange={(value) => {
          if (typeof value === "string") router.push(schoolHref(`/topics/${value}`, school));
        }}
      >
        <SelectTrigger aria-label="Тема" className="w-60">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {items.map((item) => (
            <SelectItem key={item.value} value={item.value}>
              {item.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {next ? (
        <Link
          href={schoolHref(`/topics/${next.topic_id}`, school)}
          title={next.topic}
          aria-label={`Следующая тема: ${next.topic}`}
          className={STEP_CLASS}
        >
          следующая →
        </Link>
      ) : (
        <span className={cn(STEP_CLASS, "pointer-events-none text-muted-foreground/60")} aria-hidden>
          следующая →
        </span>
      )}
    </nav>
  );
}
