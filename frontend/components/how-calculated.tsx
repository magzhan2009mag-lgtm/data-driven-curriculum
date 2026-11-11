import type { How } from "@/lib/api";
import { formatIndex, formatP } from "@/lib/format";
import { cn } from "@/lib/utils";

const count = new Intl.NumberFormat("ru-RU");

/** Раскрывающаяся строка «Как посчитано»: все значения приходят с бэкенда, здесь только форматирование. */
export function HowCalculated({ how, className, limit = 6 }: { how: How; className?: string; limit?: number }) {
  const shown = how.tests.slice(0, limit);
  const hidden = how.tests.length - shown.length;
  return (
    <details className={cn("group text-sm", className)}>
      <summary className="inline-flex cursor-pointer items-center gap-1 rounded-sm text-muted-foreground select-none hover:text-foreground">
        <span aria-hidden className="inline-block transition-transform duration-150 group-open:rotate-90 motion-reduce:transition-none">
          ›
        </span>
        Как посчитано
      </summary>
      <div className="mt-2 max-w-prose space-y-1.5 border-l-2 border-border pl-3 text-muted-foreground">
        <p>{how.method}</p>
        {(how.n_students !== null || how.n_results !== null) && (
          <p className="tabular-nums">
            {how.n_students !== null && <>Учеников: {count.format(how.n_students)}</>}
            {how.n_students !== null && how.n_results !== null && " · "}
            {how.n_results !== null && <>результатов тестов: {count.format(how.n_results)}</>}
          </p>
        )}
        {shown.length > 0 && (
          <ul className="space-y-0.5 tabular-nums">
            {shown.map((test) => (
              <li key={test.label}>
                <span className="text-foreground">{test.label}</span>
                {test.p_value !== null && <>: p {test.p_value < 0.001 ? formatP(test.p_value) : `= ${formatP(test.p_value)}`}</>}
                {test.effect_name !== null && test.effect_size !== null && (
                  <>
                    {test.p_value !== null ? ", " : ": "}
                    {test.effect_name} {formatIndex(test.effect_size)}
                    {test.effect_label && ` (${test.effect_label})`}
                  </>
                )}
                {test.p_value === null && test.effect_size === null && test.effect_label && `: ${test.effect_label}`}
              </li>
            ))}
            {hidden > 0 && <li>и ещё {hidden}</li>}
          </ul>
        )}
      </div>
    </details>
  );
}
