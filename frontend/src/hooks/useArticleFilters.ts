import { useMemo } from "react";
import type { Article } from "../types";

export type FilterType =
  | "all"
  | "processed"
  | "unprocessed"
  | "selected"
  | "unselected";

interface UseArticleFiltersOptions {
  articles: Article[];
  statusFilter: FilterType;
}

/**
 * Shared hook for filtering articles by status
 * Consolidates duplicate filter logic from AllArticlesPage and ArticlesManagement
 */
export function useArticleFilters({
  articles,
  statusFilter,
}: UseArticleFiltersOptions) {
  const filteredArticles = useMemo(() => {
    return articles.filter((article) => {
      // Apply status filter
      switch (statusFilter) {
        case "processed":
          return article.summary !== null;
        case "unprocessed":
          return article.summary === null;
        case "selected":
          return article.relevance_score >= 0.6;
        case "unselected":
          return article.summary !== null && article.relevance_score < 0.6;
        case "all":
        default:
          return true;
      }
    });
  }, [articles, statusFilter]);

  const stats = useMemo(
    () => ({
      total: articles.length,
      processed: articles.filter((a) => a.summary !== null).length,
      unprocessed: articles.filter((a) => a.summary === null).length,
      selected: articles.filter((a) => a.relevance_score >= 0.6).length,
    }),
    [articles]
  );

  return {
    filteredArticles,
    stats,
  };
}
