import { formatDistanceToNow } from "date-fns";
import { BookmarkCheck } from "lucide-react";
import type { Article } from "../../../types";

interface ArticleMetaConfig {
  source?: boolean;
  author?: boolean;
  date?: boolean;
  category?: boolean;
  unreadBadge?: boolean;
  recommendedBadge?: boolean;
}

interface ArticleMetaProps {
  article: Article;
  config?: ArticleMetaConfig;
  categoryName?: string | null;
  className?: string;
  /** Show compact version (less text) */
  compact?: boolean;
}

/**
 * Displays article metadata (source, author, date, category, badges)
 */
export default function ArticleMeta({
  article,
  config = {
    source: true,
    author: true,
    date: true,
    category: false,
    unreadBadge: true,
    recommendedBadge: true,
  },
  categoryName,
  className = "",
  compact = false,
}: ArticleMetaProps) {
  const publishedDate = article.published_date
    ? formatDistanceToNow(new Date(article.published_date), { addSuffix: true })
    : null;

  const isRecommended = article.relevance_score >= 0.6;

  return (
    <div className={`flex items-center gap-2 text-newspaper-600 flex-wrap ${className}`}>
      {/* Source */}
      {config.source && article.feed_source_title && (
        <span className="font-semibold text-newspaper-800">
          {article.feed_source_title}
        </span>
      )}

      {/* Author */}
      {config.author && article.author && (
        <span className="font-semibold">{article.author}</span>
      )}

      {/* Date */}
      {config.date && publishedDate && <span>{publishedDate}</span>}

      {/* Category */}
      {config.category && categoryName && (
        <span className="px-2 py-0.5 bg-blue-100 text-blue-800 rounded text-xs">
          {categoryName}
        </span>
      )}

      {/* Unread Badge */}
      {config.unreadBadge && !article.is_read && (
        <span className="bg-blue-500 text-white px-2 py-0.5 rounded text-xs">
          UNREAD
        </span>
      )}

      {/* Recommended Badge */}
      {config.recommendedBadge && isRecommended && (
        <span className="flex items-center gap-1 text-green-700">
          <BookmarkCheck className="w-3 h-3" />
          {!compact && <span className="text-xs">Recommended</span>}
        </span>
      )}
    </div>
  );
}
