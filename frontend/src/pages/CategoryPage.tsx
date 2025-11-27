import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getCategories } from "../services/api";
import PageHeader from "../components/Layout/PageHeader";
import NewspaperView from "../components/Articles/NewspaperView";
import { ArticleViewToggle, useViewMode } from "../components/Articles";
import { Loader2, AlertCircle } from "lucide-react";

export default function CategoryPage() {
  const { slug } = useParams<{ slug: string }>();
  const { viewMode, toggleViewMode } = useViewMode("grid");

  const { data: categories = [], isLoading: categoriesLoading } = useQuery({
    queryKey: ["categories"],
    queryFn: getCategories,
  });

  const category = categories.find((c) => c.slug === slug);

  if (categoriesLoading) {
    return (
      <div className="flex justify-center items-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-newspaper-600" />
      </div>
    );
  }

  if (!category) {
    return (
      <div className="flex justify-center items-center py-20">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-newspaper-600 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-newspaper-900 mb-2">
            Category not found
          </h2>
          <p className="text-newspaper-600">
            The category "{slug}" does not exist.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title={category.name}
        subtitle="Section curated by AI • Sorted by relevance"
        actions={
          <ArticleViewToggle viewMode={viewMode} onToggle={toggleViewMode} />
        }
      />
      <NewspaperView categorySlug={slug} viewMode={viewMode} />
    </div>
  );
}
