import { http, HttpResponse } from "msw";
import {
  mockArticles,
  mockCategories,
  mockFeeds,
  mockNewspaper,
} from "./mockData";

const API_BASE_URL = "/api";

export const handlers = [
  // Articles
  http.get(`${API_BASE_URL}/articles/`, () => {
    return HttpResponse.json(mockArticles);
  }),

  http.get(`${API_BASE_URL}/articles/:id`, ({ params }) => {
    const article = mockArticles.find((a) => a.id === Number(params.id));
    if (!article) {
      return new HttpResponse(null, { status: 404 });
    }
    return HttpResponse.json(article);
  }),

  http.put(`${API_BASE_URL}/articles/:id`, async ({ request, params }) => {
    const updates = (await request.json()) as Record<string, any>;
    const article = mockArticles.find((a) => a.id === Number(params.id));
    if (!article) {
      return new HttpResponse(null, { status: 404 });
    }
    return HttpResponse.json({ ...article, ...updates });
  }),

  http.post(`${API_BASE_URL}/articles/mark-all-read`, () => {
    return HttpResponse.json({ message: "Marked 5 articles as read" });
  }),

  http.post(`${API_BASE_URL}/articles/:id/downvote`, ({ params }) => {
    return HttpResponse.json({ message: "Article downvoted", user_vote: -1 });
  }),

  // Categories
  http.get(`${API_BASE_URL}/categories/`, () => {
    return HttpResponse.json(mockCategories);
  }),

  http.post(`${API_BASE_URL}/categories/`, async ({ request }) => {
    const data = (await request.json()) as Record<string, any>;
    return HttpResponse.json({
      id: 4,
      ...data,
      slug: "new-category",
      display_order: 4,
    });
  }),

  http.put(`${API_BASE_URL}/categories/:id`, async ({ request, params }) => {
    const updates = (await request.json()) as Record<string, any>;
    const category = mockCategories.find((c) => c.id === Number(params.id));
    if (!category) {
      return new HttpResponse(null, { status: 404 });
    }
    return HttpResponse.json({ ...category, ...updates });
  }),

  http.delete(`${API_BASE_URL}/categories/:id`, () => {
    return HttpResponse.json({ message: "Category deleted" });
  }),

  // Feeds
  http.get(`${API_BASE_URL}/feeds/`, () => {
    return HttpResponse.json(mockFeeds);
  }),

  http.post(`${API_BASE_URL}/feeds/`, async ({ request }) => {
    const data = (await request.json()) as Record<string, any>;
    return HttpResponse.json({ id: 3, ...data, is_active: true });
  }),

  http.put(`${API_BASE_URL}/feeds/:id`, async ({ request, params }) => {
    const updates = (await request.json()) as Record<string, any>;
    const feed = mockFeeds.find((f) => f.id === Number(params.id));
    if (!feed) {
      return new HttpResponse(null, { status: 404 });
    }
    return HttpResponse.json({ ...feed, ...updates });
  }),

  http.delete(`${API_BASE_URL}/feeds/:id`, () => {
    return HttpResponse.json({ message: "Feed deleted" });
  }),

  // Actions
  http.post(`${API_BASE_URL}/actions/fetch-feeds`, () => {
    return HttpResponse.json({ message: "Fetched feeds", new_articles: 10 });
  }),

  http.post(`${API_BASE_URL}/actions/process-articles`, () => {
    return HttpResponse.json({
      message: "Processed articles",
      processed_count: 10,
    });
  }),

  http.post(`${API_BASE_URL}/actions/reprocess-article/:id`, () => {
    return HttpResponse.json({
      message: "Article reprocessed",
      processed: true,
    });
  }),

  http.post(`${API_BASE_URL}/actions/run-full-update`, () => {
    return HttpResponse.json({
      message: "Full update complete",
      new_articles: 15,
      processed_articles: 10,
      today_count: 20,
      category_count: 30,
    });
  }),

  // Newspapers
  http.get(`${API_BASE_URL}/newspapers/today`, () => {
    return HttpResponse.json(mockNewspaper);
  }),

  http.get(`${API_BASE_URL}/newspapers/date/:date`, () => {
    return HttpResponse.json(mockNewspaper);
  }),

  http.get(`${API_BASE_URL}/newspapers/dates`, () => {
    return HttpResponse.json(["2024-01-01", "2024-01-02", "2024-01-03"]);
  }),

  http.post(`${API_BASE_URL}/newspapers/regenerate`, () => {
    return HttpResponse.json({
      message: "Newspaper regenerated",
      date: "2024-01-01",
      today_count: 20,
      category_count: 30,
    });
  }),

  // Settings
  http.get(`${API_BASE_URL}/settings/:key`, ({ params }) => {
    return HttpResponse.json({ key: params.key, value: "test value" });
  }),

  http.post(`${API_BASE_URL}/settings/`, async ({ request }) => {
    const data = (await request.json()) as Record<string, any>;
    return HttpResponse.json(data);
  }),

  // Auth
  http.get(`${API_BASE_URL}/auth/user`, () => {
    return HttpResponse.json({
      id: 1,
      email: "test@example.com",
      is_active: true,
    });
  }),
];
