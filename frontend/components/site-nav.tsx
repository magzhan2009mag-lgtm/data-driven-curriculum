"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const LINKS = [
  { href: "/", label: "Сложные темы" },
  { href: "/textbooks", label: "Учебники" },
  { href: "/recommendations", label: "Часы" },
];

export function SiteNav() {
  const pathname = usePathname();
  return (
    <nav aria-label="Разделы" className="-mx-2 flex flex-wrap text-sm">
      {LINKS.map(({ href, label }) => {
        const active = href === "/" ? pathname === "/" || pathname.startsWith("/topics") : pathname.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            aria-current={active ? "page" : undefined}
            className={cn(
              "rounded-sm px-2 py-1.5 underline-offset-4 transition-colors duration-150 hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
              active ? "font-medium text-primary underline" : "text-muted-foreground hover:text-foreground",
            )}
          >
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
