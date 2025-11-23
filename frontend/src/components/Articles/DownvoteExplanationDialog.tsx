import { useQuery } from "@tanstack/react-query";
import { explainScoreAdjustment } from "../../services/api";
import { X, AlertTriangle, TrendingDown, Loader2 } from "lucide-react";
import type { ScoreAdjustmentExplanation } from "../../types";

interface DownvoteExplanationDialogProps {
  articleId: number;
  articleTitle: string;
  onClose: () => void;
}

export default function DownvoteExplanationDialog({
  articleId,
  articleTitle,
  onClose,
}: DownvoteExplanationDialogProps) {
  const { data, isLoading, error } = useQuery<ScoreAdjustmentExplanation>({
    queryKey: ["scoreAdjustment", articleId],
    queryFn: () => explainScoreAdjustment(articleId),
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-start justify-between p-6 border-b border-gray-200">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="w-5 h-5 text-orange-600" />
              <h2 className="text-xl font-bold text-gray-900">
                Score Adjustment Explanation
              </h2>
            </div>
            <p className="text-sm text-gray-600 line-clamp-2">{articleTitle}</p>
          </div>
          <button
            onClick={onClose}
            className="ml-4 p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
              Failed to load explanation. Please try again.
            </div>
          )}

          {data && (
            <>
              {!data.has_adjustment ? (
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-gray-700">
                  No score adjustment was applied to this article.
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Score Comparison */}
                  <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <TrendingDown className="w-5 h-5 text-orange-600" />
                      <h3 className="font-semibold text-gray-900">
                        Score Impact
                      </h3>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <div className="text-xs text-gray-600 mb-1">
                          Original Score
                        </div>
                        <div className="text-2xl font-bold text-gray-900">
                          {data.original_score?.toFixed(3)}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-gray-600 mb-1">
                          Adjusted Score
                        </div>
                        <div className="text-2xl font-bold text-orange-600">
                          {data.adjusted_score?.toFixed(3)}
                        </div>
                      </div>
                    </div>
                    {data.original_score &&
                      data.adjusted_score &&
                      data.original_score > 0 && (
                        <div className="mt-3 text-sm text-gray-700">
                          Score reduced by{" "}
                          <span className="font-semibold">
                            {(
                              ((data.original_score - data.adjusted_score) /
                                data.original_score) *
                              100
                            ).toFixed(1)}
                            %
                          </span>
                        </div>
                      )}
                  </div>

                  {/* Brief Reason */}
                  {data.brief_reason && (
                    <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                      <h3 className="font-semibold text-gray-900 mb-2">
                        Quick Summary
                      </h3>
                      <p className="text-sm text-gray-700">
                        {data.brief_reason}
                      </p>
                    </div>
                  )}

                  {/* Detailed Explanation */}
                  {data.explanation && (
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                      <h3 className="font-semibold text-gray-900 mb-2">
                        Why This Matters
                      </h3>
                      <div className="text-sm text-gray-700 whitespace-pre-wrap">
                        {data.explanation}
                      </div>
                    </div>
                  )}

                  {/* Key Similarity Points */}
                  {data.key_points && data.key_points.length > 0 && (
                    <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
                      <h3 className="font-semibold text-gray-900 mb-3">
                        Key Similarity Points
                      </h3>
                      <ul className="space-y-2">
                        {data.key_points.map((point: string, index: number) => (
                          <li key={index} className="flex items-start gap-2">
                            <span className="text-purple-600 mt-0.5">•</span>
                            <span className="text-sm text-gray-700">
                              {point}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Embedding Similarity Metrics */}
                  {data.similarity_score !== undefined && (
                    <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-4">
                      <h3 className="font-semibold text-gray-900 mb-2">
                        Similarity Metrics
                      </h3>
                      <div className="space-y-2">
                        <div className="flex justify-between items-center">
                          <span className="text-sm text-gray-700">
                            Embedding Similarity
                          </span>
                          <div className="flex items-center gap-2">
                            <div className="w-32 h-2 bg-gray-200 rounded-full overflow-hidden">
                              <div
                                className="h-full bg-indigo-600 transition-all"
                                style={{
                                  width: `${(
                                    data.similarity_score * 100
                                  ).toFixed(0)}%`,
                                }}
                              />
                            </div>
                            <span className="text-sm font-semibold text-indigo-600">
                              {(data.similarity_score * 100).toFixed(1)}%
                            </span>
                          </div>
                        </div>
                        {data.similar_article_title && (
                          <div className="mt-3 pt-3 border-t border-indigo-200">
                            <div className="text-xs text-gray-600 mb-1">
                              Most Similar Downvoted Article:
                            </div>
                            <div className="text-sm text-gray-900 font-medium">
                              {data.similar_article_title}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-gray-200 p-4 bg-gray-50">
          <button
            onClick={onClose}
            className="w-full px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors font-medium"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
