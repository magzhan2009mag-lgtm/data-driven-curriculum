export const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";

export type Level = "hard" | "medium" | "easy";

export type School = { school_id: number; school: string; n_classes: number; n_students: number };

/** Поля, которые API добавляет при выбранной школе: те же показатели по всем школам для сравнения. */
type ScopeNote = { scope_note?: string };

export type TopicDifficulty = {
  topic_id: number;
  topic: string;
  hours_planned: number;
  avg_score: number;
  fail_rate: number;
  difficulty_index: number;
  level: Level;
  by_school: { school_id: number; school: string; avg_score: number }[];
  score_distribution: { range: string; count: number; failing: boolean }[];
  avg_score_all?: number;
  fail_rate_all?: number;
  difficulty_index_all?: number;
  by_class?: { class_id: number; class: string; textbook: string; avg_score: number }[];
};

export type Comparison = {
  topic_id: number | null;
  topic: string | null;
  textbooks: {
    textbook_id: number;
    name: string;
    n_students: number;
    avg_score: number;
    adjusted_score: number;
    mean_z: number;
    enough_data: boolean;
    adjusted_score_all?: number | null;
  }[];
  comparisons: {
    a: string;
    b: string;
    p_value: number | null;
    p_adjusted: number | null;
    cohens_d: number | null;
    effect: string;
    significant: boolean;
  }[];
  conclusion: string;
  confounding_note: string | null;
  limitation: string;
  school_note: string | null;
};

/** Строка плана учебника. В одной школе у учебника с малым числом учеников чисел нет (null). */
export type TextbookHours = {
  textbook: string;
  level: Level | null;
  avg_score: number | null;
  fail_rate: number | null;
  difficulty_index: number | null;
  hours_recommended: number | null;
  delta: number | null;
  reason: string;
};

export type Recommendations = {
  total_hours: number;
  hours_moved: number;
  items: {
    topic_id: number;
    topic: string;
    level: Level;
    hours_current: number;
    hours_recommended: number;
    delta: number;
    reason: string;
    by_textbook: TextbookHours[];
    delta_all?: number;
    hours_recommended_all?: number;
  }[];
  textbook_plans: {
    textbook: string;
    hours_moved: number;
    added: { topic_id: number; topic: string; delta: number }[];
    text: string;
    enough_data: boolean;
  }[];
  hours_moved_all?: number;
};

export type Explanations = {
  source: "llm" | "template";
  items: { topic_id: number; explanation: string }[];
};

export type Trend = {
  topic_id: number;
  topic: string;
  slope_per_year: number;
  direction: "улучшается" | "ухудшается" | "без заметных изменений";
  text: string;
  by_year: { year: number; avg_score: number }[];
};

export type ItemQuality = {
  topic_id: number;
  topic: string;
  items: {
    item_id: number;
    test_number: number;
    item_number: number;
    p_correct: number;
    issue: string | null;
    is_bad: boolean;
  }[];
  n_bad: number;
  conclusion: string;
};

export type Outliers = ScopeNote & {
  n_classes: number;
  outliers: {
    class_id: number;
    class: string;
    school_id: number;
    school: string;
    textbook: string;
    topic_id: number;
    topic: string;
    avg_score: number;
    expected_score: number;
    difference: number;
    text: string;
  }[];
  conclusion: string;
};

export type PrerequisiteLink = {
  from_topic_id: number;
  from_topic: string;
  to_topic_id: number;
  to_topic: string;
  coef: number;
  std_coef: number;
  p_value: number;
  p_adjusted: number;
  points: number;
  text: string;
};

export type Prerequisites = ScopeNote & {
  topics: { topic_id: number; topic: string; level: Level }[];
  links: PrerequisiteLink[];
  roots: {
    topic_id: number;
    topic: string;
    level: Level;
    dependents: { topic_id: number; topic: string; level: Level }[];
    text: string;
  }[];
  n_students: number;
  conclusion: string;
  note: string;
};

export type Regression = {
  topic_id: number | null;
  reference: string | null;
  conclusion: string;
};

