import { ArrowUpRight } from "lucide-react";
import Link from "next/link";
import { AllSchools } from "@/components/all-schools";
import type { SummaryCard } from "@/lib/api";
import { formatHours, formatScore, hoursWord } from "@/lib/format";
import { schoolHref } from "@/lib/school";

function Value({ card }: { card: SummaryCard }) {
  if (card.value === null) return null;
  const hours = card.unit === "hours";
  return (
    <p className="mt-2 tabular-nums">
      <span className="text-4xl leading-none font-semibold">{hours ? card.value : formatScore(card.value)}</span>
      <span className="ml-1.5 text-sm text-muted-foreground">{hours ? hoursWord(card.value) : "из 100"}</span>
      <AllSchools value={card.value_all} format={hours ? formatHours : formatScore} standalone className="mt-1 text-sm" />
    </p>
  );
}

/** «Главное за минуту»: четыре вывода с цифрой и ссылкой. Что показать, решает бэкенд (GET /summary). */
export function SummaryCards({ cards, school }: { cards: SummaryCard[]; school?: number }) {
  if (cards.length === 0) return null;
  return (
    <section aria-labelledby="summary-title">
      <h2 id="summary-title" className="text-xl font-semibold">
        Главное за минуту
      </h2>
      <ul className="mt-3 grid gap-px overflow-hidden rounded-md border bg-border sm:grid-cols-2 lg:grid-cols-4">
        {cards.map((card) => (
          <li key={card.kind} className="bg-background">
            <Link
              href={schoolHref(card.path, card.all_schools ? undefined : school)}
              className="group flex h-full flex-col p-4 transition-colors duration-150 hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none focus-visible:ring-inset"
            >
              <span className="flex items-start justify-between gap-2 text-sm text-muted-foreground">
                {card.label}
                <ArrowUpRight
                  className="size-4 shrink-0 transition-transform duration-150 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:text-primary motion-reduce:transition-none"
                  aria-hidden
                />
              </span>
              <Value card={card} />
              {card.headline && <span className="mt-3 font-medium">{card.headline}</span>}
              <span className="mt-1 text-sm text-muted-foreground">{card.text}</span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
