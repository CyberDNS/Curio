import { useMutation, useQueryClient } from "@tanstack/react-query";
import { updateArticle, reprocessArticle } from "../services/api";

/**
 * Shared hook for common article actions (mark as read, reprocess)
 * Used by ArticleCard, ArticleListItem, and ArticleActions components
 */
export function useArticleActions() {
  const queryClient = useQueryClient();

  const markReadMutation = useMutation({
    mutationFn: (id: number) => updateArticle(id, { is_read: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["articles"] });
      queryClient.invalidateQueries({ queryKey: ["newspaper"] });
    },
  });

  const reprocessMutation = useMutation({
    mutationFn: (id: number) => reprocessArticle(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["articles"] });
      queryClient.invalidateQueries({ queryKey: ["newspaper"] });
    },
  });

  const handleClick = (article: {
    id: number;
    is_read: boolean;
    link: string;
  }) => {
    if (!article.is_read) {
      markReadMutation.mutate(article.id);
    }
    window.open(article.link, "_blank");
  };

  const handleReprocess = (
    e: React.MouseEvent,
    articleId: number,
    articleTitle?: string
  ) => {
    e.stopPropagation();
    const message = articleTitle
      ? `Recalculate LLM analysis for "${articleTitle}"?`
      : "Recalculate LLM analysis for this article?";

    if (confirm(message)) {
      reprocessMutation.mutate(articleId);
    }
  };

  return {
    markReadMutation,
    reprocessMutation,
    handleClick,
    handleReprocess,
  };
}
