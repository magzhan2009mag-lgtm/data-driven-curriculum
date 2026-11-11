import { Check, Minus, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { AllSchools } from "@/components/all-schools";
import { EmptyState } from "@/components/empty-state";
import { HowCalculated } from "@/components/how-calculated";
import { Term } from "@/components/term";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { TextbookDecisions } from "@/components/textbook-decisions";
import { getComparison, getDecisions, getRegression, getTopics } from "@/lib/api";
import { formatIndex, formatP, formatScore, formatSigned } from "@/lib/format";
import { inSchool, schoolHref } from "@/lib/school";
import { readScope } from "@/lib/scope";
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
  const { school, selected } = await readScope(searchParams);
  const [topics, comparison, regression, decisions] = await Promise.all([
    getTopics(school),
    getComparison(topicId, school),
    getRegression(topicId, school),
    getDecisions(school),
  ]);
  const topicPath = topicId === undefined ? "/textbooks" : `/textbooks?topic_id=${topicId}`;
  if (!comparison) notFound();
  if (topics.length === 0) return <EmptyState />;

  return (
    <div className="space-y-10">
      {decisions && (
        <section>
          {selected && <p className="mb-1 text-lg text-muted-foreground">{selected.school}</p>}
          <h1 id="decisions-title" className="text-3xl leading-tight font-semibold sm:text-4xl">
            Что решить по учебникам
          </h1>
          <TextbookDecisions data={decisions} school={school} titleId="decisions-title" />
        </section>
      )}

      <section>
        <h2 className="text-2xl leading-tight font-semibold">
          Сравнение учебников: {comparison.topic ? `«${comparison.topic}»` : "все темы"}
        </h2>
        {comparison.school_note ? (
          <div className="mt-4 max-w-prose border-l-2 border-primary pl-4">
            <p className="text-lg">{comparison.school_note}</p>
            <Link
              href={schoolHref(topicPath, undefined)}
              className="mt-2 inline-block text-primary underline underline-offset-4"
            >
              Открыть сравнение по всем школам
            </Link>
          </div>
        ) : (
          <p className="mt-3 max-w-prose text-lg">{comparison.conclusion}</p>
        )}
        <HowCalculated how={comparison.how} className="mt-3" />
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
        <TopicLink href={schoolHref("/textbooks", school)} active={topicId === undefined} label="Все темы" />
        {topics.map((topic) => (
          <TopicLink
            key={topic.topic_id}
            href={schoolHref(`/textbooks?topic_id=${topic.topic_id}`, school)}
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
                <p className="mt-1 text-sm text-muted-foreground">
                  {selected ? `в ${inSchool(selected.school)}` : <Term term="same_schools" className="whitespace-nowrap">в одинаковых школах</Term>}
                </p>
              </div>
              {/* В одной школе балл «в этой школе» и простое среднее совпадают: второе не показываем. */}
              {!selected && (
                <div>
                  <p className="text-xl text-muted-foreground">{formatScore(book.avg_score)}</p>
                  <p className="mt-1 text-sm text-muted-foreground">простое среднее</p>
                </div>
              )}
            </div>
            <AllSchools value={book.adjusted_score_all} format={formatScore} standalone className="mt-2 text-sm tabular-nums" />
            {book.enough_data ? (
              <p className="mt-2 text-sm text-muted-foreground">
                {book.n_students} уч., отклонение от среднего по школе и теме {formatSigned(book.mean_z)} σ
              </p>
            ) : (
              <p className="mt-2 flex items-start gap-1.5 text-sm">
                <TriangleAlert className="mt-0.5 size-3.5 shrink-0 text-destructive" aria-hidden />
                Всего {book.n_students} уч. — мало данных, вывод не делаем
              </p>
            )}
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
              <TableHead>
                <Term term="significant">Разница</Term>
              </TableHead>
              <TableHead>
                <Term term="effect_size">Размер эффекта</Term>
              </TableHead>
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
