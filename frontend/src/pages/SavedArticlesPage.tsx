import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getSavedArticles,
  getTags,
  updateSavedArticleTags,
} from "../services/api";
import {
  Bookmark,
  Tag as TagIcon,
  Loader2,
  X,
  Edit2,
  Check,
} from "lucide-react";
import {
  ArticleCard,
  ArticleListItem,
  ArticleGrid,
  ArticleList,
  ArticleViewToggle,
  useViewMode,
  SAVED_CONFIG,
} from "../components/Articles";
import PageHeader from "../components/Layout/PageHeader";
import type { SavedArticleWithArticle, Tag } from "../types";

export default function SavedArticlesPage() {
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [editingTags, setEditingTags] = useState<number | null>(null);
  const [tagInput, setTagInput] = useState("");
  const [editTagNames, setEditTagNames] = useState<string[]>([]);
  const { viewMode, toggleViewMode } = useViewMode("list");

  const queryClient = useQueryClient();

  // Fetch saved articles
  const { data: savedArticles = [], isLoading } = useQuery<
    SavedArticleWithArticle[]
  >({
    queryKey: ["savedArticles", selectedTags],
    queryFn: () =>
      getSavedArticles({
        tags: selectedTags.length > 0 ? selectedTags : undefined,
      }),
  });

  // Fetch all tags for filtering
  const { data: allTags = [] } = useQuery<Tag[]>({
    queryKey: ["tags"],
    queryFn: () => getTags(),
  });

  // Update tags mutation
  const updateTagsMutation = useMutation({
    mutationFn: ({ id, tagNames }: { id: number; tagNames: string[] }) =>
      updateSavedArticleTags(id, { tag_names: tagNames }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["savedArticles"] });
      queryClient.invalidateQueries({ queryKey: ["tags"] });
      setEditingTags(null);
    },
  });

  const handleToggleTag = (tagName: string) => {
    setSelectedTags((prev) =>
      prev.includes(tagName)
        ? prev.filter((t) => t !== tagName)
        : [...prev, tagName]
    );
  };

  const handleStartEditTags = (savedArticle: SavedArticleWithArticle) => {
    setEditingTags(savedArticle.id);
    setEditTagNames(savedArticle.tags.map((t) => t.name));
    setTagInput("");
  };

  const handleCancelEditTags = () => {
    setEditingTags(null);
    setEditTagNames([]);
    setTagInput("");
  };

  const handleSaveTags = (savedArticleId: number) => {
    updateTagsMutation.mutate({
      id: savedArticleId,
      tagNames: editTagNames,
    });
  };

  const handleAddEditTag = (tagName: string) => {
    const normalizedTag = tagName.trim().toLowerCase();
    if (normalizedTag && !editTagNames.includes(normalizedTag)) {
      setEditTagNames([...editTagNames, normalizedTag]);
      setTagInput("");
    }
  };

  const handleRemoveEditTag = (tagToRemove: string) => {
    setEditTagNames(editTagNames.filter((tag) => tag !== tagToRemove));
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && tagInput.trim()) {
      e.preventDefault();
      handleAddEditTag(tagInput);
    }
  };

  // Filter tags for autocomplete
  const filteredTagSuggestions = allTags.filter(
    (tag) =>
      tag.name.toLowerCase().includes(tagInput.toLowerCase()) &&
      !editTagNames.includes(tag.name)
  );

  // Render tags section for a saved article
  const renderTagsSection = (savedArticle: SavedArticleWithArticle) => (
    <div className="px-4 py-3 border-t border-gray-200 bg-gray-50">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          {editingTags === savedArticle.id ? (
            <div className="space-y-2">
              {/* Edit Tags Input */}
              <div className="flex flex-wrap gap-2 p-2 border border-gray-300 rounded-lg bg-white">
                {editTagNames.map((tag) => (
                  <span
                    key={tag}
                    className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-800 text-sm rounded-full"
                  >
                    <TagIcon className="w-3 h-3" />
                    {tag}
                    <button
                      onClick={() => handleRemoveEditTag(tag)}
                      className="hover:text-blue-900"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
                <input
                  type="text"
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Add tag..."
                  className="flex-1 min-w-[100px] outline-none text-sm"
                  autoFocus
                />
              </div>

              {/* Tag Suggestions */}
              {tagInput && filteredTagSuggestions.length > 0 && (
                <div className="bg-white border border-gray-300 rounded-lg shadow-lg max-h-32 overflow-y-auto">
                  {filteredTagSuggestions.slice(0, 5).map((tag) => (
                    <button
                      key={tag.id}
                      onClick={() => handleAddEditTag(tag.name)}
                      className="w-full text-left px-3 py-1 hover:bg-blue-50 text-sm"
                    >
                      {tag.name}
                    </button>
                  ))}
                </div>
              )}

              {/* Save/Cancel Buttons */}
              <div className="flex gap-2">
                <button
                  onClick={() => handleSaveTags(savedArticle.id)}
                  disabled={updateTagsMutation.isPending}
                  className="px-3 py-1 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded transition-colors flex items-center gap-1"
                >
                  <Check className="w-3 h-3" />
                  Save
                </button>
                <button
                  onClick={handleCancelEditTags}
                  className="px-3 py-1 text-xs font-semibold text-gray-700 hover:bg-gray-200 rounded transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs text-gray-600 flex items-center gap-1">
                <TagIcon className="w-3 h-3" />
                Tags:
              </span>
              {savedArticle.tags.length > 0 ? (
                savedArticle.tags.map((tag) => (
                  <span
                    key={tag.id}
                    className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full"
                  >
                    {tag.name}
                  </span>
                ))
              ) : (
                <span className="text-xs text-gray-400 italic">No tags</span>
              )}
            </div>
          )}
        </div>

        {editingTags !== savedArticle.id && (
          <button
            onClick={() => handleStartEditTags(savedArticle)}
            className="ml-4 p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-200 rounded transition-colors"
            title="Edit tags"
          >
            <Edit2 className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-newspaper-100">
      <PageHeader
        title="Saved Articles"
        subtitle="Your bookmarked articles for later reading"
        actions={
          <ArticleViewToggle viewMode={viewMode} onToggle={toggleViewMode} />
        }
      />

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Tag Filter */}
        {allTags.length > 0 && (
          <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <TagIcon className="w-4 h-4" />
              Filter by Tags
            </h3>
            <div className="flex flex-wrap gap-2">
              {allTags.map((tag) => (
                <button
                  key={tag.id}
                  onClick={() => handleToggleTag(tag.name)}
                  className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                    selectedTags.includes(tag.name)
                      ? "bg-blue-600 text-white"
                      : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                  }`}
                >
                  {tag.name}
                  {tag.usage_count !== undefined && tag.usage_count > 0 && (
                    <span className="ml-1 opacity-75">({tag.usage_count})</span>
                  )}
                </button>
              ))}
            </div>
            {selectedTags.length > 0 && (
              <button
                onClick={() => setSelectedTags([])}
                className="mt-2 text-xs text-gray-600 hover:text-gray-800 underline"
              >
                Clear filters
              </button>
            )}
          </div>
        )}

        {/* Loading State */}
        {isLoading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
          </div>
        )}

        {/* Empty State */}
        {!isLoading && savedArticles.length === 0 && (
          <div className="bg-white rounded-lg shadow-sm p-12 text-center">
            <Bookmark className="w-16 h-16 mx-auto mb-4 text-gray-300" />
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              No saved articles yet
            </h3>
            <p className="text-gray-600">
              {selectedTags.length > 0
                ? "No articles found with the selected tags."
                : "Start saving articles by clicking the bookmark icon on any article."}
            </p>
          </div>
        )}

        {/* Saved Articles - Grid View */}
        {!isLoading && savedArticles.length > 0 && viewMode === "grid" && (
          <ArticleGrid>
            {savedArticles.map((savedArticle) => (
              <div
                key={savedArticle.id}
                className="bg-white rounded-lg shadow-sm overflow-hidden flex flex-col"
              >
                <div className="flex-1">
                  <ArticleCard
                    article={savedArticle.article}
                    size="medium"
                    config={SAVED_CONFIG}
                    autoMarkRead={false}
                  />
                </div>
                {renderTagsSection(savedArticle)}
              </div>
            ))}
          </ArticleGrid>
        )}

        {/* Saved Articles - List View */}
        {!isLoading && savedArticles.length > 0 && viewMode === "list" && (
          <ArticleList>
            {savedArticles.map((savedArticle) => (
              <div
                key={savedArticle.id}
                className="bg-white rounded-lg shadow-sm overflow-hidden"
              >
                <ArticleListItem
                  article={savedArticle.article}
                  config={SAVED_CONFIG}
                />
                {renderTagsSection(savedArticle)}
              </div>
            ))}
          </ArticleList>
        )}
      </div>
    </div>
  );
}
