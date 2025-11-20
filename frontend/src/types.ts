export interface Feed {
  id: number;
  url: string;
  title: string | null;
  source_title: string | null;
  description: string | null;
  is_active: boolean;
  last_fetched: string | null;
  fetch_interval: number;
  created_at: string;
  updated_at: string;
}

export interface Category {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  display_order: number;
  created_at: string;
  updated_at: string;
}

export interface Article {
  id: number;
  feed_id: number;
  category_id: number | null;
  // Original RSS data
  title: string;
  link: string;
  description: string | null;
  content: string | null;
  author: string | null;
  published_date: string | null;
  image_url: string | null;
  // LLM-enhanced data
  llm_title: string | null;
  llm_subtitle: string | null;
  llm_summary: string | null;
  llm_category_suggestion: string | null;
  image_urls: string[] | null;
  // Analysis
  summary: string | null;
  relevance_score: number; // >= 0.6 means "recommended"
  // User feedback and score adjustment
  user_vote: number; // 0 = neutral, -1 = downvote
  vote_updated_at: string | null;
  adjusted_relevance_score: number | null; // Final score after downvote adjustment
  score_adjustment_reason: string | null; // Brief explanation for UI
  // Feed source information
  feed_source_title: string | null;
  // Duplicate detection
  is_duplicate: boolean;
  duplicate_of_id: number | null;
  title_embedding: string | null; // JSON string of embedding vector
  // Metadata
  is_read: boolean; // false = "NEW" article, true = read
  is_archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface ScoreAdjustmentExplanation {
  explanation: string;
  has_adjustment: boolean;
  original_score?: number;
  adjusted_score?: number;
  brief_reason?: string;
}

export interface UserSettings {
  id: number;
  key: string;
  value: string;
  created_at: string;
  updated_at: string;
}

export interface FeedCreate {
  url: string;
  title?: string;
  source_title?: string;
  description?: string;
  is_active?: boolean;
  fetch_interval?: number;
}

export interface CategoryCreate {
  name: string;
  slug: string;
  description?: string;
  display_order?: number;
}

export interface SettingsCreate {
  key: string;
  value: string;
}

export interface NewspaperStructure {
  today: number[];
  categories: Record<string, number[]>;
}

export interface Newspaper {
  id: number;
  user_id: number;
  date: string;
  structure: NewspaperStructure;
  created_at: string;
  updated_at: string;
}
