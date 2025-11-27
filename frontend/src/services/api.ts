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
  SavedArticle,
  SavedArticleWithArticle,
  Tag,
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

// Track if we're currently refreshing to prevent multiple refresh attempts
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: unknown) => void;
  reject: (reason?: unknown) => void;
}> = [];

const processQueue = (error: unknown = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve();
    }
  });
  failedQueue = [];
};

// Response interceptor to handle token refresh on 401 errors
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // If error is 401 and we haven't already tried to refresh
    if (error.response?.status === 401 && !originalRequest._retry) {
      // Don't try to refresh if we're already on auth endpoints
      if (
        originalRequest.url?.includes("/auth/refresh") ||
        originalRequest.url?.includes("/auth/login") ||
        originalRequest.url?.includes("/auth/me")
      ) {
        return Promise.reject(error);
      }

      if (isRefreshing) {
        // If already refreshing, queue this request
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then(() => api(originalRequest))
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        // Attempt to refresh the token
        await axios.post(
          `${API_BASE_URL}/auth/refresh`,
          {},
          { withCredentials: true }
        );

        // Token refreshed successfully, process queued requests
        processQueue();

        // Retry the original request
        return api(originalRequest);
      } catch (refreshError) {
        // Refresh failed, process queue with error
        processQueue(refreshError);

        // Dispatch event to trigger logout/redirect to login
        window.dispatchEvent(new Event("authExpired"));

        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

// Articles
export const getArticles = async (params?: {
  skip?: number;
  limit?: number;
  category_id?: number;
  feed_id?: number;
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

export const getRelatedArticles = async (
  articleId: number
): Promise<Article[]> => {
  const { data } = await api.get(`/articles/${articleId}/related`);
  return data;
};

export const downvoteArticle = async (
  articleId: number
): Promise<{ message: string; user_vote: number }> => {
  const { data } = await api.post(`/articles/${articleId}/downvote`);
  return data;
};

export const explainScoreAdjustment = async (
  articleId: number
): Promise<{
  explanation: string;
  has_adjustment: boolean;
  original_score?: number;
  adjusted_score?: number;
  brief_reason?: string;
}> => {
  const { data } = await api.get(`/articles/${articleId}/explain-adjustment`);
  return data;
};

export const getUnreadCounts = async (): Promise<Record<string, number>> => {
  const { data } = await api.get("/articles/unread-counts");
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

export const reorderCategories = async (
  categoryIds: number[]
): Promise<Category[]> => {
  const { data } = await api.post("/categories/reorder", categoryIds);
  return data;
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

export const runFullUpdate = async (): Promise<{
  message: string;
  status?: string;
  new_articles?: number;
  processed_articles?: number;
  today_count?: number;
  category_count?: number;
}> => {
  // Extended timeout for long-running operation (5 minutes)
  // Note: This operation now runs in background and returns immediately
  const { data } = await api.post("/actions/run-full-update", null, {
    timeout: 300000, // 5 minutes fallback
  });
  return data;
};

// Newspapers
export const getTodayNewspaper = async (): Promise<Newspaper> => {
  const { data } = await api.get("/newspapers/today");
  return data;
};

export const getNewspaperByDate = async (date: string): Promise<Newspaper> => {
  const { data } = await api.get(`/newspapers/date/${date}`);
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

// Saved Articles
export const saveArticle = async (articleData: {
  article_id: number;
  tag_names?: string[];
}): Promise<SavedArticle> => {
  const { data } = await api.post("/saved-articles/", articleData);
  return data;
};

export const getSavedArticles = async (params?: {
  skip?: number;
  limit?: number;
  tags?: string[];
}): Promise<SavedArticleWithArticle[]> => {
  const { data } = await api.get("/saved-articles/", {
    params,
    paramsSerializer: {
      indexes: null, // Use tags=value1&tags=value2 format instead of tags[0]=value1
    },
  });
  return data;
};

export const getSavedArticle = async (
  id: number
): Promise<SavedArticleWithArticle> => {
  const { data } = await api.get(`/saved-articles/${id}`);
  return data;
};

export const updateSavedArticleTags = async (
  id: number,
  tagData: { tag_names: string[] }
): Promise<SavedArticle> => {
  const { data } = await api.put(`/saved-articles/${id}/tags`, tagData);
  return data;
};

export const unsaveArticle = async (id: number): Promise<void> => {
  await api.delete(`/saved-articles/${id}`);
};

export const checkArticleSaved = async (
  articleId: number
): Promise<{ is_saved: boolean; saved_article_id: number | null }> => {
  const { data } = await api.get(`/saved-articles/check/${articleId}`);
  return data;
};

// Tags
export const getTags = async (params?: { search?: string }): Promise<Tag[]> => {
  const { data } = await api.get("/tags/", { params });
  return data;
};

export default api;
