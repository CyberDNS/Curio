import { LayoutGrid, List } from "lucide-react";
import type { ViewMode } from "./useViewMode";

interface ArticleViewToggleProps {
  viewMode: ViewMode;
  onToggle: () => void;
  className?: string;
}

/**
 * Toggle button for switching between grid and list view modes
 */
export default function ArticleViewToggle({
  viewMode,
  onToggle,
  className = "",
}: ArticleViewToggleProps) {
  return (
    <div
      className={`inline-flex rounded-md border border-newspaper-300 ${className}`}
    >
      <button
        onClick={viewMode === "list" ? onToggle : undefined}
        className={`p-2 rounded-l-md transition-colors ${
          viewMode === "grid"
            ? "bg-newspaper-100 text-newspaper-900"
            : "bg-white text-newspaper-500 hover:text-newspaper-700 hover:bg-newspaper-50"
        }`}
        title="Grid view"
        aria-label="Grid view"
        aria-pressed={viewMode === "grid"}
      >
        <LayoutGrid className="w-4 h-4" />
      </button>
      <button
        onClick={viewMode === "grid" ? onToggle : undefined}
        className={`p-2 rounded-r-md border-l border-newspaper-300 transition-colors ${
          viewMode === "list"
            ? "bg-newspaper-100 text-newspaper-900"
            : "bg-white text-newspaper-500 hover:text-newspaper-700 hover:bg-newspaper-50"
        }`}
        title="List view"
        aria-label="List view"
        aria-pressed={viewMode === "list"}
      >
        <List className="w-4 h-4" />
      </button>
    </div>
  );
}
