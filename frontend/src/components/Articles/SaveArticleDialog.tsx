import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { X, Bookmark, Tag as TagIcon, Loader2 } from "lucide-react";
import { saveArticle, getTags } from "../../services/api";
import type { Tag } from "../../types";

interface SaveArticleDialogProps {
  articleId: number;
  articleTitle: string;
  onClose: () => void;
  onSuccess?: () => void;
}

export default function SaveArticleDialog({
  articleId,
  articleTitle,
  onClose,
  onSuccess,
}: SaveArticleDialogProps) {
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState("");
  const [showSuggestions, setShowSuggestions] = useState(false);

  const queryClient = useQueryClient();

  // Fetch existing tags for autocomplete
  const { data: existingTags = [] } = useQuery<Tag[]>({
    queryKey: ["tags"],
    queryFn: () => getTags(),
  });

  // Filter tags based on input
  const filteredTags = existingTags.filter(
    (tag) =>
      tag.name.toLowerCase().includes(tagInput.toLowerCase()) &&
      !selectedTags.includes(tag.name)
  );

  const saveMutation = useMutation({
    mutationFn: () =>
      saveArticle({
        article_id: articleId,
        tag_names: selectedTags,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["savedArticles"] });
      queryClient.invalidateQueries({ queryKey: ["tags"] });
      if (onSuccess) onSuccess();
      onClose();
    },
  });

  const handleAddTag = (tagName: string) => {
    const normalizedTag = tagName.trim().toLowerCase();
    if (normalizedTag && !selectedTags.includes(normalizedTag)) {
      setSelectedTags([...selectedTags, normalizedTag]);
      setTagInput("");
      setShowSuggestions(false);
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setSelectedTags(selectedTags.filter((tag) => tag !== tagToRemove));
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && tagInput.trim()) {
      e.preventDefault();
      handleAddTag(tagInput);
    } else if (e.key === "Backspace" && !tagInput && selectedTags.length > 0) {
      // Remove last tag if backspace is pressed with empty input
      handleRemoveTag(selectedTags[selectedTags.length - 1]);
    }
  };

  const handleSave = () => {
    saveMutation.mutate();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4 overflow-hidden">
        {/* Header */}
        <div className="flex items-start justify-between p-6 border-b border-gray-200">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <Bookmark className="w-5 h-5 text-blue-600" />
              <h2 className="text-xl font-bold text-gray-900">Save Article</h2>
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
        <div className="p-6 space-y-4">
          {/* Tag Input */}
          <div>
            <label className="block text-sm font-semibold text-gray-900 mb-2">
              Add Tags (Optional)
            </label>
            <div className="relative">
              {/* Selected Tags + Input */}
              <div className="flex flex-wrap gap-2 p-2 border border-gray-300 rounded-lg focus-within:border-blue-500 focus-within:ring-2 focus-within:ring-blue-500 focus-within:ring-opacity-20 min-h-[42px]">
                {selectedTags.map((tag) => (
                  <span
                    key={tag}
                    className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-800 text-sm rounded-full"
                  >
                    <TagIcon className="w-3 h-3" />
                    {tag}
                    <button
                      onClick={() => handleRemoveTag(tag)}
                      className="hover:text-blue-900"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
                <input
                  type="text"
                  value={tagInput}
                  onChange={(e) => {
                    setTagInput(e.target.value);
                    setShowSuggestions(true);
                  }}
                  onKeyDown={handleKeyDown}
                  onFocus={() => setShowSuggestions(true)}
                  placeholder={
                    selectedTags.length === 0
                      ? "Type a tag and press Enter..."
                      : ""
                  }
                  className="flex-1 min-w-[120px] outline-none text-sm"
                />
              </div>

              {/* Tag Suggestions */}
              {showSuggestions && tagInput && filteredTags.length > 0 && (
                <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-48 overflow-y-auto">
                  {filteredTags.slice(0, 10).map((tag) => (
                    <button
                      key={tag.id}
                      onClick={() => handleAddTag(tag.name)}
                      className="w-full text-left px-4 py-2 hover:bg-blue-50 flex items-center justify-between text-sm"
                    >
                      <span className="flex items-center gap-2">
                        <TagIcon className="w-3 h-3 text-gray-400" />
                        {tag.name}
                      </span>
                      {tag.usage_count !== undefined && tag.usage_count > 0 && (
                        <span className="text-xs text-gray-500">
                          {tag.usage_count}
                        </span>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <p className="mt-1 text-xs text-gray-500">
              Press Enter to add a tag. Click X to remove.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200 bg-gray-50">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-200 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saveMutation.isPending}
            className="px-4 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {saveMutation.isPending ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Bookmark className="w-4 h-4" />
                Save Article
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
