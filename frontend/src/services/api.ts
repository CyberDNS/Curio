import axios from "axios";
import type {
  Article,
  Category,
  Feed,
  UserSettings,
  FeedCreate,
  CategoryCreate,
  SettingsCreate,
  Newspaper,
} from "../types";

const API_BASE_URL = import.meta.env.VITE_API_URL || "/api";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: true, // Include cookies in requests
});

// Note: Auth token is now sent via HttpOnly cookie automatically
// No need to manually add Authorization header

// Articles
export const getArticles = async (params?: {
  skip?: number;
  limit?: number;
  category_id?: number;
  selected_only?: boolean;
  unread_only?: boolean;
  days_back?: number;
  balanced?: boolean;
}): Promise<Article[]> => {
  const { data } = await api.get("/articles/", { params });
  return data;
};

export const getArticle = async (id: number): Promise<Article> => {
  const { data } = await api.get(`/articles/${id}`);
  return data;
};

export const updateArticle = async (
  id: number,
  update: Partial<Article>
): Promise<Article> => {
  const { data } = await api.put(`/articles/${id}`, update);
  return data;
};

export const markAllRead = async (category_id?: number): Promise<void> => {
  await api.post("/articles/mark-all-read", null, { params: { category_id } });
};

export const getRelatedArticles = async (articleId: number): Promise<Article[]> => {
  const { data } = await api.get(`/articles/${articleId}/related`);
  return data;
};

// Categories
export const getCategories = async (): Promise<Category[]> => {
  const { data } = await api.get("/categories/");
  return data;
};

export const createCategory = async (
  category: CategoryCreate
): Promise<Category> => {
  const { data } = await api.post("/categories/", category);
  return data;
};

export const updateCategory = async (
  id: number,
  update: Partial<Category>
): Promise<Category> => {
  const { data } = await api.put(`/categories/${id}`, update);
  return data;
};

export const deleteCategory = async (id: number): Promise<void> => {
  await api.delete(`/categories/${id}`);
};

// Feeds
export const getFeeds = async (): Promise<Feed[]> => {
  const { data } = await api.get("/feeds/");
  return data;
};

export const createFeed = async (feed: FeedCreate): Promise<Feed> => {
  const { data } = await api.post("/feeds/", feed);
  return data;
};

export const updateFeed = async (
  id: number,
  update: Partial<Feed>
): Promise<Feed> => {
  const { data } = await api.put(`/feeds/${id}`, update);
  return data;
};

export const deleteFeed = async (id: number): Promise<void> => {
  await api.delete(`/feeds/${id}`);
};

// Settings
export const getSettings = async (): Promise<UserSettings[]> => {
  const { data } = await api.get("/settings/");
  return data;
};

export const getSetting = async (key: string): Promise<UserSettings> => {
  const { data } = await api.get(`/settings/${key}`);
  return data;
};

export const createOrUpdateSetting = async (
  setting: SettingsCreate
): Promise<UserSettings> => {
  const { data } = await api.post("/settings/", setting);
  return data;
};

// Actions
export const fetchFeeds = async (
  feedId?: number,
  daysBack?: number
): Promise<{ message: string; new_articles: number }> => {
  const { data } = await api.post("/actions/fetch-feeds", null, {
    params: { feed_id: feedId, days_back: daysBack },
  });
  return data;
};

export const processArticles = async (
  daysBack?: number
): Promise<{ message: string; processed_count: number }> => {
  const { data } = await api.post("/actions/process-articles", null, {
    params: { days_back: daysBack },
  });
  return data;
};

export const regenerateSummaries = async (
  category_id?: number
): Promise<{ message: string; count: number }> => {
  const { data } = await api.post("/actions/regenerate-summaries", null, {
    params: { category_id },
  });
  return data;
};

export const reprocessArticle = async (
  article_id: number
): Promise<{ message: string; processed: boolean }> => {
  const { data } = await api.post(`/actions/reprocess-article/${article_id}`);
  return data;
};

// Newspapers
export const getTodayNewspaper = async (): Promise<Newspaper> => {
  const { data } = await api.get("/newspapers/today");
  return data;
};

export const getNewspaperByDate = async (date: string): Promise<Newspaper> => {
  const { data} = await api.get(`/newspapers/date/${date}`);
  return data;
};

export const getNewspaperHistory = async (
  daysBack: number = 7
): Promise<Newspaper[]> => {
  const { data } = await api.get("/newspapers/history", {
    params: { days_back: daysBack },
  });
  return data;
};

export const getAvailableNewspaperDates = async (
  daysBack: number = 7
): Promise<string[]> => {
  const { data } = await api.get("/newspapers/dates", {
    params: { days_back: daysBack },
  });
  return data;
};

export const regenerateTodayNewspaper = async (): Promise<{
  message: string;
  date: string;
  today_count: number;
  category_count: number;
}> => {
  const { data } = await api.post("/newspapers/regenerate");
  return data;
};

export const getNewspaperArticles = async (
  newspaperId: number,
  section?: string
): Promise<Article[]> => {
  const { data } = await api.get(`/newspapers/${newspaperId}/articles`, {
    params: { section },
  });
  return data;
};

// Image URL handler - Returns local path for downloaded images, or proxy for external URLs
export const getProxiedImageUrl = (
  imageUrl: string | null | undefined
): string | null => {
  if (!imageUrl) return null;

  // If it's already a local media path, return it with the API base URL
  if (imageUrl.startsWith("/media/")) {
    return `${API_BASE_URL}${imageUrl}`;
  }

  // Legacy support for old static paths
  if (imageUrl.startsWith("/static/")) {
    return `${API_BASE_URL}${imageUrl}`;
  }

  // For external URLs, use the proxy (though this should rarely happen now)
  const encodedUrl = encodeURIComponent(imageUrl);
  return `${API_BASE_URL}/proxy/image?url=${encodedUrl}`;
};

export default api;
