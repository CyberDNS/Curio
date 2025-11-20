import { formatDistanceToNow } from "date-fns";
import { ExternalLink } from "lucide-react";
import type { Article } from "../../types";

interface ArticleListCardProps {
  article: Article;
  onArticleClick?: (article: Article) => void;
  categoryName?: string | null;
}

export default function ArticleListCard({
  article,
  onArticleClick,
  categoryName,
}: ArticleListCardProps) {
  const displayTitle = article.llm_title || article.title;
  const displaySummary =
    article.llm_summary || article.summary || article.description;

  const handleClick = () => {
    if (onArticleClick) {
      onArticleClick(article);
    }
  };

  return (
    <div className="border border-newspaper-300 p-4 hover:bg-newspaper-50 transition-colors">
      <h4
        className="newspaper-heading text-lg mb-2 cursor-pointer hover:text-newspaper-700"
        onClick={handleClick}
      >
        {displayTitle}
      </h4>

      {/* Meta info */}
      <div className="flex items-center gap-2 text-xs text-newspaper-600 mb-2 flex-wrap">
        {article.feed_source_title && (
          <span className="font-semibold text-newspaper-800">
            {article.feed_source_title}
          </span>
        )}
        {article.author && (
          <span className="font-semibold">{article.author}</span>
        )}
        {article.published_date && (
          <span>
            {formatDistanceToNow(new Date(article.published_date), {
              addSuffix: true,
            })}
          </span>
        )}
        {categoryName && (
          <span className="px-2 py-0.5 bg-blue-100 text-blue-800 rounded">
            {categoryName}
          </span>
        )}
      </div>

      {/* Summary */}
      {displaySummary && (
        <p className="text-sm text-newspaper-700 mb-3 line-clamp-3">
          {displaySummary}
        </p>
      )}

      {/* Actions */}
      <div className="flex items-center gap-3">
        <button
          onClick={handleClick}
          className="inline-flex items-center gap-1 text-xs font-semibold text-newspaper-900 hover:text-newspaper-700 transition-colors"
        >
          Read Article
          <ExternalLink className="w-3 h-3" />
        </button>
      </div>
    </div>
  );
}
