import "@fontsource-variable/literata/index.css";
import "@fontsource-variable/onest/index.css";
import type { Metadata } from "next";
import { Suspense } from "react";
import { DemoBadge } from "@/components/demo-badge";
import { SchoolFilter } from "@/components/school-filter";
import { SchoolLink } from "@/components/school-link";
import { SiteNav } from "@/components/site-nav";
import { getSchools, type School } from "@/lib/api";
import "./globals.css";

export const metadata: Metadata = {
  title: "Аналитика программы",
  description: "Сложные темы, сравнение учебников и рекомендации по учебным часам",
};

/** Список школ для фильтра. Если сервер аналитики не отвечает, шапка остаётся без фильтра, а ошибку покажет страница. */
async function loadSchools(): Promise<School[]> {
  try {
    return await getSchools();
  } catch {
    return [];
  }
}

export default async function RootLayout({ children }: LayoutProps<"/">) {
  const schools = await loadSchools();
  return (
    <html lang="ru" className="h-full antialiased">
      <body className="flex min-h-full flex-col">
        <header className="border-b">
          <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center gap-x-8 gap-y-3 px-4 py-3 sm:px-8">
            <div className="flex items-center gap-3">
              <Suspense fallback={<span className="font-heading text-lg font-semibold">Аналитика программы</span>}>
                <SchoolLink
                  href="/"
                  className="rounded-sm font-heading text-lg font-semibold focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
                >
                  Аналитика программы
                </SchoolLink>
              </Suspense>
              <DemoBadge />
            </div>
            <Suspense fallback={<div className="h-8" />}>
              <SiteNav />
            </Suspense>
            <div className="sm:ml-auto">
              <Suspense fallback={<div className="h-9 w-40" />}>
                <SchoolFilter schools={schools} />
              </Suspense>
            </div>
          </div>
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-10 sm:px-8">{children}</main>
      </body>
    </html>
  );
}
