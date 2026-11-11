import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { HowCalculated } from "@/components/how-calculated";
import type { Decisions } from "@/lib/api";
import { schoolHref } from "@/lib/school";
import { cn } from "@/lib/utils";

type Verdict = Decisions["textbooks"][number]["verdict"];

/** Метка решения: цвет только дублирует текст. */
const VERDICTS: Record<Verdict, { label: string; className: string }> = {
  replace: { label: "Рассмотреть замену", className: "border-destructive/40 text-destructive" },
  strengthen: { label: "Усилить отдельные темы", className: "border-border text-foreground" },
  strong: { label: "Сильнее других", className: "border-primary/40 text-primary" },
  equal: { label: "Равноценен", className: "border-border text-muted-foreground" },
};

/** «Что решить по учебникам»: строка-вывод на учебник по значимым разницам в одних и тех же школах. */
export function TextbookDecisions({ data, school, titleId }: { data: Decisions; school?: number; titleId: string }) {
  return (
    <div>
      {data.note && (
        <p className="mt-2 max-w-prose text-sm text-muted-foreground">
          {data.note}{" "}
          <Link href={schoolHref("/textbooks", undefined)} className="text-primary underline underline-offset-4">
            Сравнение по всем школам
          </Link>
        </p>
      )}
      <ul aria-labelledby={titleId} className="mt-4 divide-y border-y">
        {data.textbooks.map((item) => {
          const verdict = VERDICTS[item.verdict];
          return (
            <li key={item.textbook} className="grid gap-x-8 gap-y-2 py-4 md:grid-cols-[12rem_1fr]">
              <div>
                <p className="font-heading text-lg font-semibold">{item.textbook}</p>
                <span className={cn("mt-1 inline-block rounded-sm border px-1.5 py-0.5 text-xs", verdict.className)}>
                  {verdict.label}
                </span>
              </div>
              <div className="max-w-prose">
                <p>{item.text}</p>
                {item.advice && (
                  <p className="mt-2 border-l-2 border-primary pl-3 font-medium">
                    {item.advice}{" "}
                    <Link
                      href={schoolHref("/recommendations", school)}
                      className="inline-flex items-center gap-1 font-normal whitespace-nowrap text-primary underline underline-offset-4"
                    >
                      План часов
                      <ArrowRight className="size-3.5" aria-hidden />
                    </Link>
                  </p>
                )}
                <HowCalculated how={item.how} className="mt-2" />
              </div>
            </li>
          );
        })}
      </ul>
      <p className="mt-3 max-w-prose text-sm text-muted-foreground">
        Учитываем только значимые разницы (с поправкой Холма) по каждой из {data.n_topics} тем, сравнивая классы одной
        и той же школы. Замену советуем, только если отставание хотя бы среднее по размеру эффекта.
      </p>
    </div>
  );
}
