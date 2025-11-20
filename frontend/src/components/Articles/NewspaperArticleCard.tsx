import { useState, useEffect, useRef } from "react";
import { formatDistanceToNow } from "date-fns";
import { ExternalLink, BookmarkCheck, RefreshCw, Copy } from "lucide-react";
import type { Article } from "../../types";
import { getProxiedImageUrl, getRelatedArticles } from "../../services/api";
import { useArticleActions } from "../../hooks/useArticleActions";
import { useQuery } from "@tanstack/react-query";
import RelatedArticlesDialog from "./RelatedArticlesDialog";

interface NewspaperArticleCardProps {
  article: Article;
  size: "hero" | "large" | "medium" | "small";
}

export default function NewspaperArticleCard({
  article,
  size,
}: NewspaperArticleCardProps) {
  const [imageError, setImageError] = useState(false);
  const [showRelatedDialog, setShowRelatedDialog] = useState(false);
  // Start at random index to avoid all images showing the same one initially
  const [currentImageIndex, setCurrentImageIndex] = useState(() =>
    Math.floor(Math.random() * (article.image_urls?.length || 1))
  );
  const articleRef = useRef<HTMLElement | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Fetch related articles when dialog is opened
  const { data: relatedArticles = [], isLoading: loadingRelated } = useQuery({
    queryKey: ["relatedArticles", article.id],
    queryFn: () => getRelatedArticles(article.id),
    enabled: showRelatedDialog,
  });

  const {
    markReadMutation,
    reprocessMutation,
    handleClick: handleArticleClick,
    handleReprocess: handleArticleReprocess,
  } = useArticleActions();

  const handleClick = () => handleArticleClick(article);
  const handleReprocess = (e: React.MouseEvent) =>
    handleArticleReprocess(e, article.id);

  const publishedDate = article.published_date
    ? formatDistanceToNow(new Date(article.published_date), { addSuffix: true })
    : null;

  // Use LLM-enhanced data if available, fallback to original
  const displayTitle = article.llm_title || article.title;
  const displaySubtitle = article.llm_subtitle;
  const displaySummary =
    article.llm_summary || article.summary || article.description;

  // Collect all available images
  const allImages: string[] = [];
  if (article.image_url) allImages.push(article.image_url);
  if (article.image_urls && article.image_urls.length > 0) {
    article.image_urls.forEach((url) => {
      if (!allImages.includes(url)) allImages.push(url);
    });
  }

  // Cycle through images every 5 seconds if multiple images exist
  useEffect(() => {
    if (allImages.length <= 1) return;

    const interval = setInterval(() => {
      setCurrentImageIndex((prev) => (prev + 1) % allImages.length);
    }, 5000); // Change image every 5 seconds

    return () => clearInterval(interval);
  }, [allImages.length]);

  // Auto-mark as read after being in viewport for 3 seconds
  useEffect(() => {
    if (article.is_read || !articleRef.current) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            // Article is visible - start timer
            timerRef.current = setTimeout(() => {
              // Mark as read after 3 seconds
              if (!article.is_read) {
                markReadMutation.mutate(article.id);
              }
            }, 3000);
          } else {
            // Article left viewport - cancel timer
            if (timerRef.current) {
              clearTimeout(timerRef.current);
              timerRef.current = null;
            }
          }
        });
      },
      { threshold: 0.5 } // At least 50% visible
    );

    if (articleRef.current) {
      observer.observe(articleRef.current);
    }

    return () => {
      observer.disconnect();
      // Cleanup any pending timers
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [article.id, article.is_read, markReadMutation]);

  const currentImage = allImages[currentImageIndex];
  const primaryImage = getProxiedImageUrl(currentImage);

  // Size-specific styles
  const getSizeStyles = () => {
    switch (size) {
      case "hero":
        return {
          container: "border-b-4 border-newspaper-900",
          layout: "flex flex-col",
          imageContainer: "w-full h-96",
          contentPadding: "p-6",
          title: "newspaper-heading text-4xl md:text-6xl leading-tight mb-3",
          subtitle: "text-xl italic mb-4",
          summary: "text-lg leading-relaxed mb-4",
          meta: "text-base",
          showFullSummary: true,
        };
      case "large":
        return {
          container: "border-b-2 border-newspaper-900",
          layout: "flex flex-col",
          imageContainer: "w-full h-64",
          contentPadding: "p-4",
          title: "newspaper-heading text-2xl md:text-3xl leading-tight mb-2",
          subtitle: "text-base italic mb-3",
          summary: "text-base leading-relaxed mb-3",
          meta: "text-sm",
          showFullSummary: true,
        };
      case "medium":
        return {
          container: "border-b border-newspaper-400",
          layout: "flex flex-col",
          imageContainer: "w-full h-48",
          contentPadding: "p-3",
          title: "newspaper-heading text-xl md:text-2xl leading-tight mb-2",
          subtitle: "text-sm italic mb-2",
          summary: "text-sm leading-relaxed mb-2 line-clamp-3",
          meta: "text-xs",
          showFullSummary: false,
        };
      case "small":
        return {
          container: "border-b border-newspaper-300",
          layout: "flex flex-col",
          imageContainer: "w-full h-32",
          contentPadding: "p-2",
          title: "newspaper-heading text-lg md:text-xl leading-tight mb-1",
          subtitle: "text-xs italic mb-1",
          summary: "text-xs leading-relaxed mb-1 line-clamp-2",
          meta: "text-xs",
          showFullSummary: false,
        };
    }
  };

  const styles = getSizeStyles();

  return (
    <article
      ref={articleRef}
      className={`${styles.container} pb-4 bg-white hover:bg-newspaper-50 transition-colors h-full flex flex-col`}
    >
      <div className={styles.layout}>
        {/* Image with Harry Potter-style animation */}
        {primaryImage && !imageError && (
          <div
            className={`${styles.imageContainer} overflow-hidden relative group`}
          >
            <img
              src={primaryImage}
              alt={displayTitle}
              className="w-full h-full object-cover harry-potter-image"
              onError={() => setImageError(true)}
            />
            {/* Image counter indicator */}
            {allImages.length > 1 && (
              <div className="absolute bottom-2 right-2 bg-black bg-opacity-70 text-white px-2 py-1 rounded text-xs">
                {currentImageIndex + 1} / {allImages.length}
              </div>
            )}
            {/* Click overlay */}
            <div
              className="absolute inset-0 cursor-pointer opacity-0 hover:opacity-100 transition-opacity bg-newspaper-900 bg-opacity-10"
              onClick={handleClick}
            />
          </div>
        )}

        {/* Content */}
        <div className={`${styles.contentPadding} flex-1 flex flex-col`}>
          <h2
            className={`${
              styles.title
            } cursor-pointer hover:text-newspaper-700 transition-colors ${
              article.is_read ? "text-newspaper-500" : "text-newspaper-900"
            }`}
            onClick={handleClick}
          >
            {displayTitle}
          </h2>

          {displaySubtitle && (
            <p className={`${styles.subtitle} text-newspaper-600`}>
              {displaySubtitle}
            </p>
          )}

          {/* Meta info */}
          <div
            className={`flex items-center gap-2 ${styles.meta} text-newspaper-600 mb-2 flex-wrap`}
          >
            {article.feed_source_title && (
              <span className="font-semibold text-newspaper-800">
                {article.feed_source_title}
              </span>
            )}
            {article.author && (
              <span className="font-semibold">{article.author}</span>
            )}
            {publishedDate && <span>{publishedDate}</span>}
            {!article.is_read && (
              <span className="bg-blue-500 text-white px-2 py-0.5 rounded text-xs">
                UNREAD
              </span>
            )}
            {article.relevance_score >= 0.6 && (
              <span className="flex items-center gap-1 text-green-700">
                <BookmarkCheck className="w-3 h-3" />
                {size !== "small" && (
                  <span className="text-xs">Recommended</span>
                )}
              </span>
            )}
          </div>

          {/* Summary */}
          <p className={`${styles.summary} text-newspaper-700 flex-1`}>
            {displaySummary}
          </p>

          {/* Actions */}
          <div className="flex items-center gap-3 mt-auto pt-2">
            <button
              onClick={handleClick}
              className={`inline-flex items-center gap-1 ${styles.meta} font-semibold text-newspaper-900 hover:text-newspaper-700 transition-colors`}
            >
              Read More
              <ExternalLink className="w-3 h-3" />
            </button>
            <button
              onClick={handleReprocess}
              disabled={reprocessMutation.isPending}
              className={`inline-flex items-center gap-1 ${styles.meta} text-newspaper-600 hover:text-newspaper-900 transition-colors disabled:opacity-50`}
              title="Recalculate LLM analysis"
            >
              <RefreshCw
                className={`w-3 h-3 ${
                  reprocessMutation.isPending ? "animate-spin" : ""
                }`}
              />
            </button>
            {article.is_duplicate && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setShowRelatedDialog(true);
                }}
                className={`inline-flex items-center gap-1 ${styles.meta} text-newspaper-600 hover:text-newspaper-900 transition-colors`}
                title="View related articles"
              >
                <Copy className="w-3 h-3" />
                {size !== "small" && <span>Related</span>}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Related Articles Dialog */}
      <RelatedArticlesDialog
        isOpen={showRelatedDialog}
        onClose={() => setShowRelatedDialog(false)}
        relatedArticles={relatedArticles}
        isLoading={loadingRelated}
        onArticleClick={handleArticleClick}
      />
    </article>
  );
}
