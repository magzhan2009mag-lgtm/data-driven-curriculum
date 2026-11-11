"use client";

import type { ReactNode } from "react";
import { Popover, PopoverContent, PopoverDescription, PopoverTitle, PopoverTrigger } from "@/components/ui/popover";
import { GLOSSARY, type GlossaryKey } from "@/lib/glossary";
import { cn } from "@/lib/utils";

/**
 * Термин со значком «?». Объяснение открывается по наведению и по клику, с клавиатуры — Enter или пробел,
 * закрывается Esc. children — сам термин в тексте; без children рисуется только значок.
 */
export function Term({ term, children, className }: { term: GlossaryKey; children?: ReactNode; className?: string }) {
  const entry = GLOSSARY[term];
  return (
    <span className={cn("inline-flex items-baseline gap-1", className)}>
      {children}
      <Popover>
        <PopoverTrigger
          openOnHover
          delay={150}
          closeDelay={100}
          aria-label={`Что значит «${entry.title}»`}
          className="relative inline-flex size-4 shrink-0 cursor-help items-center justify-center self-center rounded-full border border-muted-foreground/60 text-[0.65rem] leading-none font-semibold text-muted-foreground transition-colors duration-150 after:absolute after:-inset-1.5 hover:border-primary hover:text-primary focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:ring-offset-background focus-visible:outline-none data-popup-open:border-primary data-popup-open:text-primary"
        >
          ?
        </PopoverTrigger>
        <PopoverContent>
          <PopoverTitle className="font-medium">{entry.title}</PopoverTitle>
          <PopoverDescription className="mt-1 text-muted-foreground">{entry.text}</PopoverDescription>
        </PopoverContent>
      </Popover>
    </span>
  );
}
