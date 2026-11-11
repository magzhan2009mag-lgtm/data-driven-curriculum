/** Фильтр по школе живёт в адресе страницы: ?school=5. */
export const SCHOOL_PARAM = "school";

export function parseSchool(value: string | string[] | undefined): number | undefined {
  return typeof value === "string" && /^\d+$/.test(value) ? Number(value) : undefined;
}

/**
 * Единственная функция для внутренних ссылок: сохраняет выбранную школу при любом переходе.
 * Без school убирает фильтр из адреса; остальные параметры (например topic_id) не трогает.
 */
export function schoolHref(path: string, school: number | undefined): string {
  const [base, query = ""] = path.split("?");
  const params = new URLSearchParams(query);
  if (school === undefined) params.delete(SCHOOL_PARAM);
  else params.set(SCHOOL_PARAM, String(school));
  const search = params.toString();
  return search ? `${base}?${search}` : base;
}

/** «Школа №5» → «Школе №5»: для фраз «в Школе №5». */
export function inSchool(name: string): string {
  return name.replace("Школа", "Школе");
}
