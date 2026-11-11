import Link from "next/link";
import type { Outliers } from "@/lib/api";
import { formatScore } from "@/lib/format";
import { schoolHref } from "@/lib/school";

/**
 * Пары «класс × тема», результат которых не объясняется уровнем класса и учебником.
 * С выбранной школой блок виден всегда: «не найдено» тоже ответ для методиста этой школы.
 */
export function OutlierNotice({ data, school }: { data: Outliers | null; school?: number }) {
  if (!data) return null;
  if (data.outliers.length === 0 && !data.scope_note) return null;

  return (
    <section aria-labelledby="outliers-title">
      <h2 id="outliers-title" className="text-xl font-semibold">
        Необычный результат в классе
      </h2>
      <p className="mt-1 max-w-prose text-sm text-muted-foreground">
        Ожидаемый балл учитывает общий уровень класса и то, как тема даётся по его учебнику в других классах.
        {data.scope_note && ` ${data.scope_note}`}
      </p>
      {data.outliers.length === 0 ? (
        <p className="mt-3 max-w-prose">{data.conclusion}</p>
      ) : (
        <ul className="mt-3 divide-y border-y">
          {data.outliers.map((item) => (
            <li
              key={`${item.class_id}-${item.topic_id}`}
              className="grid gap-x-8 gap-y-1 py-4 sm:grid-cols-[14rem_10rem_1fr]"
            >
              <div>
                <p className="font-medium">
                  {item.class}, {item.school}
                </p>
                <Link
                  href={schoolHref(`/topics/${item.topic_id}`, school)}
                  className="text-sm text-muted-foreground underline underline-offset-4 hover:text-foreground"
                >
                  {item.topic}
                </Link>
              </div>
              <p className="tabular-nums">
                <span className="text-xl font-semibold">{formatScore(item.avg_score)}</span>
                <span className="text-sm text-muted-foreground"> при ожидаемых {formatScore(item.expected_score)}</span>
              </p>
              <p className="max-w-prose text-sm text-muted-foreground">{item.text}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
