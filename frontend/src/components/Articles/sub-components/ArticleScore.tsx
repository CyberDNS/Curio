import { useState } from "react";
import { Info } from "lucide-react";
import type { Article } from "../../../types";
import DownvoteExplanationDialog from "../DownvoteExplanationDialog";

interface ArticleScoreProps {
  article: Article;
  className?: string;
  /** Show as percentage (e.g., "85%") vs decimal (e.g., "0.85") */
  showAsPercentage?: boolean;
}

/**
 * Displays the article relevance score with adjustment indicator
 */
export default function ArticleScore({
  article,
  className = "",
  showAsPercentage = true,
}: ArticleScoreProps) {
  const [showExplanationDialog, setShowExplanationDialog] = useState(false);

  // Don't show if no score
  if (article.relevance_score <= 0) {
    return null;
  }

  const hasAdjustment =
    article.adjusted_relevance_score !== null &&
    article.adjusted_relevance_score !== article.relevance_score;

  const displayScore = hasAdjustment
    ? article.adjusted_relevance_score!
    : article.relevance_score;

  const formatScore = (score: number) => {
    if (showAsPercentage) {
      return `${(score * 100).toFixed(0)}%`;
    }
    return score.toFixed(2);
  };

  const displayTitle = article.llm_title || article.title;

  const handleExplainClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowExplanationDialog(true);
  };

  return (
    <>
      <span className={`flex items-center gap-1 ${className}`}>
        {hasAdjustment ? (
          <>
            <span className="text-gray-400 line-through">
              {showAsPercentage ? "" : "Score: "}
              {formatScore(article.relevance_score)}
            </span>
            <span className="font-semibold text-orange-600">
              → {formatScore(displayScore)}
            </span>
            <button
              onClick={handleExplainClick}
              className="text-blue-600 hover:text-blue-800 transition-colors"
              title="Explain adjustment"
            >
              <Info className="w-3 h-3" />
            </button>
          </>
        ) : (
          <span className="text-newspaper-600">
            {showAsPercentage ? "" : "Score: "}
            {formatScore(displayScore)}
          </span>
        )}
      </span>

      {/* Downvote Explanation Dialog */}
      {showExplanationDialog && (
        <DownvoteExplanationDialog
          articleId={article.id}
          articleTitle={displayTitle}
          onClose={() => setShowExplanationDialog(false)}
        />
      )}
    </>
  );
}
