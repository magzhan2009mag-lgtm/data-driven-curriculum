import { cn } from "@/lib/utils";

/**
 * Значение по всем школам рядом с цифрой выбранной школы: «62,2 · по всем школам 53,4».
 * standalone — отдельной строкой под цифрой, без точки-разделителя.
 * Без фильтра API этих полей не отдаёт, и компонент ничего не рисует.
 */
export function AllSchools({
  value,
  format,
  standalone = false,
  className,
}: {
  value: number | null | undefined;
  format: (value: number) => string;
  standalone?: boolean;
  className?: string;
}) {
  if (value === undefined || value === null) return null;
  if (standalone) {
    return <span className={cn("block font-normal text-muted-foreground", className)}>по всем школам {format(value)}</span>;
  }
  return (
    <span className={cn("font-normal whitespace-nowrap text-muted-foreground", className)}>
      {" "}
      · по всем школам {format(value)}
    </span>
  );
}
