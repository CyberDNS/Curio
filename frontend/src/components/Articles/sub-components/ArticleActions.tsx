import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ExternalLink,
  ThumbsDown,
  RefreshCw,
  Copy,
  Share2,
  Check,
} from "lucide-react";
import { downvoteArticle, getRelatedArticles } from "../../../services/api";
import { useArticleActions } from "../../../hooks/useArticleActions";
import type { Article } from "../../../types";
import BookmarkButton from "../BookmarkButton";
import RelatedArticlesDialog from "../RelatedArticlesDialog";
import { useState } from "react";

interface ArticleActionsConfig {
  read?: boolean;
  save?: boolean;
  share?: boolean;
  downvote?: boolean;
  reprocess?: boolean;
  related?: boolean;
}

interface ArticleActionsProps {
  article: Article;
  config?: ArticleActionsConfig;
  className?: string;
  /** Show text labels next to icons */
  showLabels?: boolean;
  onArticleClick?: (article: Article) => void;
}

/**
 * Action buttons for articles (Read, Save, Downvote, Reprocess, Related)
 */
export default function ArticleActions({
  article,
  config = {
    read: true,
    save: true,
    share: true,
    downvote: true,
    reprocess: false,
    related: true,
  },
  className = "",
  showLabels = true,
  onArticleClick,
}: ArticleActionsProps) {
  const [showRelatedDialog, setShowRelatedDialog] = useState(false);
  const [shareStatus, setShareStatus] = useState<"idle" | "copied">("idle");
  const queryClient = useQueryClient();

  const {
    reprocessMutation,
    handleClick: defaultHandleClick,
    handleReprocess: handleArticleReprocess,
  } = useArticleActions();

  // Fetch related articles when dialog is opened
  const { data: relatedArticles = [], isLoading: loadingRelated } = useQuery({
    queryKey: ["relatedArticles", article.id],
    queryFn: () => getRelatedArticles(article.id),
    enabled: showRelatedDialog,
  });

  const downvoteMutation = useMutation({
    mutationFn: () => downvoteArticle(article.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["articles"] });
      queryClient.invalidateQueries({ queryKey: ["newspaper"] });
    },
  });

  const handleClick = () => {
    if (onArticleClick) {
      onArticleClick(article);
    } else {
      defaultHandleClick(article);
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

  const handleReprocess = (e: React.MouseEvent) => {
    handleArticleReprocess(e, article.id, article.llm_title || article.title);
  };

  const handleRelated = (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowRelatedDialog(true);
  };

  const handleShare = async (e: React.MouseEvent) => {
    e.stopPropagation();

    const title = article.llm_title || article.title;
    const url = article.link;
    const text = article.llm_summary || "";

    // Try native Web Share API first (works on mobile and some desktop browsers)
    if (navigator.share) {
      try {
        await navigator.share({
          title,
          text,
          url,
        });
        return;
      } catch (err) {
        // User cancelled or share failed - fall through to clipboard
        if ((err as Error).name === "AbortError") {
          return; // User cancelled, don't copy to clipboard
        }
      }
    }

    // Fallback: Copy link to clipboard
    try {
      await navigator.clipboard.writeText(url);
      setShareStatus("copied");
      setTimeout(() => setShareStatus("idle"), 2000);
    } catch (err) {
      console.error("Failed to copy link:", err);
    }
  };

  const buttonClass = `inline-flex items-center gap-1 text-xs font-semibold transition-colors`;

  return (
    <>
      <div className={`flex items-center flex-wrap gap-2 ${className}`}>
        {/* Read Article */}
        {config.read && (
          <button
            onClick={handleClick}
            className={`${buttonClass} text-newspaper-900 hover:text-newspaper-700`}
          >
            {showLabels ? "Read Article" : "Read"}
            <ExternalLink className="w-3 h-3" />
          </button>
        )}

        {/* Save/Bookmark */}
        {config.save && (
          <BookmarkButton article={article} showLabel={showLabels} />
        )}

        {/* Share */}
        {config.share && (
          <button
            onClick={handleShare}
            className={`${buttonClass} ${
              shareStatus === "copied"
                ? "text-green-600"
                : "text-newspaper-600 hover:text-newspaper-900"
            }`}
            title={shareStatus === "copied" ? "Link copied!" : "Share article"}
          >
            {shareStatus === "copied" ? (
              <Check className="w-3 h-3" />
            ) : (
              <Share2 className="w-3 h-3" />
            )}
            {showLabels && (shareStatus === "copied" ? "Copied!" : "Share")}
          </button>
        )}

        {/* Downvote */}
        {config.downvote && (
          <button
            onClick={handleDownvote}
            disabled={downvoteMutation.isPending}
            className={`${buttonClass} ${
              article.user_vote === -1
                ? "text-red-600 hover:text-red-800"
                : "text-gray-600 hover:text-gray-800"
            } disabled:opacity-50`}
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
            {showLabels &&
              (article.user_vote === -1 ? "Downvoted" : "Downvote")}
          </button>
        )}

        {/* Reprocess */}
        {config.reprocess && (
          <button
            onClick={handleReprocess}
            disabled={reprocessMutation.isPending}
            className={`${buttonClass} text-newspaper-600 hover:text-newspaper-900 disabled:opacity-50`}
            title="Recalculate LLM analysis"
          >
            <RefreshCw
              className={`w-3 h-3 ${
                reprocessMutation.isPending ? "animate-spin" : ""
              }`}
            />
            {showLabels && "Reprocess"}
          </button>
        )}

        {/* Related Articles */}
        {config.related && article.is_duplicate && (
          <button
            onClick={handleRelated}
            className={`${buttonClass} text-newspaper-600 hover:text-newspaper-900`}
            title="View related articles"
          >
            <Copy className="w-3 h-3" />
            {showLabels && "Related"}
          </button>
        )}
      </div>

      {/* Related Articles Dialog */}
      <RelatedArticlesDialog
        isOpen={showRelatedDialog}
        onClose={() => setShowRelatedDialog(false)}
        relatedArticles={relatedArticles}
        isLoading={loadingRelated}
        onArticleClick={defaultHandleClick}
      />
    </>
  );
}
