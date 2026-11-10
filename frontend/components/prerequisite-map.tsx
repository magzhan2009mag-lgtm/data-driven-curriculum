"use client";

import Link from "next/link";
import { useState } from "react";
import type { Level, PrerequisiteLink, Prerequisites } from "@/lib/api";
import { LEVEL_LABELS } from "@/lib/format";
import { cn } from "@/lib/utils";

const ROW = 36;
const WIDTH = 64;
// Точки тем стоят у правого края, дуги уходят влево. Вокруг точки корня — кольцо радиусом 8,5.
const DOT_X = WIDTH - 9;
const ARC_X = DOT_X - 11;
const MIN_STROKE = 2;
const MAX_STROKE = 6;

const DOT_CLASS: Record<Level, string> = {
  hard: "fill-score-1",
  medium: "fill-muted-foreground",
  easy: "fill-score-5",
};

function strokeWidth(link: PrerequisiteLink): number {
  // Порог связи 0,15 даёт тонкую дугу, связь 0,3 и сильнее — самую толстую.
  const width = MIN_STROKE + (link.std_coef - 0.15) * 27;
  return Math.min(MAX_STROKE, Math.max(MIN_STROKE, width));
}

function arcPath(from: number, to: number): string {
  const top = from * ROW + ROW / 2;
  const bottom = to * ROW + ROW / 2;
  const bulge = Math.min(ARC_X - 4, 18 + 0.42 * (bottom - top));
  return `M ${ARC_X} ${top} C ${ARC_X - bulge} ${top}, ${ARC_X - bulge} ${bottom}, ${ARC_X} ${bottom}`;
}

function linkKey(link: PrerequisiteLink): string {
  return `${link.from_topic_id}-${link.to_topic_id}`;
}

