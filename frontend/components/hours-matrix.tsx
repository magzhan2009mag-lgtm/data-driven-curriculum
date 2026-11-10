import Link from "next/link";
import type { Recommendations } from "@/lib/api";
import { cn } from "@/lib/utils";

const signed = new Intl.NumberFormat("ru-RU", { signDisplay: "exceptZero" });

function DeltaCell({ delta, hours, title }: { delta: number; hours: number; title: string }) {
  return (
    <td
      title={title}
      className={cn(
        "rounded-sm px-2 py-1.5 text-center whitespace-nowrap",
        delta > 0 && "bg-primary font-semibold text-primary-foreground",
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
export function HoursMatrix({ items }: { items: Recommendations["items"] }) {
  const textbooks = items[0]?.by_textbook.map((row) => row.textbook) ?? [];

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
              <th scope="col" className="sticky left-0 bg-background px-2 py-1 text-left font-normal">
                Тема
              </th>
              <th scope="col" className="px-2 py-1 text-right font-normal whitespace-nowrap">
                По плану
              </th>
              <th scope="col" className="min-w-20 px-2 py-1 font-normal whitespace-nowrap">
                Все классы
              </th>
              {textbooks.map((name) => (
                <th key={name} scope="col" className="min-w-20 px-2 py-1 font-normal whitespace-nowrap">
                  {name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.topic_id}>
                <th scope="row" className="sticky left-0 min-w-36 bg-background px-2 py-1 text-left font-normal">
                  <Link href={`/topics/${item.topic_id}`} className="underline-offset-4 hover:text-primary hover:underline">
                    {item.topic}
                  </Link>
                </th>
                <td className="px-2 py-1.5 text-right">{item.hours_current} ч</td>
                <DeltaCell delta={item.delta} hours={item.hours_recommended} title={item.reason} />
                {item.by_textbook.map((row) => (
                  <DeltaCell key={row.textbook} delta={row.delta} hours={row.hours_recommended} title={row.reason} />
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
