import type { Article } from "../../../types";

interface ArticleSummaryProps {
  article: Article;
  className?: string;
  /** Number of lines to clamp, or "full" for no clamping */
  lines?: 2 | 3 | 4 | "full";
}

/**
 * Displays the article summary, preferring LLM-enhanced summary over original
 */
export default function ArticleSummary({
  article,
  className = "",
  lines = 3,
}: ArticleSummaryProps) {
  const displaySummary =
    article.llm_summary || article.summary || article.description;

  if (!displaySummary) {
    return null;
  }

  const clampClass =
    lines === "full"
      ? ""
      : lines === 2
      ? "line-clamp-2"
      : lines === 4
      ? "line-clamp-4"
      : "line-clamp-3";

  return (
    <p className={`text-newspaper-700 ${clampClass} ${className}`}>
      {displaySummary}
    </p>
  );
}
