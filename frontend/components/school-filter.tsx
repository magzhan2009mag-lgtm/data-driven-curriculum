"use client";

import { X } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { School } from "@/lib/api";
import { parseSchool, schoolHref } from "@/lib/school";

const ALL = "all";

/** Выбор школы в шапке. Выбор хранится в адресе (?school=5) и переживает любые переходы. */
export function SchoolFilter({ schools }: { schools: School[] }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const school = parseSchool(searchParams.get("school") ?? undefined);
  const selected = schools.find((item) => item.school_id === school);
  if (schools.length === 0) return null;

  const current = `${pathname}?${searchParams.toString()}`;
  const items = [
    { value: ALL, label: "Все школы" },
    ...schools.map((item) => ({ value: String(item.school_id), label: item.school })),
  ];

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Select
        items={items}
        value={selected ? String(selected.school_id) : ALL}
        onValueChange={(value) => {
          if (typeof value !== "string") return;
          router.push(schoolHref(current, value === ALL ? undefined : Number(value)), { scroll: false });
        }}
      >
        <SelectTrigger aria-label="Школа" className="w-40">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ALL}>Все школы</SelectItem>
          {schools.map((item) => (
            <SelectItem key={item.school_id} value={String(item.school_id)}>
              <span className="flex items-baseline justify-between gap-4">
                {item.school}
                <span className="text-xs text-muted-foreground tabular-nums">
                  {item.n_classes} кл., {item.n_students} уч.
                </span>
              </span>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {selected && (
        <span className="inline-flex h-7 items-center gap-1 rounded-sm bg-accent pr-0.5 pl-2.5 text-sm text-accent-foreground">
          Только {selected.school}
          <Link
            href={schoolHref(current, undefined)}
            scroll={false}
            aria-label="Сбросить фильтр и показать все школы"
            title="Показать все школы"
            className="inline-flex size-6 items-center justify-center rounded-sm transition-colors duration-150 hover:bg-background/70 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
          >
            <X className="size-3.5" aria-hidden />
          </Link>
        </span>
      )}
    </div>
  );
}
