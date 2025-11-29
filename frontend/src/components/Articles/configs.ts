import type { ArticleDisplayConfig } from "./types";

/**
 * Default configuration for reader views (Today, Categories, Saved)
 * Shows all relevant information for reading/consuming articles
 */
export const READER_CONFIG: ArticleDisplayConfig = {
  showImage: true,
  showScore: true,
  showSummary: true,
  showSubtitle: true,
  showMeta: {
    source: true,
    author: true,
    date: true,
    category: false,
    unreadBadge: true,
    recommendedBadge: true,
  },
  showActions: {
    read: true,
    save: true,
    share: true,
    downvote: true,
    reprocess: true,
    related: true,
  },
  summaryLines: 3,
};

/**
 * Configuration for saved articles view
 * Similar to reader but with category visible
 */
export const SAVED_CONFIG: ArticleDisplayConfig = {
  ...READER_CONFIG,
  showMeta: {
    ...READER_CONFIG.showMeta,
    category: true,
    unreadBadge: false,
  },
};

/**
 * Configuration for admin/management views (All Articles)
 * More compact, focused on management actions
 */
export const ADMIN_CONFIG: ArticleDisplayConfig = {
  showImage: true,
  showScore: true,
  showSummary: false,
  showSubtitle: false,
  showMeta: {
    source: true,
    author: false,
    date: true,
    category: true,
    unreadBadge: false,
    recommendedBadge: false,
  },
  showActions: {
    read: true,
    save: false,
    share: false,
    downvote: false,
    reprocess: false,
    related: false,
  },
  summaryLines: 2,
};

/**
 * Compact configuration for related articles or small displays
 */
export const COMPACT_CONFIG: ArticleDisplayConfig = {
  showImage: true,
  showScore: false,
  showSummary: true,
  showSubtitle: false,
  showMeta: {
    source: true,
    author: false,
    date: true,
    category: false,
    unreadBadge: false,
    recommendedBadge: false,
  },
  showActions: {
    read: true,
    save: false,
    share: true,
    downvote: false,
    reprocess: false,
    related: false,
  },
  summaryLines: 2,
};

/**
 * Merge a partial config with defaults
 */
export function mergeConfig(
  base: ArticleDisplayConfig,
  overrides?: Partial<ArticleDisplayConfig>
): ArticleDisplayConfig {
  if (!overrides) return base;

  return {
    ...base,
    ...overrides,
    showMeta: {
      ...base.showMeta,
      ...overrides.showMeta,
    },
    showActions: {
      ...base.showActions,
      ...overrides.showActions,
    },
  };
}
