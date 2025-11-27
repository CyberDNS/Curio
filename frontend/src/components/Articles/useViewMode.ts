import { useState, useEffect, useCallback } from "react";

export type ViewMode = "grid" | "list";

const STORAGE_KEY = "article-view-mode";

/**
 * Hook for managing article view mode preference (grid vs list)
 * Persists the preference to localStorage
 */
export function useViewMode(defaultMode: ViewMode = "grid") {
  const [viewMode, setViewMode] = useState<ViewMode>(() => {
    // Try to load from localStorage on initial render
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored === "grid" || stored === "list") {
        return stored;
      }
    }
    return defaultMode;
  });

  // Persist to localStorage when changed
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, viewMode);
  }, [viewMode]);

  const toggleViewMode = useCallback(() => {
    setViewMode((prev) => (prev === "grid" ? "list" : "grid"));
  }, []);

  return {
    viewMode,
    setViewMode,
    toggleViewMode,
    isGrid: viewMode === "grid",
    isList: viewMode === "list",
  };
}
