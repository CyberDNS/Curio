import { RefreshCw } from "lucide-react";
import type { Article } from "../../types";
import ArticleListCard from "./ArticleListCard";

interface RelatedArticlesDialogProps {
  isOpen: boolean;
  onClose: () => void;
  relatedArticles: Article[];
  isLoading: boolean;
  onArticleClick: (article: Article) => void;
  getCategoryName?: (categoryId: number | null) => string | null;
}

export default function RelatedArticlesDialog({
  isOpen,
  onClose,
  relatedArticles,
  isLoading,
  onArticleClick,
  getCategoryName,
}: RelatedArticlesDialogProps) {
  if (!isOpen) return null;

  const handleArticleClick = (article: Article) => {
    onArticleClick(article);
    onClose();
  };

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-white max-w-2xl w-full max-h-[80vh] overflow-auto border-4 border-newspaper-900 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Dialog Header */}
        <div className="sticky top-0 bg-white border-b-2 border-newspaper-900 p-4">
          <div className="flex items-center justify-between">
            <h3 className="newspaper-heading text-2xl">Related Articles</h3>
            <button
              onClick={onClose}
              className="text-newspaper-600 hover:text-newspaper-900 text-2xl leading-none"
              aria-label="Close"
            >
              ×
            </button>
          </div>
          <p className="text-sm text-newspaper-600 mt-1">
            These articles are similar or duplicate stories detected by our
            system
          </p>
        </div>

        {/* Dialog Content */}
        <div className="p-4">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <RefreshCw className="w-6 h-6 animate-spin text-newspaper-600" />
              <span className="ml-2 text-newspaper-600">
                Loading related articles...
              </span>
            </div>
          ) : relatedArticles.length === 0 ? (
            <div className="text-center py-8 text-newspaper-600">
              No related articles found
            </div>
          ) : (
            <div className="space-y-4">
              {relatedArticles.map((relatedArticle) => (
                <ArticleListCard
                  key={relatedArticle.id}
                  article={relatedArticle}
                  onArticleClick={handleArticleClick}
                  categoryName={
                    getCategoryName
                      ? getCategoryName(relatedArticle.category_id)
                      : undefined
                  }
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
