"use client";

import { Info } from "lucide-react";
import { Popover, PopoverContent, PopoverDescription, PopoverTitle, PopoverTrigger } from "@/components/ui/popover";
import { GLOSSARY } from "@/lib/glossary";

/** Метка в шапке: честно говорим, что данные синтетические. Подсказка — по наведению, клику и с клавиатуры. */
export function DemoBadge() {
  const entry = GLOSSARY.demo_data;
  return (
    <Popover>
      <PopoverTrigger
        openOnHover
        delay={150}
        closeDelay={100}
        className="inline-flex h-6 cursor-help items-center gap-1 rounded-sm border border-dashed border-muted-foreground/50 px-1.5 text-xs text-muted-foreground transition-colors duration-150 hover:border-primary hover:text-primary focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none data-popup-open:border-primary data-popup-open:text-primary"
      >
        {entry.title}
        <Info className="size-3" aria-hidden />
      </PopoverTrigger>
      <PopoverContent side="bottom">
        <PopoverTitle className="font-medium">{entry.title}</PopoverTitle>
        <PopoverDescription className="mt-1 text-muted-foreground">{entry.text}</PopoverDescription>
      </PopoverContent>
    </Popover>
  );
}
