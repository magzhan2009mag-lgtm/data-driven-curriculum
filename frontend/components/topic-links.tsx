import Link from "next/link";
import type { PrerequisiteLink, Prerequisites } from "@/lib/api";
import { schoolHref } from "@/lib/school";

function LinkList({ title, id, intro, items, other, school }: {
  title: string;
  school?: number;
  id: string;
  intro?: string;
  items: PrerequisiteLink[];
  other: (link: PrerequisiteLink) => { id: number; name: string };
}) {
  return (
    <section aria-labelledby={id}>
      <h2 id={id} className="text-xl font-semibold">
        {title}
      </h2>
      {intro && <p className="mt-1 max-w-prose">{intro}</p>}
      <ul className="mt-3 divide-y border-y">
        {items.map((link) => {
          const topic = other(link);
          return (
            <li key={`${link.from_topic_id}-${link.to_topic_id}`} className="py-3">
              <Link href={schoolHref(`/topics/${topic.id}`, school)} className="font-medium underline-offset-4 hover:underline">
                {topic.name}
              </Link>
              <p className="mt-0.5 max-w-prose text-sm text-muted-foreground">{link.text}</p>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

/** «Опирается на» и «От неё зависят»: связи темы с другими темами программы. */
export function TopicLinks({ data, topicId, school }: { data: Prerequisites | null; topicId: number; school?: number }) {
  if (!data) return null;
  const basis = data.links.filter((link) => link.to_topic_id === topicId);
  const dependents = data.links.filter((link) => link.from_topic_id === topicId);
  if (basis.length === 0 && dependents.length === 0) return null;
  const root = data.roots.find((item) => item.topic_id === topicId);

  return (
    <div className="grid grid-cols-1 gap-x-12 gap-y-10 lg:grid-cols-2">
      {basis.length > 0 && (
        <LinkList
          title="Опирается на"
          id="basis-title"
          items={basis}
          school={school}
          other={(link) => ({ id: link.from_topic_id, name: link.from_topic })}
        />
      )}
      {dependents.length > 0 && (
        <LinkList
          title="От неё зависят"
          id="dependents-title"
          intro={root?.text}
          items={dependents}
          school={school}
          other={(link) => ({ id: link.to_topic_id, name: link.to_topic })}
        />
      )}
    </div>
  );
}
