import { Check, Minus, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { EmptyState } from "@/components/empty-state";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { getComparison, getRegression, getTopics } from "@/lib/api";
import { formatIndex, formatP, formatScore, formatSigned } from "@/lib/format";
import { cn } from "@/lib/utils";

function TopicLink({ href, active, label }: { href: string; active: boolean; label: string }) {
  return (
    <Link
      href={href}
      scroll={false}
      aria-current={active ? "page" : undefined}
      className={cn(
        "rounded-sm border px-2.5 py-1 text-sm transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
        active ? "border-primary bg-primary text-primary-foreground" : "hover:bg-muted",
      )}
    >
      {label}
    </Link>
  );
}

export default async function TextbooksPage({ searchParams }: PageProps<"/textbooks">) {
  const { topic_id: rawId } = await searchParams;
  const topicId = typeof rawId === "string" && /^\d+$/.test(rawId) ? Number(rawId) : undefined;
  const [topics, comparison, regression] = await Promise.all([
    getTopics(),
    getComparison(topicId),
    getRegression(topicId),
  ]);
  if (!comparison) notFound();
  if (topics.length === 0) return <EmptyState />;

  return (
    <div className="space-y-10">
      <section>
        <h1 className="text-3xl leading-tight font-semibold sm:text-4xl">
          Сравнение учебников: {comparison.topic ? `«${comparison.topic}»` : "все темы"}
        </h1>
        <p className="mt-3 max-w-prose text-lg">{comparison.conclusion}</p>
      </section>

      {comparison.confounding_note && (
        <section aria-labelledby="confounding-title" className="max-w-prose border-l-2 border-primary pl-4">
          <h2 id="confounding-title" className="flex items-center gap-2 text-xl font-semibold">
            <TriangleAlert className="size-4 text-primary" aria-hidden />
            Простое сравнение средних вводит в заблуждение
          </h2>
          <p className="mt-1">{comparison.confounding_note}</p>
          {regression && (
            <p className="mt-2 text-sm text-muted-foreground">
              Проверка регрессией, где учтены школа и тема: {regression.conclusion}
            </p>
          )}
        </section>
      )}

      <nav aria-label="Выбор темы" className="flex flex-wrap gap-1.5">
        <TopicLink href="/textbooks" active={topicId === undefined} label="Все темы" />
        {topics.map((topic) => (
          <TopicLink
            key={topic.topic_id}
            href={`/textbooks?topic_id=${topic.topic_id}`}
            active={topic.topic_id === topicId}
            label={topic.topic}
          />
        ))}
      </nav>

      <section aria-label="Показатели учебников" className="grid gap-x-8 border-y sm:grid-cols-3">
        {comparison.textbooks.map((book) => (
          <div key={book.textbook_id} className="border-t py-5 first:border-t-0 sm:border-t-0">
            <h2 className="font-medium">{book.name}</h2>
            <div className="mt-2 flex items-baseline gap-x-6 tabular-nums">
              <div>
                <p className="text-4xl font-semibold">{formatScore(book.adjusted_score)}</p>
                <p className="mt-1 text-sm text-muted-foreground">в одинаковых школах</p>
              </div>
              <div>
                <p className="text-xl text-muted-foreground">{formatScore(book.avg_score)}</p>
                <p className="mt-1 text-sm text-muted-foreground">простое среднее</p>
              </div>
            </div>
            <p className="mt-2 text-sm text-muted-foreground">
              {book.n_students} уч., отклонение от среднего по школе и теме {formatSigned(book.mean_z)} σ
            </p>
          </div>
        ))}
      </section>

      <section aria-labelledby="pairs-title">
        <h2 id="pairs-title" className="text-xl font-semibold">
          Есть ли реальная разница
        </h2>
        <Table className="mt-3 tabular-nums">
          <TableHeader>
            <TableRow>
              <TableHead>Пара учебников</TableHead>
              <TableHead>Разница</TableHead>
              <TableHead>Размер эффекта</TableHead>
              <TableHead className="text-right">d Коэна</TableHead>
              <TableHead className="text-right">p с поправкой</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {comparison.comparisons.map((pair) => (
              <TableRow key={`${pair.a}-${pair.b}`}>
                <TableCell>
                  {pair.a} и {pair.b}
                </TableCell>
                <TableCell>
                  <span className="inline-flex items-center gap-1.5">
                    {pair.significant ? <Check className="size-4" aria-hidden /> : <Minus className="size-4" aria-hidden />}
                    {pair.p_adjusted === null ? "Мало данных" : pair.significant ? "Значимая" : "Не подтверждена"}
                  </span>
                </TableCell>
                <TableCell>{pair.effect}</TableCell>
                <TableCell className="text-right">{pair.cohens_d === null ? "—" : formatIndex(pair.cohens_d)}</TableCell>
                <TableCell className="text-right">{pair.p_adjusted === null ? "—" : formatP(pair.p_adjusted)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        <p className="mt-4 max-w-prose text-sm text-muted-foreground">{comparison.limitation}</p>
      </section>
    </div>
  );
}
