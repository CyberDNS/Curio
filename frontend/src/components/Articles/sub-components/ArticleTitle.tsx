import type { Article } from "../../../types";

interface ArticleTitleProps {
  article: Article;
  className?: string;
  onClick?: () => void;
}

/**
 * Displays the article title, preferring LLM-enhanced title over original
 */
export default function ArticleTitle({
  article,
  className = "",
  onClick,
}: ArticleTitleProps) {
  const displayTitle = article.llm_title || article.title;

  return (
    <h2
      className={`${className} ${
        onClick
          ? "cursor-pointer hover:text-newspaper-700 transition-colors"
          : ""
      } text-newspaper-900`}
      onClick={onClick}
    >
      {displayTitle}
    </h2>
  );
}
