import type { ReactNode } from "react";

interface ArticleListProps {
  children: ReactNode;
  className?: string;
}

/**
 * Container component for list view layout
 * Renders children in a vertical stack with spacing
 */
export default function ArticleList({
  children,
  className = "",
}: ArticleListProps) {
  return (
    <div className={`space-y-3 sm:space-y-4 ${className}`}>{children}</div>
  );
}
