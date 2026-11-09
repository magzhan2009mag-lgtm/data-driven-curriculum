import "@fontsource-variable/literata/index.css";
import "@fontsource-variable/onest/index.css";
import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { SiteNav } from "@/components/site-nav";
import "./globals.css";

export const metadata: Metadata = {
  title: "Аналитика программы",
  description: "Сложные темы, сравнение учебников и рекомендации по учебным часам",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ru" className="h-full antialiased">
      <body className="flex min-h-full flex-col">
        <header className="border-b">
          <div className="mx-auto flex w-full max-w-5xl flex-wrap items-center justify-between gap-x-8 gap-y-2 px-4 py-4 sm:px-8">
            <Link href="/" className="font-heading text-lg font-semibold">
              Аналитика программы
            </Link>
            <Suspense fallback={<div className="h-8" />}>
              <SiteNav />
            </Suspense>
          </div>
        </header>
        <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-10 sm:px-8">{children}</main>
      </body>
    </html>
  );
}
