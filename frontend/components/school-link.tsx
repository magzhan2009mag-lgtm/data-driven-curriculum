"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import type { ComponentProps } from "react";
import { parseSchool, schoolHref } from "@/lib/school";

/** Ссылка для общих частей страницы (шапка, 404): берёт выбранную школу из адреса. */
export function SchoolLink({ href, ...props }: Omit<ComponentProps<typeof Link>, "href"> & { href: string }) {
  const school = parseSchool(useSearchParams().get("school") ?? undefined);
  return <Link href={schoolHref(href, school)} {...props} />;
}
