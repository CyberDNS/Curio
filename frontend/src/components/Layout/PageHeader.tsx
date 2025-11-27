import type { ReactNode } from "react";

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  /** Optional actions (e.g., view toggle) to display on the right */
  actions?: ReactNode;
}

export default function PageHeader({
  title,
  subtitle,
  actions,
}: PageHeaderProps) {
  return (
    <div className="mb-4 border-b-4 border-double border-newspaper-900 pb-4">
      {/* Section Title Row */}
      <div className="flex items-center gap-3 mb-2">
        <div className="flex-grow border-t border-newspaper-400"></div>
        <h1 className="newspaper-heading text-2xl md:text-3xl uppercase tracking-wider">
          {title}
        </h1>
        <div className="flex-grow border-t border-newspaper-400"></div>
        {actions && <div className="flex-shrink-0">{actions}</div>}
      </div>

      {/* Subtitle */}
      {subtitle && (
        <p className="text-xs text-center text-newspaper-600 font-serif italic">
          {subtitle}
        </p>
      )}
    </div>
  );
}
