import { formatDistanceToNow } from "date-fns";
import { ExternalLink, ThumbsDown, Info } from "lucide-react";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { downvoteArticle } from "../../services/api";
import type { Article } from "../../types";
import DownvoteExplanationDialog from "./DownvoteExplanationDialog";

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

  const [showExplanationDialog, setShowExplanationDialog] = useState(false);

  const queryClient = useQueryClient();

  const downvoteMutation = useMutation({
    mutationFn: () => downvoteArticle(article.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["articles"] });
    },
  });

  const handleClick = () => {
    if (onArticleClick) {
      onArticleClick(article);
    }
  };

  const handleDownvote = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (
      confirm(
        article.user_vote === -1
          ? "Remove downvote from this article?"
          : "Downvote this article? Future similar articles will be scored lower."
      )
    ) {
      downvoteMutation.mutate();
    }
  };

  const handleExplain = (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowExplanationDialog(true);
  };

  // Determine which score to display
  const hasAdjustment =
    article.adjusted_relevance_score !== null &&
    article.adjusted_relevance_score !== article.relevance_score;
  const displayScore = hasAdjustment
    ? article.adjusted_relevance_score
    : article.relevance_score;

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

      {/* Score Display */}
      {article.relevance_score > 0 && (
        <div className="flex items-center gap-2 mb-2 text-xs">
          {hasAdjustment ? (
            <>
              <span className="text-gray-400 line-through">
                Score: {article.relevance_score.toFixed(2)}
              </span>
              <span className="font-semibold text-orange-600">
                → {displayScore!.toFixed(2)}
              </span>
              <button
                onClick={handleExplain}
                className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800 transition-colors"
                title="Explain adjustment"
              >
                <Info className="w-3 h-3" />
                Why?
              </button>
            </>
          ) : (
            <span className="text-newspaper-600">
              Score: {displayScore?.toFixed(2) ?? "0.00"}
            </span>
          )}
        </div>
      )}

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
        <button
          onClick={handleDownvote}
          disabled={downvoteMutation.isPending}
          className={`inline-flex items-center gap-1 text-xs font-semibold transition-colors ${
            article.user_vote === -1
              ? "text-red-600 hover:text-red-800"
              : "text-gray-600 hover:text-gray-800"
          }`}
          title={
            article.user_vote === -1
              ? "Remove downvote"
              : "Downvote (less like this)"
          }
        >
          <ThumbsDown
            className={`w-3 h-3 ${
              article.user_vote === -1 ? "fill-current" : ""
            }`}
          />
          {article.user_vote === -1 ? "Downvoted" : "Downvote"}
        </button>
      </div>

      {/* Downvote Explanation Dialog */}
      {showExplanationDialog && (
        <DownvoteExplanationDialog
          articleId={article.id}
          articleTitle={displayTitle}
          onClose={() => setShowExplanationDialog(false)}
        />
      )}
    </div>
  );
}
