import { PrerequisiteMap } from "@/components/prerequisite-map";
import type { Prerequisites } from "@/lib/api";

/** Темы, слабое освоение которых тянет за собой провал следующих тем. */
export function RootCauses({ data }: { data: Prerequisites | null }) {
  if (!data) return null;

  return (
    <section aria-labelledby="roots-title">
      <h2 id="roots-title" className="text-xl font-semibold">
        Корень проблемы
      </h2>
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
          <PrerequisiteMap data={data} />
          <p className="mt-4 max-w-prose text-sm text-muted-foreground">
            Сравниваем учеников одного общего уровня, поэтому сильные и слабые ученики связь не создают. {data.note}
          </p>
        </>
      )}
    </section>
  );
}
