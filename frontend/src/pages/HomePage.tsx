import PageHeader from "../components/Layout/PageHeader";
import NewspaperView from "../components/Articles/NewspaperView";
import { ArticleViewToggle, useViewMode } from "../components/Articles";

export default function HomePage() {
  const { viewMode, toggleViewMode } = useViewMode("grid");

  return (
    <div>
      <PageHeader
        title="Today"
        subtitle="Front page headlines and top stories • Curated by AI"
        actions={
          <ArticleViewToggle viewMode={viewMode} onToggle={toggleViewMode} />
        }
      />
      <NewspaperView showFallback={true} viewMode={viewMode} />
    </div>
  );
}
