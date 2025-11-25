import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bookmark, Loader2 } from "lucide-react";
import { checkArticleSaved, unsaveArticle } from "../../services/api";
import SaveArticleDialog from "./SaveArticleDialog";
import type { Article } from "../../types";

interface BookmarkButtonProps {
  article: Article;
  className?: string;
  showLabel?: boolean;
}

export default function BookmarkButton({
  article,
  className = "",
  showLabel = false,
}: BookmarkButtonProps) {
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const queryClient = useQueryClient();

  // Check if article is saved
  const { data: savedStatus } = useQuery({
    queryKey: ["articleSaved", article.id],
    queryFn: () => checkArticleSaved(article.id),
  });

  const isSaved = savedStatus?.is_saved || false;
  const savedArticleId = savedStatus?.saved_article_id;

  // Unsave mutation
  const unsaveMutation = useMutation({
    mutationFn: () => unsaveArticle(savedArticleId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["articleSaved", article.id] });
      queryClient.invalidateQueries({ queryKey: ["savedArticles"] });
    },
  });

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();

    if (isSaved) {
      // Unsave
      if (confirm("Remove this article from saved articles?")) {
        unsaveMutation.mutate();
      }
    } else {
      // Show save dialog
      setShowSaveDialog(true);
    }
  };

  const isLoading = unsaveMutation.isPending;

  return (
    <>
      <button
        onClick={handleClick}
        disabled={isLoading}
        className={`inline-flex items-center gap-1 text-xs font-semibold transition-colors ${
          isSaved
            ? "text-blue-600 hover:text-blue-800"
            : "text-gray-600 hover:text-gray-800"
        } ${className}`}
        title={isSaved ? "Remove from saved" : "Save article"}
      >
        {isLoading ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : (
          <Bookmark
            className="w-4 h-4"
            fill={isSaved ? "currentColor" : "none"}
          />
        )}
        {showLabel && (isSaved ? "Saved" : "Save")}
      </button>

      {showSaveDialog && (
        <SaveArticleDialog
          articleId={article.id}
          articleTitle={article.llm_title || article.title}
          onClose={() => setShowSaveDialog(false)}
          onSuccess={() => {
            queryClient.invalidateQueries({
              queryKey: ["articleSaved", article.id],
            });
          }}
        />
      )}
    </>
  );
}
