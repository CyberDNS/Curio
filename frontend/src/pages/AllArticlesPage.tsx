import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getArticles,
  reprocessArticle,
  processArticles,
  getCategories,
  getRelatedArticles,
} from "../services/api";
import PageHeader from "../components/Layout/PageHeader";
import {
  Loader2,
  RefreshCw,
  ExternalLink,
  Check,
  X,
  Sparkles,
  Copy,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";

type FilterType =
  | "all"
  | "processed"
  | "unprocessed"
  | "selected"
  | "unselected"
  | "duplicates";

export default function AllArticlesPage() {
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState<FilterType>("all");
  const [page, setPage] = useState(0);
  const [processingArticleIds, setProcessingArticleIds] = useState<Set<number>>(
    new Set()
  );
  const [showProcessDialog, setShowProcessDialog] = useState(false);
  const [daysBack, setDaysBack] = useState<number>(7);
  const [showRelatedDialog, setShowRelatedDialog] = useState(false);
  const [selectedArticleId, setSelectedArticleId] = useState<number | null>(
    null
  );
  const pageSize = 50;

  const { data: allArticles = [], isLoading } = useQuery({
    queryKey: ["articles", "all", 1000],
    queryFn: () => getArticles({ limit: 1000 }),
    refetchInterval: 30000,
  });

  const { data: categories = [] } = useQuery({
    queryKey: ["categories"],
    queryFn: getCategories,
  });

  const { data: relatedArticles = [], isLoading: loadingRelated } = useQuery({
    queryKey: ["relatedArticles", selectedArticleId],
    queryFn: () => getRelatedArticles(selectedArticleId!),
    enabled: showRelatedDialog && selectedArticleId !== null,
  });

  // Map category IDs to category names
  const getCategoryName = (categoryId: number | null) => {
    if (!categoryId) return null;
    const category = categories.find((c) => c.id === categoryId);
    return category?.name || null;
  };

  const reprocessMutation = useMutation({
    mutationFn: (id: number) => reprocessArticle(id),
    onSuccess: (_, articleId) => {
      queryClient.invalidateQueries({ queryKey: ["articles"] });
      setProcessingArticleIds((prev) => {
        const next = new Set(prev);
        next.delete(articleId);
        return next;
      });
    },
    onError: (_, articleId) => {
      setProcessingArticleIds((prev) => {
        const next = new Set(prev);
        next.delete(articleId);
        return next;
      });
    },
  });

  const processMutation = useMutation({
    mutationFn: (days: number) => processArticles(days),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["articles"] });
      setShowProcessDialog(false);
    },
  });

  const handleReprocess = (articleId: number, title: string) => {
    if (confirm(`Recalculate LLM analysis for "${title}"?`)) {
      setProcessingArticleIds((prev) => new Set(prev).add(articleId));
      reprocessMutation.mutate(articleId);
    }
  };

  const handleProcessConfirm = () => {
    processMutation.mutate(daysBack);
  };

  // Filter articles based on selected filter
  const filteredArticles = allArticles.filter((article) => {
    switch (filter) {
      case "processed":
        return article.summary !== null;
      case "unprocessed":
        return article.summary === null;
      case "selected":
        return article.relevance_score >= 0.6;
      case "unselected":
        return article.summary !== null && article.relevance_score < 0.6;
      case "duplicates":
        return article.is_duplicate;
      default:
        return true;
    }
  });

  const totalPages = Math.ceil(filteredArticles.length / pageSize);
  const paginatedArticles = filteredArticles.slice(
    page * pageSize,
    (page + 1) * pageSize
  );

  const stats = {
    total: allArticles.length,
    processed: allArticles.filter((a) => a.summary !== null).length,
    unprocessed: allArticles.filter((a) => a.summary === null).length,
    selected: allArticles.filter((a) => a.relevance_score >= 0.6).length,
    duplicates: allArticles.filter((a) => a.is_duplicate).length,
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-newspaper-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHeader
        title="All Articles"
        subtitle="View and manage all articles • Processing status and AI selections"
      />

      {/* Page Actions */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => setShowProcessDialog(true)}
          disabled={stats.unprocessed === 0 || processMutation.isPending}
          className="flex items-center gap-2 px-4 py-2 bg-newspaper-900 text-white hover:bg-newspaper-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          title="Process unprocessed articles with AI"
        >
          <Sparkles className="w-4 h-4" />
          Process Articles
        </button>
      </div>

      {/* Statistics */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="border border-newspaper-300 p-4 bg-white">
          <div className="text-2xl font-bold text-newspaper-900">
            {stats.total}
          </div>
          <div className="text-sm text-newspaper-600">Total Articles</div>
        </div>
        <div className="border border-newspaper-300 p-4 bg-white">
          <div className="text-2xl font-bold text-green-700">
            {stats.processed}
          </div>
          <div className="text-sm text-newspaper-600">Processed</div>
        </div>
        <div className="border border-newspaper-300 p-4 bg-white">
          <div className="text-2xl font-bold text-orange-600">
            {stats.unprocessed}
          </div>
          <div className="text-sm text-newspaper-600">Unprocessed</div>
        </div>
        <div className="border border-newspaper-300 p-4 bg-white">
          <div className="text-2xl font-bold text-blue-700">
            {stats.selected}
          </div>
          <div className="text-sm text-newspaper-600">AI Selected</div>
        </div>
        <div className="border border-newspaper-300 p-4 bg-white">
          <div className="text-2xl font-bold text-purple-700">
            {stats.duplicates}
          </div>
          <div className="text-sm text-newspaper-600">Duplicates</div>
        </div>
      </div>

      {/* Process Dialog */}
      {showProcessDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 max-w-md w-full mx-4 border-2 border-newspaper-900">
            <h3 className="newspaper-heading text-xl mb-4">
              Process Articles with AI
            </h3>
            <p className="text-sm text-newspaper-600 mb-4">
              Process unprocessed articles from the last N days with the LLM to
              generate summaries, categories, and relevance scores.
            </p>
            <div className="mb-6">
              <label className="block text-sm font-medium mb-2">
                Days to go back
              </label>
              <input
                type="number"
                min="1"
                max="365"
                value={daysBack}
                onChange={(e) => setDaysBack(parseInt(e.target.value) || 7)}
                className="w-full px-3 py-2 border border-newspaper-300 focus:outline-none focus:border-newspaper-900"
                placeholder="7"
              />
              <p className="text-xs text-newspaper-600 mt-1">
                Only unprocessed articles from the last {daysBack} days will be
                processed
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleProcessConfirm}
                disabled={processMutation.isPending}
                className="flex-1 px-4 py-2 bg-blue-600 text-white hover:bg-blue-700 transition-colors disabled:opacity-50"
              >
                {processMutation.isPending ? "Processing..." : "Process"}
              </button>
              <button
                onClick={() => setShowProcessDialog(false)}
                disabled={processMutation.isPending}
                className="flex-1 px-4 py-2 border border-newspaper-300 hover:bg-newspaper-100 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="space-y-4">
        <div>
          <div className="text-sm font-semibold text-newspaper-900 mb-2">
            Filter by Status
          </div>
          <div className="flex gap-2 flex-wrap">
            <button
              onClick={() => {
                setFilter("all");
                setPage(0);
              }}
              className={`px-4 py-2 text-sm transition-colors ${
                filter === "all"
                  ? "bg-newspaper-900 text-white"
                  : "bg-newspaper-200 text-newspaper-900 hover:bg-newspaper-300"
              }`}
            >
              All ({allArticles.length})
            </button>
            <button
              onClick={() => {
                setFilter("processed");
                setPage(0);
              }}
              className={`px-4 py-2 text-sm transition-colors ${
                filter === "processed"
                  ? "bg-newspaper-900 text-white"
                  : "bg-newspaper-200 text-newspaper-900 hover:bg-newspaper-300"
              }`}
            >
              Processed ({stats.processed})
            </button>
            <button
              onClick={() => {
                setFilter("unprocessed");
                setPage(0);
              }}
              className={`px-4 py-2 text-sm transition-colors ${
                filter === "unprocessed"
                  ? "bg-newspaper-900 text-white"
                  : "bg-newspaper-200 text-newspaper-900 hover:bg-newspaper-300"
              }`}
            >
              Unprocessed ({stats.unprocessed})
            </button>
            <button
              onClick={() => {
                setFilter("selected");
                setPage(0);
              }}
              className={`px-4 py-2 text-sm transition-colors ${
                filter === "selected"
                  ? "bg-newspaper-900 text-white"
                  : "bg-newspaper-200 text-newspaper-900 hover:bg-newspaper-300"
              }`}
            >
              AI Selected ({stats.selected})
            </button>
            <button
              onClick={() => {
                setFilter("unselected");
                setPage(0);
              }}
              className={`px-4 py-2 text-sm transition-colors ${
                filter === "unselected"
                  ? "bg-newspaper-900 text-white"
                  : "bg-newspaper-200 text-newspaper-900 hover:bg-newspaper-300"
              }`}
            >
              Not Selected ({stats.processed - stats.selected})
            </button>
            <button
              onClick={() => {
                setFilter("duplicates");
                setPage(0);
              }}
              className={`px-4 py-2 text-sm transition-colors ${
                filter === "duplicates"
                  ? "bg-newspaper-900 text-white"
                  : "bg-newspaper-200 text-newspaper-900 hover:bg-newspaper-300"
              }`}
            >
              Duplicates ({stats.duplicates})
            </button>
          </div>
        </div>
      </div>

      {/* Articles Table - Desktop */}
      <div className="hidden md:block bg-white border border-newspaper-300 overflow-x-auto">
        <table className="w-full">
          <thead className="bg-newspaper-100 border-b border-newspaper-300">
            <tr>
              <th className="text-left p-3 text-sm font-semibold">Title</th>
              <th className="text-left p-3 text-sm font-semibold w-32">
                Category
              </th>
              <th className="text-left p-3 text-sm font-semibold w-32">
                Status
              </th>
              <th className="text-left p-3 text-sm font-semibold w-24">
                Score
              </th>
              <th className="text-left p-3 text-sm font-semibold w-32">
                Published
              </th>
              <th className="text-left p-3 text-sm font-semibold w-32">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {paginatedArticles.map((article) => {
              const categoryName = getCategoryName(article.category_id);
              return (
                <tr
                  key={article.id}
                  className="border-b border-newspaper-200 hover:bg-newspaper-50"
                >
                  <td className="p-3">
                    <div className="flex items-start gap-2">
                      <div className="flex-1">
                        <div className="font-semibold text-sm">
                          {article.llm_title || article.title}
                        </div>
                        {article.feed_source_title && (
                          <div className="text-xs text-newspaper-800 font-semibold mt-1">
                            {article.feed_source_title}
                          </div>
                        )}
                        {article.summary && (
                          <div className="text-xs text-newspaper-600 mt-1 line-clamp-2">
                            {article.summary}
                          </div>
                        )}
                      </div>
                      {article.is_duplicate && (
                        <span className="inline-flex items-center px-2 py-1 text-xs font-semibold bg-purple-100 text-purple-800 rounded">
                          <Copy className="w-3 h-3 mr-1" />
                          Duplicate
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="p-3">
                    {categoryName ? (
                      <span className="inline-block px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">
                        {categoryName}
                      </span>
                    ) : (
                      <span className="text-xs text-newspaper-400">—</span>
                    )}
                  </td>
                  <td className="p-3">
                    <div className="flex flex-col gap-1">
                      {article.summary ? (
                        <span className="inline-flex items-center gap-1 text-xs text-green-700">
                          <Check className="w-3 h-3" />
                          Processed
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-xs text-orange-600">
                          <X className="w-3 h-3" />
                          Pending
                        </span>
                      )}
                      {article.relevance_score >= 0.6 && (
                        <span className="inline-flex items-center gap-1 text-xs text-green-700">
                          <Check className="w-3 h-3" />
                          Recommended
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="p-3">
                    {article.summary && (
                      <div className="text-sm">
                        <div className="font-semibold">
                          {(article.relevance_score * 100).toFixed(0)}%
                        </div>
                        <div className="w-16 h-2 bg-newspaper-200 mt-1">
                          <div
                            className="h-full bg-blue-600"
                            style={{
                              width: `${article.relevance_score * 100}%`,
                            }}
                          />
                        </div>
                      </div>
                    )}
                  </td>
                  <td className="p-3 text-xs text-newspaper-600">
                    {article.published_date
                      ? formatDistanceToNow(new Date(article.published_date), {
                          addSuffix: true,
                        })
                      : "Unknown"}
                  </td>
                  <td className="p-3">
                    <div className="flex items-center gap-2">
                      <a
                        href={article.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-xs text-newspaper-700 hover:text-newspaper-900"
                      >
                        <ExternalLink className="w-3 h-3" />
                        View
                      </a>
                      {article.is_duplicate && (
                        <button
                          onClick={() => {
                            setSelectedArticleId(article.id);
                            setShowRelatedDialog(true);
                          }}
                          className="p-2 text-purple-600 hover:bg-purple-50 rounded transition-colors"
                          title="View related articles"
                        >
                          <Copy className="w-4 h-4" />
                        </button>
                      )}
                      <button
                        onClick={() =>
                          handleReprocess(
                            article.id,
                            article.llm_title || article.title
                          )
                        }
                        disabled={processingArticleIds.has(article.id)}
                        className="p-2 text-newspaper-600 hover:bg-newspaper-100 rounded transition-colors disabled:opacity-50"
                        title="Recalculate LLM analysis"
                      >
                        <RefreshCw
                          className={`w-4 h-4 ${
                            processingArticleIds.has(article.id)
                              ? "animate-spin"
                              : ""
                          }`}
                        />
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {filteredArticles.length === 0 && (
          <div className="text-center py-12 text-newspaper-600">
            <p className="text-lg">No articles found</p>
            <p className="text-sm mt-2">Try adjusting your filter</p>
          </div>
        )}
      </div>

      {/* Articles List - Mobile */}
      <div className="md:hidden space-y-3">
        {paginatedArticles.map((article) => {
          const categoryName = getCategoryName(article.category_id);
          return (
            <div
              key={article.id}
              className="bg-white border border-newspaper-300 p-4"
            >
              <div className="space-y-2">
                {/* Title */}
                <div className="font-semibold text-sm">
                  {article.llm_title || article.title}
                </div>

                {/* Source */}
                {article.feed_source_title && (
                  <div className="text-xs text-newspaper-800 font-semibold">
                    {article.feed_source_title}
                  </div>
                )}

                {/* Category */}
                {categoryName && (
                  <div>
                    <span className="inline-block px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">
                      {categoryName}
                    </span>
                  </div>
                )}

                {/* Summary */}
                {article.summary && (
                  <div className="text-xs text-newspaper-600 line-clamp-3">
                    {article.summary}
                  </div>
                )}

                {/* Status badges */}
                <div className="flex flex-wrap gap-2">
                  {article.summary ? (
                    <span className="inline-flex items-center gap-1 text-xs text-green-700">
                      <Check className="w-3 h-3" />
                      Processed
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-xs text-orange-600">
                      <X className="w-3 h-3" />
                      Pending
                    </span>
                  )}
                  {article.relevance_score >= 0.6 && (
                    <span className="inline-flex items-center gap-1 text-xs text-green-700">
                      <Check className="w-3 h-3" />
                      Recommended
                    </span>
                  )}
                  {article.is_duplicate && (
                    <span className="inline-flex items-center gap-1 text-xs text-purple-700">
                      <Copy className="w-3 h-3" />
                      Duplicate
                    </span>
                  )}
                </div>

                {/* Score and Published */}
                <div className="flex items-center justify-between text-xs text-newspaper-600">
                  <div>
                    {article.summary && (
                      <span className="font-semibold">
                        Score: {(article.relevance_score * 100).toFixed(0)}%
                      </span>
                    )}
                  </div>
                  <div>
                    {article.published_date
                      ? formatDistanceToNow(new Date(article.published_date), {
                          addSuffix: true,
                        })
                      : "Unknown"}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-3 pt-2 border-t border-newspaper-200">
                  <a
                    href={article.link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-newspaper-700 hover:text-newspaper-900"
                  >
                    <ExternalLink className="w-3 h-3" />
                    View Article
                  </a>
                  {article.is_duplicate && (
                    <button
                      onClick={() => {
                        setSelectedArticleId(article.id);
                        setShowRelatedDialog(true);
                      }}
                      className="inline-flex items-center gap-1 text-xs text-purple-700 hover:text-purple-900"
                      title="View related articles"
                    >
                      <Copy className="w-3 h-3" />
                      Related
                    </button>
                  )}
                  <button
                    onClick={() =>
                      handleReprocess(
                        article.id,
                        article.llm_title || article.title
                      )
                    }
                    disabled={processingArticleIds.has(article.id)}
                    className="inline-flex items-center gap-1 text-xs text-newspaper-600 hover:text-newspaper-900 disabled:opacity-50"
                    title="Recalculate LLM analysis"
                  >
                    <RefreshCw
                      className={`w-3 h-3 ${
                        processingArticleIds.has(article.id)
                          ? "animate-spin"
                          : ""
                      }`}
                    />
                    Reprocess
                  </button>
                </div>
              </div>
            </div>
          );
        })}

        {filteredArticles.length === 0 && (
          <div className="text-center py-12 text-newspaper-600 bg-white border border-newspaper-300">
            <p className="text-lg">No articles found</p>
            <p className="text-sm mt-2">Try adjusting your filter</p>
          </div>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center gap-2 items-center">
          <button
            onClick={() => setPage(Math.max(0, page - 1))}
            disabled={page === 0}
            className="px-4 py-2 bg-newspaper-900 text-white disabled:opacity-50 disabled:cursor-not-allowed hover:bg-newspaper-700 transition-colors"
          >
            Previous
          </button>
          <span className="text-sm text-newspaper-600">
            Page {page + 1} of {totalPages}
          </span>
          <button
            onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
            disabled={page === totalPages - 1}
            className="px-4 py-2 bg-newspaper-900 text-white disabled:opacity-50 disabled:cursor-not-allowed hover:bg-newspaper-700 transition-colors"
          >
            Next
          </button>
        </div>
      )}

      {/* Related Articles Dialog */}
      {showRelatedDialog && selectedArticleId && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
          onClick={() => {
            setShowRelatedDialog(false);
            setSelectedArticleId(null);
          }}
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
                  onClick={() => {
                    setShowRelatedDialog(false);
                    setSelectedArticleId(null);
                  }}
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
              {loadingRelated ? (
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
                    <div
                      key={relatedArticle.id}
                      className="border border-newspaper-300 p-4 hover:bg-newspaper-50 transition-colors"
                    >
                      <a
                        href={relatedArticle.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="newspaper-heading text-lg mb-2 hover:text-newspaper-700 block"
                      >
                        {relatedArticle.llm_title || relatedArticle.title}
                      </a>

                      {/* Meta info */}
                      <div className="flex items-center gap-2 text-xs text-newspaper-600 mb-2 flex-wrap">
                        {relatedArticle.feed_source_title && (
                          <span className="font-semibold text-newspaper-800">
                            {relatedArticle.feed_source_title}
                          </span>
                        )}
                        {relatedArticle.author && (
                          <span className="font-semibold">
                            {relatedArticle.author}
                          </span>
                        )}
                        {relatedArticle.published_date && (
                          <span>
                            {formatDistanceToNow(
                              new Date(relatedArticle.published_date),
                              { addSuffix: true }
                            )}
                          </span>
                        )}
                        {getCategoryName(relatedArticle.category_id) && (
                          <span className="px-2 py-0.5 bg-blue-100 text-blue-800 rounded">
                            {getCategoryName(relatedArticle.category_id)}
                          </span>
                        )}
                      </div>

                      {/* Summary */}
                      {relatedArticle.llm_summary && (
                        <p className="text-sm text-newspaper-700 line-clamp-3">
                          {relatedArticle.llm_summary}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
