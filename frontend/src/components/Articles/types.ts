import type { Article } from "../../types";

/**
 * Configuration for what parts of an article to display
 */
export interface ArticleDisplayConfig {
  showImage?: boolean;
  showScore?: boolean;
  showSummary?: boolean;
  showSubtitle?: boolean;
  showMeta?: {
    source?: boolean;
    author?: boolean;
    date?: boolean;
    category?: boolean;
    unreadBadge?: boolean;
    recommendedBadge?: boolean;
  };
  showActions?: {
    read?: boolean;
    save?: boolean;
    share?: boolean;
    downvote?: boolean;
    reprocess?: boolean;
    related?: boolean;
  };
  summaryLines?: 2 | 3 | 4 | "full";
}

/**
 * Size variants for card-style display
 */
export type ArticleCardSize = "hero" | "large" | "medium" | "small";

/**
 * Common props passed to sub-components
 */
export interface ArticleSubComponentProps {
  article: Article;
  size?: ArticleCardSize;
  className?: string;
}

/**
 * Props for the main ArticleCard component
 */
export interface ArticleCardProps {
  article: Article;
  size?: ArticleCardSize;
  config?: ArticleDisplayConfig;
  onArticleClick?: (article: Article) => void;
  categoryName?: string | null;
}

/**
 * Props for the ArticleListItem component
 */
export interface ArticleListItemProps {
  article: Article;
  config?: ArticleDisplayConfig;
  onArticleClick?: (article: Article) => void;
  categoryName?: string | null;
}

/**
 * Size-specific style configuration
 */
export interface SizeStyles {
  container: string;
  imageContainer: string;
  contentPadding: string;
  title: string;
  subtitle: string;
  summary: string;
  meta: string;
}

/**
 * Get size-specific styles for article cards
 */
export function getSizeStyles(size: ArticleCardSize): SizeStyles {
  switch (size) {
    case "hero":
      return {
        container: "border-b-4 border-newspaper-900",
        imageContainer: "w-full h-48 sm:h-64 md:h-96",
        contentPadding: "p-4 sm:p-6",
        title:
          "newspaper-heading text-2xl sm:text-4xl md:text-6xl leading-tight mb-2 sm:mb-3",
        subtitle: "text-base sm:text-xl italic mb-2 sm:mb-4",
        summary: "text-base sm:text-lg leading-relaxed mb-2 sm:mb-4",
        meta: "text-sm sm:text-base",
      };
    case "large":
      return {
        container: "border-b-2 border-newspaper-900",
        imageContainer: "w-full h-40 sm:h-52 md:h-64",
        contentPadding: "p-3 sm:p-4",
        title:
          "newspaper-heading text-xl sm:text-2xl md:text-3xl leading-tight mb-2",
        subtitle: "text-sm sm:text-base italic mb-2 sm:mb-3",
        summary: "text-sm sm:text-base leading-relaxed mb-2 sm:mb-3",
        meta: "text-xs sm:text-sm",
      };
    case "medium":
      return {
        container: "border-b border-newspaper-400",
        imageContainer: "w-full h-32 sm:h-40 md:h-48",
        contentPadding: "p-2 sm:p-3",
        title:
          "newspaper-heading text-lg sm:text-xl md:text-2xl leading-tight mb-1 sm:mb-2",
        subtitle: "text-xs sm:text-sm italic mb-1 sm:mb-2",
        summary: "text-xs sm:text-sm leading-relaxed mb-1 sm:mb-2 line-clamp-3",
        meta: "text-xs",
      };
    case "small":
      return {
        container: "border-b border-newspaper-300",
        imageContainer: "w-full h-24 sm:h-28 md:h-32",
        contentPadding: "p-2",
        title:
          "newspaper-heading text-base sm:text-lg md:text-xl leading-tight mb-1",
        subtitle: "text-xs italic mb-1",
        summary: "text-xs leading-relaxed mb-1 line-clamp-2",
        meta: "text-xs",
      };
  }
}
