import { useState, useEffect } from "react";
import { getProxiedImageUrl } from "../../../services/api";
import type { Article } from "../../../types";

interface ArticleImageProps {
  article: Article;
  className?: string;
  onClick?: () => void;
  /** Enable cycling through multiple images (Harry Potter effect) */
  enableCycling?: boolean;
  /** Interval for image cycling in milliseconds (default: 5000) */
  cycleInterval?: number;
}

/**
 * Displays an article image with proxy support, error handling,
 * and optional image cycling animation
 */
export default function ArticleImage({
  article,
  className = "",
  onClick,
  enableCycling = false,
  cycleInterval = 5000,
}: ArticleImageProps) {
  const [imageError, setImageError] = useState(false);
  // Start at random index to avoid all images showing the same one initially
  const [currentImageIndex, setCurrentImageIndex] = useState(() =>
    Math.floor(Math.random() * (article.image_urls?.length || 1))
  );

  // Collect all available images
  const allImages: string[] = [];
  if (article.image_url) allImages.push(article.image_url);
  if (article.image_urls && article.image_urls.length > 0) {
    article.image_urls.forEach((url) => {
      if (!allImages.includes(url)) allImages.push(url);
    });
  }

  // Cycle through images if enabled and multiple images exist
  useEffect(() => {
    if (!enableCycling || allImages.length <= 1) return;

    const interval = setInterval(() => {
      setCurrentImageIndex((prev) => (prev + 1) % allImages.length);
    }, cycleInterval);

    return () => clearInterval(interval);
  }, [enableCycling, allImages.length, cycleInterval]);

  // Reset error state if images change
  useEffect(() => {
    setImageError(false);
  }, [article.id]);

  if (allImages.length === 0 || imageError) {
    return null;
  }

  const currentImage = allImages[currentImageIndex % allImages.length];
  const proxiedUrl = getProxiedImageUrl(currentImage);
  const displayTitle = article.llm_title || article.title;

  if (!proxiedUrl) {
    return null;
  }

  return (
    <div className={`overflow-hidden relative group ${className}`}>
      <img
        src={proxiedUrl}
        alt={displayTitle}
        className={`w-full h-full object-cover ${enableCycling ? "harry-potter-image" : ""} ${
          onClick ? "cursor-pointer hover:opacity-90 transition-opacity" : ""
        }`}
        onError={() => setImageError(true)}
        onClick={onClick}
      />
      
      {/* Image counter indicator */}
      {enableCycling && allImages.length > 1 && (
        <div className="absolute bottom-2 right-2 bg-black bg-opacity-70 text-white px-2 py-1 rounded text-xs">
          {currentImageIndex + 1} / {allImages.length}
        </div>
      )}
      
      {/* Click overlay for better UX */}
      {onClick && (
        <div
          className="absolute inset-0 cursor-pointer opacity-0 hover:opacity-100 transition-opacity bg-newspaper-900 bg-opacity-10"
          onClick={onClick}
        />
      )}
    </div>
  );
}
