import { useMemo } from "react";
import type { Article } from "../../types";
import NewspaperArticleCard from "./NewspaperArticleCard";

interface NewspaperGridProps {
  articles: Article[];
}

type ArticleSize = "hero" | "large" | "medium" | "small";

interface LayoutArticle {
  article: Article;
  size: ArticleSize;
}

export default function NewspaperGrid({ articles }: NewspaperGridProps) {
  // Generate a deterministic but daily-changing layout
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

    // Preserve the order from the backend (new articles first, then existing)
    // The backend already sorts by relevance within each group
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

      let size: ArticleSize;

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

  return (
    <div className="newspaper-grid">
      {layout.map(({ article, size }) => (
        <div
          key={article.id}
          className={`newspaper-grid-item newspaper-grid-item-${size}`}
        >
          <NewspaperArticleCard article={article} size={size} />
        </div>
      ))}

      <style>{`
        .newspaper-grid {
          display: grid;
          grid-template-columns: repeat(1, 1fr);
          gap: 1.5rem;
          grid-auto-flow: dense;
        }

        @media (min-width: 768px) {
          .newspaper-grid {
            grid-template-columns: repeat(2, 1fr);
          }
          .newspaper-grid-item-hero {
            grid-column: span 2;
          }
          .newspaper-grid-item-large {
            grid-column: span 2;
          }
        }

        @media (min-width: 1024px) {
          .newspaper-grid {
            grid-template-columns: repeat(4, 1fr);
          }
          .newspaper-grid-item-hero {
            grid-column: span 4;
          }
          .newspaper-grid-item-large {
            grid-column: span 2;
          }
          .newspaper-grid-item-medium {
            grid-column: span 1;
          }
          .newspaper-grid-item-small {
            grid-column: span 1;
          }
        }
      `}</style>
    </div>
  );
}
