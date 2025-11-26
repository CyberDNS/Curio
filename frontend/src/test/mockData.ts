/**
 * Mock data for testing
 */
import type { Article, Category, Feed, Newspaper } from "../types";

export const mockCategory: Category = {
  id: 1,
  name: "Technology",
  slug: "technology",
  description: "Tech news and updates",
  display_order: 1,
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
};

export const mockFeed: Feed = {
  id: 1,
  url: "https://example.com/feed.xml",
  title: "Example Feed",
  description: "A test feed",
  source_title: "Example News",
  is_active: true,
  fetch_interval: 60,
  last_fetched: "2024-01-01T00:00:00Z",
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
};

export const mockArticle: Article = {
  id: 1,
  feed_id: 1,
  category_id: 1,
  title: "Test Article",
  link: "https://example.com/article",
  description: "Test description",
  content: "Test content",
  author: "Test Author",
  published_date: "2024-01-01T12:00:00Z",
  image_url: null,
  llm_title: "Enhanced Test Article",
  llm_subtitle: "An AI-enhanced subtitle",
  llm_summary: "AI-generated summary",
  llm_category_suggestion: null,
  summary: "Test summary",
  relevance_score: 0.75,
  adjusted_relevance_score: null,
  user_vote: 0,
  vote_updated_at: null,
  score_adjustment_reason: null,
  feed_source_title: "Example News",
  is_duplicate: false,
  duplicate_of_id: null,
  title_embedding: null,
  is_read: false,
  image_urls: ["https://example.com/image.jpg"],
  newspaper_appearances: {},
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
};

export const mockArticles: Article[] = [
  mockArticle,
  {
    ...mockArticle,
    id: 2,
    title: "Second Test Article",
    link: "https://example.com/article2",
    relevance_score: 0.85,
  },
  {
    ...mockArticle,
    id: 3,
    title: "Third Test Article",
    link: "https://example.com/article3",
    relevance_score: 0.65,
    is_read: true,
  },
];

export const mockNewspaper: Newspaper = {
  id: 1,
  user_id: 1,
  date: "2024-01-01",
  structure: {
    today: [1],
    categories: {
      technology: [1, 2],
    },
  },
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
};

export const mockCategories: Category[] = [
  mockCategory,
  {
    ...mockCategory,
    id: 2,
    name: "Science",
    slug: "science",
    description: "Scientific discoveries",
    display_order: 2,
  },
  {
    ...mockCategory,
    id: 3,
    name: "Politics",
    slug: "politics",
    description: "Political news",
    display_order: 3,
  },
];

export const mockFeeds: Feed[] = [
  mockFeed,
  {
    ...mockFeed,
    id: 2,
    url: "https://example2.com/feed.xml",
    title: "Example Feed 2",
    source_title: "Example News 2",
    fetch_interval: 60,
  },
];
