import type { ItemQuality } from "@/lib/api";
import { formatPercent } from "@/lib/format";

const EXPLANATION: Record<string, string> = {
  "не различает сильных и слабых":
    "На него одинаково часто отвечают и сильные, и слабые ученики. Похоже на неудачную формулировку или ошибку в ключе.",
  "слишком лёгкое": "С ним справляются почти все, поэтому оно мало говорит о подготовке.",
  "слишком трудное": "С ним не справляется почти никто, поэтому оно мало говорит о подготовке.",
};

/** Задания тестов темы, которые стоит проверить: сначала неразличающие, затем слишком лёгкие и трудные. */
export function ItemIssues({ data }: { data: ItemQuality | null }) {
  if (!data) return null;
  const flagged = data.items
    .filter((item) => item.issue !== null)
    .sort((a, b) => Number(b.is_bad) - Number(a.is_bad));

  return (
    <section aria-labelledby="items-title">
      <h2 id="items-title" className="text-xl font-semibold">
        Задания тестов
      </h2>
      {flagged.length === 0 ? (
        <p className="mt-1 max-w-prose text-sm text-muted-foreground">
          Все {data.items.length} заданий различают сильных и слабых учеников.
        </p>
      ) : (
        <>
          <p className="mt-1 max-w-prose text-sm text-muted-foreground">
            Проверено {data.items.length} заданий. Эти стоит пересмотреть: они искажают балл по теме.
          </p>
          <ul className="mt-3 max-w-3xl divide-y border-y">
            {flagged.map((item) => (
              <li key={item.item_id} className="grid gap-x-8 gap-y-1 py-3 sm:grid-cols-[12rem_1fr]">
                <div>
                  <p className="font-medium">
                    Тест {item.test_number}, задание {item.item_number}
                  </p>
                  <p className="text-sm text-muted-foreground tabular-nums">
                    верно ответили {formatPercent(item.p_correct)}
                  </p>
                </div>
                <p className="text-sm">
                  <span className={item.is_bad ? "font-medium text-destructive" : "font-medium"}>
                    {item.issue![0].toUpperCase() + item.issue!.slice(1)}.
                  </span>{" "}
                  <span className="text-muted-foreground">{EXPLANATION[item.issue!]}</span>
                </p>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
