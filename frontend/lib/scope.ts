import { notFound } from "next/navigation";
import { getSchools, type School } from "@/lib/api";
import { parseSchool } from "@/lib/school";

export type Scope = { school: number | undefined; selected: School | undefined };

/** Школа из адреса страницы. Неизвестная школа — страница 404, как и в API. */
export async function readScope(searchParams: Promise<Record<string, string | string[] | undefined>>): Promise<Scope> {
  const school = parseSchool((await searchParams).school);
  if (school === undefined) return { school: undefined, selected: undefined };
  const selected = (await getSchools()).find((item) => item.school_id === school);
  if (!selected) notFound();
  return { school, selected };
}