/** Дуговая диаграмма: темы в порядке программы, дуга ведёт от темы-основы к зависимой теме. */
export function PrerequisiteMap({ data }: { data: Prerequisites }) {
  const [active, setActive] = useState<string | null>(null);
  const position = new Map(data.topics.map((topic, index) => [topic.topic_id, index]));
  const roots = new Set(data.roots.map((root) => root.topic_id));
  const activeLink = data.links.find((link) => linkKey(link) === active);
  const highlighted = new Set(activeLink ? [activeLink.from_topic_id, activeLink.to_topic_id] : []);
  const height = data.topics.length * ROW;

  return (
    <div className="mt-6 grid grid-cols-1 gap-x-12 gap-y-8 lg:grid-cols-[minmax(0,30rem)_minmax(0,1fr)]">
      <figure>
        <figcaption className="sr-only">
          Темы в порядке программы и связи между ними. Те же связи описаны текстом рядом.
        </figcaption>
        <ul aria-label="Обозначения" className="mb-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
          {(["hard", "medium", "easy"] as const).map((level) => (
            <li key={level} className="flex items-center gap-1.5">
              <svg aria-hidden width="10" height="10" viewBox="0 0 10 10">
                <circle cx="5" cy="5" r="5" className={DOT_CLASS[level]} />
              </svg>
              {LEVEL_LABELS[level].toLowerCase()}
            </li>
          ))}
          <li className="flex items-center gap-1.5">
            <svg aria-hidden width="14" height="14" viewBox="0 0 14 14">
              <circle cx="7" cy="7" r="6" className="fill-none stroke-primary" strokeWidth="1.5" />
              <circle cx="7" cy="7" r="3" className="fill-muted-foreground" />
            </svg>
            корень проблемы
          </li>
          <li className="flex items-center gap-1.5">
            <svg aria-hidden width="18" height="10" viewBox="0 0 18 10">
              <path d="M 1 9 Q 9 -3 17 9" className="fill-none stroke-primary" strokeWidth="2" />
            </svg>
            толще дуга — сильнее связь
          </li>
        </ul>

        <div className="flex">
          <svg aria-hidden width={WIDTH} height={height} viewBox={`0 0 ${WIDTH} ${height}`} className="shrink-0 overflow-visible">
            <defs>
              <marker
                id="arc-arrow"
                viewBox="0 0 8 8"
                refX="7"
                refY="4"
                markerWidth="8"
                markerHeight="8"
                markerUnits="userSpaceOnUse"
                orient="auto"
              >
                <path d="M 0 0 L 8 4 L 0 8 z" className="fill-primary" />
              </marker>
            </defs>
            {data.links.map((link) => {
              const key = linkKey(link);
              const path = arcPath(position.get(link.from_topic_id) ?? 0, position.get(link.to_topic_id) ?? 0);
              return (
                <g
                  key={key}
                  onMouseEnter={() => setActive(key)}
                  onMouseLeave={() => setActive(null)}
                  className={cn(
                    "transition-opacity duration-150 ease-out motion-reduce:transition-none",
                    active && active !== key && "opacity-20",
                  )}
                >
                  <title>{link.text}</title>
                  <path d={path} className="fill-none stroke-primary" strokeWidth={strokeWidth(link)} strokeLinecap="round" markerEnd="url(#arc-arrow)" />
                  {/* Невидимая широкая полоса: по тонкой дуге трудно попасть курсором. */}
                  <path d={path} className="fill-none stroke-transparent" strokeWidth={14} />
                </g>
              );
            })}
            {data.topics.map((topic, index) => (
              <g
                key={topic.topic_id}
                className={cn(
                  "transition-opacity duration-150 ease-out motion-reduce:transition-none",
                  active && !highlighted.has(topic.topic_id) && "opacity-30",
                )}
              >
                {roots.has(topic.topic_id) && (
                  <circle cx={DOT_X} cy={index * ROW + ROW / 2} r={8.5} className="fill-none stroke-primary" strokeWidth={1.5} />
                )}
                <circle
                  cx={DOT_X}
                  cy={index * ROW + ROW / 2}
                  r={5}
                  className={cn(DOT_CLASS[topic.level], "stroke-background")}
                  strokeWidth={2}
                />
              </g>
            ))}
          </svg>

          <ol className="min-w-0 flex-1">
            {data.topics.map((topic, index) => (
              <li key={topic.topic_id} style={{ height: ROW }} className="flex items-center gap-3 pl-2">
                <span className="w-5 shrink-0 text-right text-xs text-muted-foreground tabular-nums">{index + 1}</span>
                <Link
                  href={`/topics/${topic.topic_id}`}
                  className={cn(
                    "min-w-0 truncate text-sm underline-offset-4 transition-colors duration-150 hover:underline sm:text-base",
                    roots.has(topic.topic_id) && "font-semibold",
                    active && !highlighted.has(topic.topic_id) && "text-muted-foreground",
                  )}
                >
                  {topic.topic}
                  {roots.has(topic.topic_id) && <span className="sr-only"> (корень проблемы)</span>}
                </Link>
                <span className="ml-auto shrink-0 text-xs text-muted-foreground">{LEVEL_LABELS[topic.level].toLowerCase()}</span>
              </li>
            ))}
          </ol>
        </div>
      </figure>

      <ul className="divide-y self-start border-y">
        {data.links.map((link) => {
          const key = linkKey(link);
          return (
            <li
              key={key}
              onMouseEnter={() => setActive(key)}
              onMouseLeave={() => setActive(null)}
              onFocus={() => setActive(key)}
              onBlur={() => setActive(null)}
              className={cn(
                "py-3 transition-colors duration-150 ease-out motion-reduce:transition-none sm:px-2",
                active === key && "bg-muted",
              )}
            >
              <p className="font-medium">
                <Link href={`/topics/${link.from_topic_id}`} className="underline-offset-4 hover:underline">
                  {link.from_topic}
                </Link>
                <span aria-label="влияет на" className="px-2 text-muted-foreground">
                  →
                </span>
                <Link href={`/topics/${link.to_topic_id}`} className="underline-offset-4 hover:underline">
                  {link.to_topic}
                </Link>
              </p>
              <p className="mt-0.5 max-w-prose text-sm text-muted-foreground">{link.text}</p>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
