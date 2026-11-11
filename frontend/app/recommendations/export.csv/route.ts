import { API_URL } from "@/lib/api";
import { parseSchool } from "@/lib/school";

/**
 * «Скачать для Excel»: отдаёт CSV с бэкенда с того же адреса, что и сайт.
 * Школа приходит так же, как на страницах: ?school=5.
 */
export async function GET(request: Request) {
  const school = parseSchool(new URL(request.url).searchParams.get("school") ?? undefined);
  const query = school === undefined ? "" : `?school_id=${school}`;
  const upstream = await fetch(`${API_URL}/recommendations/export.csv${query}`, { cache: "no-store" });
  if (!upstream.ok) {
    const message = upstream.status === 404 ? "Школа не найдена" : "Не удалось получить план часов";
    return new Response(message, { status: upstream.status, headers: { "Content-Type": "text/plain; charset=utf-8" } });
  }
  return new Response(upstream.body, {
    headers: {
      "Content-Type": upstream.headers.get("Content-Type") ?? "text/csv; charset=utf-8",
      "Content-Disposition": upstream.headers.get("Content-Disposition") ?? 'attachment; filename="hours.csv"',
      "Cache-Control": "no-store",
    },
  });
}
