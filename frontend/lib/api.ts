const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";

export type Level = "hard" | "medium" | "easy";

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
};

export type TextbookHours = {
  textbook: string;
  level: Level;
  avg_score: number;
  fail_rate: number;
  difficulty_index: number;
  hours_recommended: number;
  delta: number;
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
  }[];
  textbook_plans: {
    textbook: string;
    hours_moved: number;
    added: { topic_id: number; topic: string; delta: number }[];
    text: string;
  }[];
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

export type Outliers = {
  n_classes: number;
  outliers: {
    class_id: number;
    class: string;
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

export type Regression = {
  topic_id: number | null;
  reference: string | null;
  conclusion: string;
};

async function request<T>(path: string): Promise<T | null> {
  const response = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`API ${path}: ${response.status}`);
  return response.json();
}

export async function getTopics(): Promise<TopicDifficulty[]> {
  return (await request<TopicDifficulty[]>("/topics/difficulty")) ?? [];
}

export function getComparison(topicId?: number): Promise<Comparison | null> {
  return request<Comparison>(topicId === undefined ? "/textbooks/compare" : `/textbooks/compare?topic_id=${topicId}`);
}

export async function getRecommendations(): Promise<Recommendations> {
  const body = await request<Recommendations>("/recommendations");
  if (!body) throw new Error("API /recommendations: 404");
  return body;
}

export async function getTrends(): Promise<Trend[]> {
  return (await request<Trend[]>("/topics/trends")) ?? [];
}

export function getItemQuality(topicId: number): Promise<ItemQuality | null> {
  return request<ItemQuality>(`/items/quality?topic_id=${topicId}`);
}

export function getOutliers(): Promise<Outliers | null> {
  return request<Outliers>("/classes/outliers");
}

export function getRegression(topicId?: number): Promise<Regression | null> {
  return request<Regression>(topicId === undefined ? "/textbooks/regression" : `/textbooks/regression?topic_id=${topicId}`);
}

/** Пояснения от Claude. Без ключа или при ошибке бэкенд отдаёт шаблоны; недоступный API не ломает страницу. */
export async function getExplanations(): Promise<Explanations | null> {
  try {
    return await request<Explanations>("/recommendations/explanation");
  } catch {
    return null;
  }
}
