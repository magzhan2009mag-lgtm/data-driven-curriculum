import type { Stats } from "@/lib/api";
import { pluralize } from "@/lib/format";

/** «Проанализировано: …» — объём данных из GET /stats, числа не вписаны вручную. */
export function DataVolume({ stats }: { stats: Stats | null }) {
  if (!stats) return null;
  const parts = [
    pluralize(stats.n_results, ["результат теста", "результата тестов", "результатов тестов"]),
    pluralize(stats.n_item_responses, ["ответ на задания", "ответа на задания", "ответов на задания"]),
    pluralize(stats.n_students, ["ученик", "ученика", "учеников"]),
    pluralize(stats.n_classes, ["класс", "класса", "классов"]),
    pluralize(stats.n_schools, ["школа", "школы", "школ"]),
  ];
  if (stats.archive_from !== null && stats.archive_to !== null) {
    parts.push(`архив ${stats.archive_from}–${stats.archive_to}`);
  }
  return <p className="mt-3 max-w-3xl text-sm text-muted-foreground tabular-nums">Проанализировано: {parts.join(", ")}.</p>;
}
