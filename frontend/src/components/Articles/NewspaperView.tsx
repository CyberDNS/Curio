import { useQuery } from "@tanstack/react-query";
import { format } from "date-fns";
import { Loader2, AlertCircle } from "lucide-react";
import {
  getNewspaperByDate,
  getTodayNewspaper,
  getNewspaperArticles,
  getArticles,
} from "../../services/api";
import { useNewspaper } from "../../contexts/NewspaperContext";
import { ArticleLayoutView } from "./index";
import type { ViewMode } from "./useViewMode";

interface NewspaperViewProps {
  /** Category slug for filtering, or null for "today" (all categories) */
  categorySlug?: string | null;
  /** Optional fallback when no newspaper exists (only for today/homepage) */
  showFallback?: boolean;
  /** View mode (grid/list) - controlled externally */
  viewMode?: ViewMode;
}

export default function NewspaperView({
  categorySlug = null,
  showFallback = false,
  viewMode = "grid",
}: NewspaperViewProps) {
  const { selectedDate } = useNewspaper();
  const isToday =
    format(selectedDate, "yyyy-MM-dd") === format(new Date(), "yyyy-MM-dd");

  // Get newspaper for selected date
  const { data: newspaper, isLoading: isLoadingNewspaper } = useQuery({
    queryKey: ["newspaper", format(selectedDate, "yyyy-MM-dd")],
    queryFn: () =>
      isToday
        ? getTodayNewspaper()
        : getNewspaperByDate(format(selectedDate, "yyyy-MM-dd")),
    refetchInterval: isToday && !categorySlug ? 30000 : undefined, // Only refetch today's homepage
    retry: false,
  });

  // Get articles for the newspaper (filtered by section if categorySlug provided)
  const section = categorySlug || "today";
  const { data: articles = [], isLoading: isLoadingArticles } = useQuery({
    queryKey: ["newspaper", "articles", newspaper?.id, section],
    queryFn: () => getNewspaperArticles(newspaper!.id, section),
    enabled: !!newspaper,
  });

  // Fallback: fetch all articles if no newspaper exists (homepage only)
  const { data: fallbackArticles = [] } = useQuery({
    queryKey: ["articles", "all", 100],
    queryFn: () => getArticles({ limit: 100 }),
    enabled: showFallback && !newspaper && !isLoadingNewspaper,
  });

  const displayArticles =
    articles.length > 0 ? articles : showFallback ? fallbackArticles : [];
  const isLoading = isLoadingNewspaper || isLoadingArticles;
  const showingFallback =
    showFallback && !newspaper && fallbackArticles.length > 0;

  if (isLoading) {
    return (
      <div className="flex justify-center items-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-newspaper-600" />
      </div>
    );
  }

  return (
    <>
      {/* Fallback warning (homepage only) */}
      {showingFallback && (
        <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-yellow-800">
            <p className="font-semibold mb-1">No newspaper edition yet</p>
            <p>
              The newspaper for this date is being generated. Articles are
              processed and curated automatically every hour.
            </p>
          </div>
        </div>
      )}

      {/* No newspaper warning (category pages) */}
      {!showingFallback && !newspaper && (
        <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-yellow-800">
            <p className="font-semibold mb-1">No newspaper edition yet</p>
            <p>
              {categorySlug
                ? "Today's newspaper is being generated. Category sections will appear once the newspaper is ready."
                : "The newspaper for this date is being generated. Articles are processed and curated automatically every hour."}
            </p>
          </div>
        </div>
      )}

      {/* View toggle and articles */}
      {displayArticles.length > 0 && (
        <ArticleLayoutView articles={displayArticles} viewMode={viewMode} />
      )}

      {/* No articles message - Newspaper-style centered text */}
      {displayArticles.length === 0 && (newspaper || showingFallback) && (
        <div className="text-center py-12">
          <p className="text-xl font-serif text-newspaper-600">
            {categorySlug
              ? "No articles in this section."
              : "No articles available yet."}
          </p>
          <p className="text-sm text-newspaper-500 mt-2">
            {categorySlug
              ? "The AI editor hasn't curated any articles for this section in today's edition yet."
              : "Add some RSS feeds in settings and click refresh to get started!"}
          </p>
        </div>
      )}
    </>
  );
}
