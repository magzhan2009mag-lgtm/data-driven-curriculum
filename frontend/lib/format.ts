import type { Level } from "@/lib/api";

const LOCALE = "ru-RU";
const oneDecimal = new Intl.NumberFormat(LOCALE, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const twoDecimals = new Intl.NumberFormat(LOCALE, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const threeDecimals = new Intl.NumberFormat(LOCALE, { minimumFractionDigits: 3, maximumFractionDigits: 3 });
const percent = new Intl.NumberFormat(LOCALE, { style: "percent", maximumFractionDigits: 0 });
const signedTwoDecimals = new Intl.NumberFormat(LOCALE, {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
  signDisplay: "exceptZero",
});
const plural = new Intl.PluralRules(LOCALE);

export const formatScore = (value: number) => oneDecimal.format(value);
export const formatIndex = (value: number) => twoDecimals.format(value);
export const formatPercent = (value: number) => percent.format(value);
export const formatSigned = (value: number) => signedTwoDecimals.format(value);
export const formatP = (value: number) => (value < 0.001 ? "< 0,001" : threeDecimals.format(value));

const HOUR_FORMS: Partial<Record<Intl.LDMLPluralRule, string>> = { one: "час", few: "часа", many: "часов" };

export function hoursWord(count: number): string {
  return HOUR_FORMS[plural.select(count)] ?? "часа";
}

export function formatHours(count: number): string {
  return `${count} ${hoursWord(count)}`;
}

export const LEVEL_LABELS: Record<Level, string> = {
  hard: "Сложная",
  medium: "Средняя",
  easy: "Лёгкая",
};

export const SCORE_BANDS = [
  { label: "меньше 50", from: -Infinity, className: "bg-score-1 text-white" },
  { label: "50–59", from: 50, className: "bg-score-2 text-foreground" },
  { label: "60–69", from: 60, className: "bg-score-3 text-foreground" },
  { label: "70–79", from: 70, className: "bg-score-4 text-foreground" },
  { label: "80 и выше", from: 80, className: "bg-score-5 text-white" },
];

export function scoreBandClass(score: number): string {
  return SCORE_BANDS.findLast((band) => score >= band.from)!.className;
}
