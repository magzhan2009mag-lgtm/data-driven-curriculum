import Link from "next/link";
import type { Recommendations, School } from "@/lib/api";
import { schoolHref } from "@/lib/school";
import { cn } from "@/lib/utils";

const signed = new Intl.NumberFormat("ru-RU", { signDisplay: "exceptZero" });

function DeltaCell({
  delta,
  hours,
  title,
  muted = false,
}: {
  delta: number | null | undefined;
  hours: number | null | undefined;
  title: string;
  muted?: boolean;
}) {
  if (delta === null || delta === undefined || hours === null || hours === undefined) {
    return (
      <td title={title} className="rounded-sm px-2 py-1.5 text-center text-muted-foreground">
        <span aria-label="мало данных">—</span>
      </td>
    );
  }
  return (
    <td
      title={title}
      className={cn(
        "rounded-sm px-2 py-1.5 text-center whitespace-nowrap",
        delta > 0 && !muted && "bg-primary font-semibold text-primary-foreground",
        delta > 0 && muted && "bg-accent font-medium text-accent-foreground",
        delta < 0 && "bg-muted text-muted-foreground",
        delta === 0 && "text-muted-foreground",
      )}
    >
      {delta === 0 ? (
        <span aria-label="без изменений">·</span>
      ) : (
        <>
          {signed.format(delta)} <span className="text-xs font-normal opacity-80">→ {hours}</span>
        </>
      )}
    </td>
  );
}

/** Матрица «тема × учебник»: сколько часов добавить или снять классам каждого учебника. */
export function HoursMatrix({
  items,
  plans,
  selected,
}: {
  items: Recommendations["items"];
  plans: Recommendations["textbook_plans"];
  selected?: School;
}) {
  const textbooks = items[0]?.by_textbook.map((row) => row.textbook) ?? [];
  const withoutPlan = new Set(plans.filter((plan) => !plan.enough_data).map((plan) => plan.textbook));

  return (
    <section aria-labelledby="matrix-title">
      <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-3">
        <div>
          <h2 id="matrix-title" className="text-xl font-semibold">
            Часы по темам и учебникам
          </h2>
          <p className="mt-1 max-w-prose text-sm text-muted-foreground">
            Для классов каждого учебника свой перенос часов, в каждом плане сумма не меняется. Наведите на ячейку,
            чтобы увидеть причину.
            {selected && " Последний столбец — план по всем школам для сравнения."}
          </p>
        </div>
        <ul aria-label="Обозначения" className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground">
          <li className="flex items-center gap-1.5">
            <span aria-hidden className="size-3 rounded-sm bg-primary" />
            добавить часы
          </li>
          <li className="flex items-center gap-1.5">
            <span aria-hidden className="size-3 rounded-sm bg-muted ring-1 ring-border" />
            можно сократить
          </li>
          <li>· без изменений</li>
        </ul>
      </div>

      <div className="mt-4 overflow-x-auto">
        <table className="w-full border-separate border-spacing-0.5 text-sm tabular-nums">
          <thead>
            <tr className="text-xs text-muted-foreground">
              <th scope="col" className="sticky left-0 z-10 bg-background px-2 py-1 text-left align-bottom font-normal">
                Тема
              </th>
              <th scope="col" className="px-2 py-1 text-right align-bottom font-normal whitespace-nowrap">
                По плану
              </th>
              <th scope="col" className="min-w-20 px-2 py-1 align-bottom font-normal whitespace-nowrap">
                {selected ? `Все классы, ${selected.school}` : "Все классы"}
              </th>
              {textbooks.map((name) => (
                <th key={name} scope="col" className="min-w-20 px-2 py-1 align-bottom font-normal whitespace-nowrap">
                  {name}
                  {withoutPlan.has(name) && <span className="block text-destructive">мало данных</span>}
                </th>
              ))}
              {selected && (
                <th scope="col" className="min-w-20 px-2 py-1 align-bottom font-normal whitespace-nowrap">
                  Все школы
                </th>
              )}
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.topic_id}>
                <th scope="row" className="sticky left-0 z-10 min-w-36 bg-background px-2 py-1 text-left font-normal">
                  <Link
                    href={schoolHref(`/topics/${item.topic_id}`, selected?.school_id)}
                    className="rounded-sm underline-offset-4 hover:text-primary hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
                  >
                    {item.topic}
                  </Link>
                </th>
                <td className="px-2 py-1.5 text-right">{item.hours_current} ч</td>
                <DeltaCell delta={item.delta} hours={item.hours_recommended} title={item.reason} />
                {item.by_textbook.map((row) => (
                  <DeltaCell key={row.textbook} delta={row.delta} hours={row.hours_recommended} title={row.reason} />
                ))}
                {selected && (
                  <DeltaCell
                    delta={item.delta_all}
                    hours={item.hours_recommended_all}
                    title={`${item.topic}: план по всем школам`}
                    muted
                  />
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
