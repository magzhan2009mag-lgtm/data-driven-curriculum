import { Sparkles } from "lucide-react";
import Link from "next/link";
import { getExplanations, type Recommendations } from "@/lib/api";
import { schoolHref } from "@/lib/school";

/**
 * Пояснения от Claude для тем, где часы меняются. Грузится отдельно, чтобы не задерживать страницу.
 * Если ИИ недоступен (нет ключа или связи), блока нет: на странице остаются шаблонные тексты.
 */
export async function AiExplanations({ items, school }: { items: Recommendations["items"]; school?: number }) {
  const explanations = await getExplanations(school);
  if (!explanations || explanations.source !== "llm") return null;

  const changed = items.filter((item) => item.delta !== 0 || item.by_textbook.some((row) => row.delta !== null && row.delta !== 0));

  const texts = new Map(explanations.items.map((item) => [item.topic_id, item.explanation]));
  return (
    <section aria-labelledby="ai-title" className="border-l-2 border-primary pl-4">
      <h2 id="ai-title" className="flex items-center gap-2 text-xl font-semibold">
        <Sparkles className="size-4 text-primary" aria-hidden />
        Простыми словами
      </h2>
      <p className="mt-1 text-xs text-muted-foreground">
        Пояснение ИИ (Claude) по тем же цифрам. Решение остаётся за методистом.
      </p>
      <dl className="mt-3 max-w-prose space-y-3">
        {changed.map((item) => (
          <div key={item.topic_id}>
            <dt>
              <Link href={schoolHref(`/topics/${item.topic_id}`, school)} className="font-medium underline-offset-4 hover:underline">
                {item.topic}
              </Link>
            </dt>
            <dd className="text-sm">{texts.get(item.topic_id)}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

export function AiExplanationsSkeleton() {
  return (
    <div className="max-w-prose space-y-2" aria-busy="true" aria-label="Готовим пояснения ИИ">
      <div className="h-5 w-48 animate-pulse rounded-sm bg-muted motion-reduce:animate-none" />
      <div className="h-4 w-full animate-pulse rounded-sm bg-muted motion-reduce:animate-none" />
      <div className="h-4 w-4/5 animate-pulse rounded-sm bg-muted motion-reduce:animate-none" />
    </div>
  );
}
