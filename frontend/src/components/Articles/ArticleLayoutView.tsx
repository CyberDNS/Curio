import { useMemo } from "react";
import type { Article } from "../../types";
import type { ArticleCardSize, ArticleDisplayConfig } from "./types";
import { ArticleCard, ArticleListItem, NewspaperGrid, ArticleList } from "./index";

interface ArticleLayoutViewProps {
  articles: Article[];
  viewMode?: "grid" | "list";
  config?: Partial<ArticleDisplayConfig>;
}

interface LayoutArticle {
  article: Article;
  size: ArticleCardSize;
}

/**
 * Displays articles in either grid or list layout
 * Grid layout uses newspaper-style sizing based on relevance scores
 */
export default function ArticleLayoutView({
  articles,
  viewMode = "grid",
  config,
}: ArticleLayoutViewProps) {
  // Generate a deterministic but daily-changing layout for grid view
  const layout = useMemo(() => {
    if (articles.length === 0) return [];

    // Use today's date as seed for deterministic randomization
    const today = new Date().toDateString();
    const seed = today
      .split("")
      .reduce((acc, char) => acc + char.charCodeAt(0), 0);

    // Simple seeded random function
    let randomSeed = seed;
    const seededRandom = () => {
      randomSeed = (randomSeed * 9301 + 49297) % 233280;
      return randomSeed / 233280;
    };

    const layoutArticles: LayoutArticle[] = [];
    let remainingArticles = [...articles];

    // Track how many of each size we've created for better distribution
    let heroCount = 0;
    let largeCount = 0;

    // Assign sizes based on score and random variation
    while (remainingArticles.length > 0) {
      const article = remainingArticles.shift()!;
      const score = article.relevance_score;
      const rand = seededRandom();

      let size: ArticleCardSize;

      // Hero article (max 1 per 15 articles, only for very high scores)
      if (
        heroCount === 0 &&
        layoutArticles.length < 3 &&
        score > 0.8 &&
        rand > 0.3
      ) {
        size = "hero";
        heroCount++;
      }
      // Large articles (limited to ~20% of articles, higher threshold)
      else if (
        largeCount < Math.ceil(articles.length * 0.2) &&
        score > 0.7 &&
        rand > 0.5
      ) {
        size = "large";
        largeCount++;
      }
      // Medium articles (for moderate scores)
      else if (score > 0.4 || (score > 0.2 && rand > 0.4)) {
        size = "medium";
      }
      // Small articles (default for most)
      else {
        size = "small";
      }

      layoutArticles.push({ article, size });
    }

    return layoutArticles;
  }, [articles]);

  if (layout.length === 0) {
    return (
      <div className="text-center py-12 text-newspaper-600">
        <p className="text-lg">No articles available</p>
      </div>
    );
  }

  // List view
  if (viewMode === "list") {
    return (
      <ArticleList>
        {layout.map(({ article }) => (
          <ArticleListItem
            key={article.id}
            article={article}
            config={config}
          />
        ))}
      </ArticleList>
    );
  }

  // Grid view (newspaper-style)
  return (
    <NewspaperGrid>
      {layout.map(({ article, size }) => (
        <div
          key={article.id}
          className={`article-${size}`}
        >
          <ArticleCard
            article={article}
            size={size}
            config={config}
          />
        </div>
      ))}
    </NewspaperGrid>
  );
}
