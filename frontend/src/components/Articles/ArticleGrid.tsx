import type { ReactNode } from "react";
import type { ArticleCardSize } from "./types";

interface ArticleGridProps {
  children: ReactNode;
  className?: string;
}

/**
 * Container component for grid view layout
 * Responsive CSS grid that adapts to screen size
 */
export default function ArticleGrid({
  children,
  className = "",
}: ArticleGridProps) {
  return (
    <div
      className={`grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 sm:gap-6 ${className}`}
    >
      {children}
    </div>
  );
}

/**
 * Props for newspaper-style grid with mixed sizes
 */
interface NewspaperGridProps {
  children: ReactNode;
  className?: string;
}

/**
 * Newspaper-style grid that supports mixed article sizes
 * Uses CSS Grid with dense auto-flow for optimal packing
 */
export function NewspaperGrid({
  children,
  className = "",
}: NewspaperGridProps) {
  return (
    <>
      <style>
        {`
          .newspaper-grid {
            display: grid;
            grid-template-columns: repeat(1, 1fr);
            gap: 1.5rem;
            overflow-x: hidden;
            width: 100%;
          }
          
          .newspaper-grid > * {
            min-width: 0;
            overflow: hidden;
          }
          
          @media (min-width: 640px) {
            .newspaper-grid {
              grid-template-columns: repeat(2, 1fr);
            }
            .newspaper-grid .article-hero {
              grid-column: span 2;
            }
            .newspaper-grid .article-large {
              grid-column: span 2;
            }
          }
          
          @media (min-width: 1024px) {
            .newspaper-grid {
              grid-template-columns: repeat(4, 1fr);
              grid-auto-flow: dense;
            }
            .newspaper-grid .article-hero {
              grid-column: span 4;
            }
            .newspaper-grid .article-large {
              grid-column: span 2;
            }
            .newspaper-grid .article-medium {
              grid-column: span 1;
            }
            .newspaper-grid .article-small {
              grid-column: span 1;
            }
          }
        `}
      </style>
      <div className={`newspaper-grid ${className}`}>{children}</div>
    </>
  );
}

/**
 * Wrapper to apply the correct grid class based on article size
 */
interface ArticleGridItemProps {
  size: ArticleCardSize;
  children: ReactNode;
}

export function ArticleGridItem({ size, children }: ArticleGridItemProps) {
  return <div className={`article-${size}`}>{children}</div>;
}
