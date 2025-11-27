import type { Article } from "../../types";
import type { ArticleDisplayConfig } from "./types";
import { READER_CONFIG, mergeConfig } from "./configs";
import {
  ArticleImage,
  ArticleTitle,
  ArticleSummary,
  ArticleMeta,
  ArticleScore,
  ArticleActions,
} from "./sub-components";
import { useArticleActions } from "../../hooks/useArticleActions";

interface ArticleListItemProps {
  article: Article;
  config?: Partial<ArticleDisplayConfig>;
  onArticleClick?: (article: Article) => void;
  categoryName?: string | null;
}

/**
 * Article list item component for list/table layouts
 * Displays article in a horizontal format with image on left
 * Fully responsive - stacks vertically on mobile
 */
export default function ArticleListItem({
  article,
  config: configOverrides,
  onArticleClick,
  categoryName,
}: ArticleListItemProps) {
  const config = mergeConfig(READER_CONFIG, configOverrides);

  const { handleClick: defaultHandleClick } = useArticleActions();

  const handleClick = () => {
    if (onArticleClick) {
      onArticleClick(article);
    } else {
      defaultHandleClick(article);
    }
  };

  return (
    <div className="border border-newspaper-300 hover:bg-newspaper-50 transition-colors flex flex-col sm:flex-row gap-3 sm:gap-0 sm:items-stretch">
      {/* Image - full width on mobile, fixed width but full height on larger screens */}
      {config.showImage && (
        <ArticleImage
          article={article}
          className="w-full h-40 sm:w-40 sm:h-auto sm:min-h-[120px] md:w-48 flex-shrink-0"
          onClick={handleClick}
          enableCycling={false}
        />
      )}

      {/* Content */}
      <div className="flex-1 p-3 sm:p-4 flex flex-col">
        {/* Title */}
        <ArticleTitle
          article={article}
          className="newspaper-heading text-base sm:text-lg mb-2"
          onClick={handleClick}
        />

        {/* Meta info row */}
        <div className="flex items-center gap-2 text-xs text-newspaper-600 mb-2 flex-wrap">
          <ArticleMeta
            article={article}
            config={config.showMeta}
            categoryName={categoryName}
            className="text-xs"
            compact={false}
          />
        </div>

        {/* Score */}
        {config.showScore && article.relevance_score > 0 && (
          <div className="mb-2">
            <ArticleScore
              article={article}
              className="text-xs"
              showAsPercentage={false}
            />
          </div>
        )}

        {/* Summary */}
        {config.showSummary && (
          <ArticleSummary
            article={article}
            className="text-sm mb-3 flex-1"
            lines={config.summaryLines === "full" ? 3 : config.summaryLines}
          />
        )}

        {/* Actions */}
        <ArticleActions
          article={article}
          config={config.showActions}
          showLabels={true}
          onArticleClick={onArticleClick}
          className="mt-auto"
        />
      </div>
    </div>
  );
}
