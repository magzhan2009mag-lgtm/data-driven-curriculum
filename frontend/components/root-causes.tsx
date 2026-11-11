import { PrerequisiteMap } from "@/components/prerequisite-map";
import { Term } from "@/components/term";
import type { Prerequisites } from "@/lib/api";

/** Темы, слабое освоение которых тянет за собой провал следующих тем. */
export function RootCauses({ data, school }: { data: Prerequisites | null; school?: number }) {
  if (!data) return null;

  return (
    <section aria-labelledby="roots-title">
      <h2 id="roots-title" className="text-xl font-semibold">
        <Term term="root">Корень проблемы</Term>
      </h2>
      {data.scope_note && <p className="mt-1 max-w-prose text-sm text-muted-foreground">{data.scope_note}</p>}
      {data.links.length === 0 ? (
        <p className="mt-1 max-w-prose text-sm text-muted-foreground">{data.conclusion}</p>
      ) : (
        <>
          {data.roots.length > 0 && (
            <ul className="mt-3 max-w-prose space-y-2 text-lg leading-snug">
              {data.roots.map((root) => (
                <li key={root.topic_id}>{root.text}</li>
              ))}
            </ul>
          )}
          <PrerequisiteMap data={data} school={school} />
          <p className="mt-4 max-w-prose text-sm text-muted-foreground">
            Сравниваем учеников одного общего уровня, поэтому сильные и слабые ученики связь не создают. {data.note}
          </p>
        </>
      )}
    </section>
  );
}
