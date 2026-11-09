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
  limitation: string;
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
  }[];
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
