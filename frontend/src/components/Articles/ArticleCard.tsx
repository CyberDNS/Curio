import { useRef, useEffect } from "react";
import type { Article } from "../../types";
import type { ArticleDisplayConfig, ArticleCardSize } from "./types";
import { getSizeStyles } from "./types";
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

interface ArticleCardProps {
  article: Article;
  size?: ArticleCardSize;
  config?: Partial<ArticleDisplayConfig>;
  onArticleClick?: (article: Article) => void;
  categoryName?: string | null;
  /** Auto-mark as read after being visible for 1 second */
  autoMarkRead?: boolean;
}

/**
 * Article card component for grid layouts
 * Displays article in a vertical card format with image on top
 * Supports multiple size variants: hero, large, medium, small
 */
export default function ArticleCard({
  article,
  size = "medium",
  config: configOverrides,
  onArticleClick,
  categoryName,
  autoMarkRead = true,
}: ArticleCardProps) {
  const articleRef = useRef<HTMLElement | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const config = mergeConfig(READER_CONFIG, configOverrides);
  const styles = getSizeStyles(size);

  const { markReadMutation, handleClick: defaultHandleClick } =
    useArticleActions();

  const handleClick = () => {
    if (onArticleClick) {
      onArticleClick(article);
    } else {
      defaultHandleClick(article);
    }
  };

  // Auto-mark as read after being in viewport for 1 second
  useEffect(() => {
    if (!autoMarkRead || article.is_read || !articleRef.current) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            // Article is visible - start timer
            timerRef.current = setTimeout(() => {
              if (!article.is_read) {
                markReadMutation.mutate(article.id);
              }
            }, 1000);
          } else {
            // Article left viewport - cancel timer
            if (timerRef.current) {
              clearTimeout(timerRef.current);
              timerRef.current = null;
            }
          }
        });
      },
      { threshold: 0.5 }
    );

    if (articleRef.current) {
      observer.observe(articleRef.current);
    }

    return () => {
      observer.disconnect();
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [article.id, article.is_read, markReadMutation, autoMarkRead]);

  // Determine summary line clamp based on size
  const summaryLines =
    config.summaryLines === "full"
      ? "full"
      : size === "hero" || size === "large"
      ? "full"
      : size === "medium"
      ? 3
      : 2;

  // Compact mode for small size
  const isCompact = size === "small";

  return (
    <article
      ref={articleRef}
      className={`${styles.container} pb-4 bg-white hover:bg-newspaper-50 transition-colors h-full flex flex-col`}
    >
      {/* Image */}
      {config.showImage && (
        <ArticleImage
          article={article}
          className={styles.imageContainer}
          onClick={handleClick}
          enableCycling={true}
        />
      )}

      {/* Content */}
      <div className={`${styles.contentPadding} flex-1 flex flex-col`}>
        {/* Title */}
        <ArticleTitle
          article={article}
          className={styles.title}
          onClick={handleClick}
        />

        {/* Subtitle */}
        {config.showSubtitle && article.llm_subtitle && (
          <p className={`${styles.subtitle} text-newspaper-600`}>
            {article.llm_subtitle}
          </p>
        )}

        {/* Meta info row */}
        <div
          className={`flex items-center gap-2 ${styles.meta} mb-2 flex-wrap`}
        >
          <ArticleMeta
            article={article}
            config={config.showMeta}
            categoryName={categoryName}
            className={styles.meta}
            compact={isCompact}
          />

          {/* Score */}
          {config.showScore && (
            <ArticleScore
              article={article}
              className={styles.meta}
              showAsPercentage={true}
            />
          )}
        </div>

        {/* Summary */}
        {config.showSummary && (
          <ArticleSummary
            article={article}
            className={`${styles.summary} flex-1`}
            lines={summaryLines}
          />
        )}

        {/* Actions */}
        <ArticleActions
          article={article}
          config={config.showActions}
          className="mt-auto pt-2"
          showLabels={!isCompact}
          onArticleClick={onArticleClick}
        />
      </div>
    </article>
  );
}