export type TextbookGap = {
  topic_id: number;
  topic: string;
  stronger: string;
  weaker: string;
  points: number;
  p_adjusted: number;
  cohens_d: number;
  effect: string;
};

/** «Что решить по учебникам»: строка-вывод и совет для каждого учебника. */
export type Decisions = {
  all_schools: boolean;
  note: string | null;
  n_topics: number;
  textbooks: {
    textbook: string;
    verdict: "replace" | "strengthen" | "strong" | "equal";
    weaker: TextbookGap[];
    stronger: TextbookGap[];
    equivalent: { textbook: string; except_topics: string[] }[];
    alternatives: string[];
    text: string;
    advice: string | null;
    short_advice: string | null;
  }[];
};

/** Карточка «Главное за минуту». unit: score — балл из 100, hours — часы. */
export type SummaryCard = {
  kind: "hardest_topic" | "weakest_textbook" | "hours" | "outlier" | "root";
  label: string;
  headline: string | null;
  value: number | null;
  unit: "score" | "hours" | null;
  value_all: number | null;
  text: string;
  path: string;
  all_schools: boolean;
  advice: string | null;
};

async function request<T>(path: string): Promise<T | null> {
  const response = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`API ${path}: ${response.status}`);
  return response.json();
}

/** Собирает адрес запроса: необязательные параметры без значения в адрес не попадают. */
function apiPath(path: string, params: Record<string, number | undefined>): string {
  const search = new URLSearchParams();
  for (const [name, value] of Object.entries(params)) {
    if (value !== undefined) search.set(name, String(value));
  }
  const query = search.toString();
  return query ? `${path}?${query}` : path;
}

export async function getSchools(): Promise<School[]> {
  return (await request<School[]>("/schools")) ?? [];
}

export async function getSummary(school?: number): Promise<SummaryCard[]> {
  return (await request<{ cards: SummaryCard[] }>(apiPath("/summary", { school_id: school })))?.cards ?? [];
}

export async function getTopics(school?: number): Promise<TopicDifficulty[]> {
  return (await request<TopicDifficulty[]>(apiPath("/topics/difficulty", { school_id: school }))) ?? [];
}

export function getDecisions(school?: number): Promise<Decisions | null> {
  return request<Decisions>(apiPath("/textbooks/decisions", { school_id: school }));
}

export function getComparison(topicId?: number, school?: number): Promise<Comparison | null> {
  return request<Comparison>(apiPath("/textbooks/compare", { topic_id: topicId, school_id: school }));
}

export async function getRecommendations(school?: number): Promise<Recommendations> {
  const path = apiPath("/recommendations", { school_id: school });
  const body = await request<Recommendations>(path);
  if (!body) throw new Error(`API ${path}: 404`);
  return body;
}

export async function getTrends(school?: number): Promise<Trend[]> {
  return (await request<Trend[]>(apiPath("/topics/trends", { school_id: school }))) ?? [];
}

export function getItemQuality(topicId: number, school?: number): Promise<ItemQuality | null> {
  return request<ItemQuality>(apiPath("/items/quality", { topic_id: topicId, school_id: school }));
}

export function getOutliers(school?: number): Promise<Outliers | null> {
  return request<Outliers>(apiPath("/classes/outliers", { school_id: school }));
}

export function getPrerequisites(school?: number): Promise<Prerequisites | null> {
  return request<Prerequisites>(apiPath("/topics/prerequisites", { school_id: school }));
}

export function getRegression(topicId?: number, school?: number): Promise<Regression | null> {
  return request<Regression>(apiPath("/textbooks/regression", { topic_id: topicId, school_id: school }));
}

/** Пояснения от Claude. Без ключа или при ошибке бэкенд отдаёт шаблоны; недоступный API не ломает страницу. */
export async function getExplanations(school?: number): Promise<Explanations | null> {
  try {
    return await request<Explanations>(apiPath("/recommendations/explanation", { school_id: school }));
  } catch {
    return null;
  }
}
