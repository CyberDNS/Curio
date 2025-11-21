import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getArticles,
  reprocessArticle,
  getCategories,
  getRelatedArticles,
  downvoteArticle,
  explainScoreAdjustment,
  runFullUpdate,
} from "../services/api";
import PageHeader from "../components/Layout/PageHeader";
import {
  Loader2,
  RefreshCw,
  ExternalLink,
  Check,
  X,
  Copy,
  ThumbsDown,
  Info,
  GitCompare,
  Newspaper,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import RelatedArticlesDialog from "../components/Articles/RelatedArticlesDialog";

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
  const [showRelatedDialog, setShowRelatedDialog] = useState(false);
  const [selectedArticleId, setSelectedArticleId] = useState<number | null>(
    null
  );
  const [explanations, setExplanations] = useState<Record<number, string>>({});
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [loadingExplanations, setLoadingExplanations] = useState<Set<number>>(
    new Set()
  );
  const [selectedForComparison, setSelectedForComparison] = useState<
    Set<number>
  >(new Set());
  const [showCompareDialog, setShowCompareDialog] = useState(false);
  const pageSize = 50;

  const { data: allArticles = [], isLoading } = useQuery({
    queryKey: ["articles", "all", 1000, 30],
    queryFn: () => getArticles({ limit: 1000, days_back: 30 }), // Show articles from last 30 days
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

  const fullUpdateMutation = useMutation({
    mutationFn: runFullUpdate,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["articles"] });
      queryClient.invalidateQueries({ queryKey: ["newspaper"] });
      queryClient.invalidateQueries({ queryKey: ["newspapers"] });
      alert(
        `Update completed!\n\n` +
          `• ${data.new_articles} new articles fetched\n` +
          `• ${data.processed_articles} articles processed\n` +
          `• ${data.archived_articles} articles archived\n` +
          `• ${data.today_count} articles on Today page\n` +
          `• ${data.category_count} categories updated`
      );
    },
    onError: (error) => {
      alert(
        `Update failed: ${
          error instanceof Error ? error.message : "Unknown error"
        }`
      );
    },
  });

  const downvoteMutation = useMutation({
    mutationFn: (articleId: number) => downvoteArticle(articleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["articles"] });
    },
  });

  const handleReprocess = (articleId: number, title: string) => {
    if (confirm(`Recalculate LLM analysis for "${title}"?`)) {
      setProcessingArticleIds((prev) => new Set(prev).add(articleId));
      reprocessMutation.mutate(articleId);
    }
  };

  const handleDownvote = (
    articleId: number,
    isDownvoted: boolean,
    title: string
  ) => {
    if (
      confirm(
        isDownvoted
          ? `Remove downvote from "${title}"?`
          : `Downvote "${title}"? Future similar articles will be scored lower.`
      )
    ) {
      downvoteMutation.mutate(articleId);
    }
  };

  const handleExplain = async (articleId: number) => {
    if (explanations[articleId]) {
      // Toggle off
      setExplanations((prev) => {
        const next = { ...prev };
        delete next[articleId];
        return next;
      });
      return;
    }

    setLoadingExplanations((prev) => new Set(prev).add(articleId));
    try {
      const result = await explainScoreAdjustment(articleId);
      setExplanations((prev) => ({ ...prev, [articleId]: result.explanation }));
    } catch (error) {
      console.error("Failed to load explanation:", error);
      setExplanations((prev) => ({
        ...prev,
        [articleId]: "Failed to load explanation. Please try again.",
      }));
    } finally {
      setLoadingExplanations((prev) => {
        const next = new Set(prev);
        next.delete(articleId);
        return next;
      });
    }
  };

  const toggleArticleSelection = (articleId: number) => {
    setSelectedForComparison((prev) => {
      const next = new Set(prev);
      if (next.has(articleId)) {
        next.delete(articleId);
      } else {
        next.add(articleId);
      }
      return next;
    });
  };

  const clearSelection = () => {
    setSelectedForComparison(new Set());
  };

  const openCompare = () => {
    if (selectedForComparison.size >= 2) {
      setShowCompareDialog(true);
    }
  };

  const getComparisonArticles = () => {
    return allArticles.filter((a) => selectedForComparison.has(a.id));
  };

  const cosineSimilarity = (emb1: number[], emb2: number[]): number => {
    if (!emb1 || !emb2 || emb1.length !== emb2.length) return 0;
    const dotProduct = emb1.reduce((sum, val, i) => sum + val * emb2[i], 0);
    const mag1 = Math.sqrt(emb1.reduce((sum, val) => sum + val * val, 0));
    const mag2 = Math.sqrt(emb2.reduce((sum, val) => sum + val * val, 0));
    if (mag1 === 0 || mag2 === 0) return 0;
    return dotProduct / (mag1 * mag2);
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
      <div className="flex items-center gap-3 flex-wrap">
        <button
          onClick={() => {
            if (
              confirm(
                "This will:\n" +
                  "• Fetch new articles from all RSS feeds\n" +
                  "• Process new articles with AI\n" +
                  "• Regenerate today's newspaper\n\n" +
                  "Continue?"
              )
            ) {
              fullUpdateMutation.mutate();
            }
          }}
          disabled={fullUpdateMutation.isPending}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          title="Run full update: fetch feeds, process articles, regenerate newspaper"
        >
          <Newspaper
            className={`w-4 h-4 ${
              fullUpdateMutation.isPending ? "animate-pulse" : ""
            }`}
          />
          {fullUpdateMutation.isPending
            ? "Updating..."
            : "Update & Regenerate Today"}
        </button>
        {selectedForComparison.size > 0 && (
          <>
            <button
              onClick={openCompare}
              disabled={selectedForComparison.size < 2}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              title="Compare selected articles"
            >
              <GitCompare className="w-4 h-4" />
              Compare ({selectedForComparison.size})
            </button>
            <button
              onClick={clearSelection}
              className="px-4 py-2 border border-newspaper-300 hover:bg-newspaper-100 transition-colors"
            >
              Clear Selection
            </button>
          </>
        )}
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
              <th className="text-left p-3 text-sm font-semibold w-12">
                <input
                  type="checkbox"
                  checked={
                    selectedForComparison.size === paginatedArticles.length &&
                    paginatedArticles.length > 0
                  }
                  onChange={(e) => {
                    if (e.target.checked) {
                      setSelectedForComparison(
                        new Set(paginatedArticles.map((a) => a.id))
                      );
                    } else {
                      clearSelection();
                    }
                  }}
                  className="w-4 h-4 cursor-pointer"
                  title="Select all"
                />
              </th>
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
                    <input
                      type="checkbox"
                      checked={selectedForComparison.has(article.id)}
                      onChange={() => toggleArticleSelection(article.id)}
                      className="w-4 h-4 cursor-pointer"
                      onClick={(e) => e.stopPropagation()}
                    />
                  </td>
                  <td className="p-3">
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
                    {article.summary &&
                      (() => {
                        const hasAdjustment =
                          article.adjusted_relevance_score !== null &&
                          article.adjusted_relevance_score !==
                            article.relevance_score;
                        const displayScore = hasAdjustment
                          ? article.adjusted_relevance_score!
                          : article.relevance_score;
                        return (
                          <div className="text-sm space-y-1">
                            {hasAdjustment ? (
                              <div className="flex items-center gap-1 flex-wrap">
                                <span className="text-gray-400 line-through text-xs">
                                  {(article.relevance_score * 100).toFixed(0)}%
                                </span>
                                <span className="font-semibold text-orange-600">
                                  {(displayScore * 100).toFixed(0)}%
                                </span>
                                <button
                                  onClick={() => handleExplain(article.id)}
                                  className="text-blue-600 hover:text-blue-800 disabled:opacity-50"
                                  title="Explain adjustment"
                                  disabled={loadingExplanations.has(article.id)}
                                >
                                  {loadingExplanations.has(article.id) ? (
                                    "..."
                                  ) : (
                                    <Info className="w-3 h-3" />
                                  )}
                                </button>
                              </div>
                            ) : (
                              <div className="font-semibold">
                                {(displayScore * 100).toFixed(0)}%
                              </div>
                            )}
                            <div className="w-16 h-2 bg-newspaper-200">
                              <div
                                className="h-full bg-blue-600"
                                style={{
                                  width: `${displayScore * 100}%`,
                                }}
                              />
                            </div>
                          </div>
                        );
                      })()}
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
                      <button
                        onClick={() =>
                          handleDownvote(
                            article.id,
                            article.user_vote === -1,
                            article.llm_title || article.title
                          )
                        }
                        disabled={downvoteMutation.isPending}
                        className={`p-2 rounded transition-colors disabled:opacity-50 ${
                          article.user_vote === -1
                            ? "text-red-600 hover:bg-red-50"
                            : "text-gray-600 hover:bg-gray-100"
                        }`}
                        title={
                          article.user_vote === -1
                            ? "Remove downvote"
                            : "Downvote (less like this)"
                        }
                      >
                        <ThumbsDown
                          className={`w-4 h-4 ${
                            article.user_vote === -1 ? "fill-current" : ""
                          }`}
                        />
                      </button>
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
            {paginatedArticles.map((article) => {
              if (!explanations[article.id]) return null;
              return (
                <tr key={`explanation-${article.id}`}>
                  <td
                    colSpan={7}
                    className="p-3 bg-blue-50 border-t border-blue-200"
                  >
                    <div className="text-sm">
                      <p className="font-semibold text-blue-900 mb-1">
                        Why was the score adjusted?
                      </p>
                      <p className="text-blue-800">
                        {explanations[article.id]}
                      </p>
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
                </div>

                {/* Score and Published */}
                <div className="flex items-center justify-between text-xs text-newspaper-600">
                  <div>
                    {article.summary &&
                      (() => {
                        const hasAdjustment =
                          article.adjusted_relevance_score !== null &&
                          article.adjusted_relevance_score !==
                            article.relevance_score;
                        const displayScore = hasAdjustment
                          ? article.adjusted_relevance_score!
                          : article.relevance_score;
                        return (
                          <div className="flex items-center gap-1">
                            {hasAdjustment ? (
                              <>
                                <span className="text-gray-400 line-through">
                                  {(article.relevance_score * 100).toFixed(0)}%
                                </span>
                                <span className="font-semibold text-orange-600">
                                  {(displayScore * 100).toFixed(0)}%
                                </span>
                                <button
                                  onClick={() => handleExplain(article.id)}
                                  className="text-blue-600 hover:text-blue-800"
                                  title="Explain adjustment"
                                >
                                  <Info className="w-3 h-3" />
                                </button>
                              </>
                            ) : (
                              <span className="font-semibold">
                                Score: {(displayScore * 100).toFixed(0)}%
                              </span>
                            )}
                          </div>
                        );
                      })()}
                  </div>
                  <div>
                    {article.published_date
                      ? formatDistanceToNow(new Date(article.published_date), {
                          addSuffix: true,
                        })
                      : "Unknown"}
                  </div>
                </div>

                {/* Explanation */}
                {explanations[article.id] && (
                  <div className="p-3 bg-blue-50 border border-blue-200 rounded text-sm">
                    <p className="font-semibold text-blue-900 mb-1">
                      Why was the score adjusted?
                    </p>
                    <p className="text-blue-800">{explanations[article.id]}</p>
                  </div>
                )}

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
                  <button
                    onClick={() =>
                      handleDownvote(
                        article.id,
                        article.user_vote === -1,
                        article.llm_title || article.title
                      )
                    }
                    disabled={downvoteMutation.isPending}
                    className={`inline-flex items-center gap-1 text-xs disabled:opacity-50 ${
                      article.user_vote === -1
                        ? "text-red-600 hover:text-red-800"
                        : "text-gray-600 hover:text-gray-800"
                    }`}
                    title={
                      article.user_vote === -1 ? "Remove downvote" : "Downvote"
                    }
                  >
                    <ThumbsDown
                      className={`w-3 h-3 ${
                        article.user_vote === -1 ? "fill-current" : ""
                      }`}
                    />
                    {article.user_vote === -1 ? "Downvoted" : "Downvote"}
                  </button>
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
      <RelatedArticlesDialog
        isOpen={showRelatedDialog && selectedArticleId !== null}
        onClose={() => {
          setShowRelatedDialog(false);
          setSelectedArticleId(null);
        }}
        relatedArticles={relatedArticles}
        isLoading={loadingRelated}
        onArticleClick={(article) => window.open(article.link, "_blank")}
        getCategoryName={getCategoryName}
      />

      {/* Compare Articles Dialog */}
      {showCompareDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white max-w-6xl w-full max-h-[90vh] overflow-y-auto border-2 border-newspaper-900">
            <div className="sticky top-0 bg-white border-b-2 border-newspaper-900 p-6 z-10">
              <div className="flex items-center justify-between">
                <h2 className="newspaper-heading text-2xl">
                  Compare Articles ({selectedForComparison.size})
                </h2>
                <button
                  onClick={() => setShowCompareDialog(false)}
                  className="text-2xl font-bold hover:text-newspaper-700"
                >
                  ×
                </button>
              </div>
            </div>

            <div className="p-6 space-y-6">
              {/* Comparison Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {getComparisonArticles().map((article) => {
                  const hasAdjustment =
                    article.adjusted_relevance_score !== null &&
                    article.adjusted_relevance_score !==
                      article.relevance_score;
                  const displayScore = hasAdjustment
                    ? article.adjusted_relevance_score!
                    : article.relevance_score;
                  const embedding = article.title_embedding
                    ? JSON.parse(article.title_embedding)
                    : null;

                  return (
                    <div
                      key={article.id}
                      className="border-2 border-newspaper-300 p-4 bg-newspaper-50"
                    >
                      <h3 className="newspaper-heading text-lg mb-3 border-b border-newspaper-400 pb-2">
                        {article.llm_title || article.title}
                      </h3>

                      <div className="space-y-2 text-sm">
                        <div>
                          <span className="font-semibold">ID:</span>{" "}
                          {article.id}
                        </div>
                        <div>
                          <span className="font-semibold">Source:</span>{" "}
                          {article.feed_source_title || "Unknown"}
                        </div>
                        <div>
                          <span className="font-semibold">Category:</span>{" "}
                          {getCategoryName(article.category_id) || "None"}
                        </div>
                        <div>
                          <span className="font-semibold">Original Score:</span>{" "}
                          <span
                            className={
                              hasAdjustment ? "line-through text-gray-400" : ""
                            }
                          >
                            {article.relevance_score?.toFixed(3) || "N/A"}
                          </span>
                        </div>
                        {hasAdjustment && (
                          <div>
                            <span className="font-semibold">
                              Adjusted Score:
                            </span>{" "}
                            <span className="text-orange-600 font-semibold">
                              {displayScore?.toFixed(3)}
                            </span>
                          </div>
                        )}
                        <div>
                          <span className="font-semibold">User Vote:</span>{" "}
                          {article.user_vote === -1 ? (
                            <span className="text-red-600 font-semibold">
                              Downvoted
                            </span>
                          ) : (
                            <span className="text-gray-500">Neutral</span>
                          )}
                        </div>
                        <div>
                          <span className="font-semibold">Is Duplicate:</span>{" "}
                          {article.is_duplicate ? "Yes" : "No"}
                        </div>
                        <div>
                          <span className="font-semibold">Has Embedding:</span>{" "}
                          {embedding ? `Yes (${embedding.length}D)` : "No"}
                        </div>
                        {article.score_adjustment_reason && (
                          <div className="mt-2 pt-2 border-t border-newspaper-300">
                            <span className="font-semibold">
                              Adjustment Reason:
                            </span>
                            <p className="text-xs mt-1 text-newspaper-600">
                              {article.score_adjustment_reason}
                            </p>
                          </div>
                        )}
                      </div>

                      <a
                        href={article.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 mt-3 text-xs font-semibold text-blue-600 hover:text-blue-800"
                      >
                        <ExternalLink className="w-3 h-3" />
                        View Article
                      </a>
                    </div>
                  );
                })}
              </div>

              {/* Similarity Matrix */}
              {getComparisonArticles().every((a) => a.title_embedding) && (
                <div className="mt-6 border-t-2 border-newspaper-900 pt-6">
                  <h3 className="newspaper-heading text-xl mb-4">
                    Embedding Similarity Matrix
                  </h3>
                  <div className="overflow-x-auto">
                    <table className="w-full border border-newspaper-300 text-sm">
                      <thead className="bg-newspaper-100">
                        <tr>
                          <th className="border border-newspaper-300 p-2 text-left">
                            Article
                          </th>
                          {getComparisonArticles().map((article) => (
                            <th
                              key={article.id}
                              className="border border-newspaper-300 p-2 text-center"
                            >
                              #{article.id}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {getComparisonArticles().map((article1) => {
                          const emb1 = JSON.parse(article1.title_embedding!);
                          return (
                            <tr key={article1.id}>
                              <td className="border border-newspaper-300 p-2 font-semibold bg-newspaper-50">
                                #{article1.id}
                              </td>
                              {getComparisonArticles().map((article2) => {
                                const emb2 = JSON.parse(
                                  article2.title_embedding!
                                );
                                const similarity = cosineSimilarity(emb1, emb2);
                                const isHigh =
                                  similarity > 0.8 &&
                                  article1.id !== article2.id;
                                const isSelf = article1.id === article2.id;

                                return (
                                  <td
                                    key={article2.id}
                                    className={`border border-newspaper-300 p-2 text-center ${
                                      isSelf
                                        ? "bg-gray-200 font-semibold"
                                        : isHigh
                                        ? "bg-red-100 font-semibold"
                                        : similarity > 0.6
                                        ? "bg-yellow-100"
                                        : ""
                                    }`}
                                  >
                                    {similarity.toFixed(3)}
                                  </td>
                                );
                              })}
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                    <p className="text-xs text-newspaper-600 mt-2">
                      <span className="font-semibold">Legend:</span>{" "}
                      <span className="inline-block w-4 h-4 bg-red-100 border border-newspaper-300 align-middle"></span>{" "}
                      High similarity ({">"} 0.8) •{" "}
                      <span className="inline-block w-4 h-4 bg-yellow-100 border border-newspaper-300 align-middle"></span>{" "}
                      Medium similarity ({">"} 0.6)
                    </p>
                  </div>
                </div>
              )}

              {/* Close Button */}
              <div className="flex justify-end pt-4 border-t border-newspaper-300">
                <button
                  onClick={() => setShowCompareDialog(false)}
                  className="px-6 py-2 bg-newspaper-900 text-white hover:bg-newspaper-700 transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
