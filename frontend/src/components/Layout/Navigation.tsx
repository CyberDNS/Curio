import { useState, useRef, useEffect, useCallback } from "react";
import { Link, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getCategories, getUnreadCounts } from "../../services/api";
import {
  Home,
  List,
  Bookmark,
  ChevronDown,
  MoreHorizontal,
} from "lucide-react";

/** Small dot indicator for unread items */
function UnreadDot({
  count,
  showCount = false,
}: {
  count: number;
  showCount?: boolean;
}) {
  if (count === 0) return null;

  return showCount ? (
    <span className="ml-1 px-1.5 py-0.5 text-xs bg-red-500 text-white rounded-full min-w-[18px] text-center">
      {count > 99 ? "99+" : count}
    </span>
  ) : (
    <span className="w-2 h-2 bg-red-500 rounded-full" />
  );
}

export default function Navigation() {
  const location = useLocation();
  const [showMoreMenu, setShowMoreMenu] = useState(false);
  const [visibleCount, setVisibleCount] = useState<number | null>(null); // null = show all

  const moreMenuRef = useRef<HTMLLIElement>(null);
  const navRef = useRef<HTMLUListElement>(null);
  const categoryRefs = useRef<Map<number, HTMLLIElement>>(new Map());
  const measureContainerRef = useRef<HTMLDivElement>(null);

  const { data: categories = [] } = useQuery({
    queryKey: ["categories"],
    queryFn: getCategories,
  });

  const { data: unreadCounts = {} } = useQuery({
    queryKey: ["unreadCounts"],
    queryFn: getUnreadCounts,
    refetchInterval: 60000, // Refresh every minute
  });

  const isActive = (path: string) => location.pathname === path;

  // Split categories into visible and overflow
  const visibleCategories =
    visibleCount === null ? categories : categories.slice(0, visibleCount);
  const overflowCategories =
    visibleCount === null ? [] : categories.slice(visibleCount);

  // Check if active category is in overflow
  const activeOverflowCategory = overflowCategories.find(
    (cat) => location.pathname === `/category/${cat.slug}`
  );

  // Calculate total unread for overflow categories
  const overflowUnreadCount = overflowCategories.reduce(
    (sum, cat) => sum + (unreadCounts[cat.slug] || 0),
    0
  );

  // Measure and determine how many categories fit
  const calculateVisibleCount = useCallback(() => {
    if (
      !measureContainerRef.current ||
      !navRef.current ||
      categories.length === 0
    ) {
      setVisibleCount(null);
      return;
    }

    const containerWidth = navRef.current.clientWidth;
    const measureItems = measureContainerRef.current.children;

    // Get widths of fixed items (Today, All, Saved, More button)
    const todayWidth = (measureItems[0] as HTMLElement)?.offsetWidth || 0;
    const allWidth =
      (measureItems[measureItems.length - 2] as HTMLElement)?.offsetWidth || 0;
    const savedWidth =
      (measureItems[measureItems.length - 1] as HTMLElement)?.offsetWidth || 0;

    // Estimate "More" button width (approximately 100px)
    const moreButtonWidth = 100;

    const fixedWidth = todayWidth + allWidth + savedWidth;
    let availableWidth = containerWidth - fixedWidth;

    // Measure each category and count how many fit
    let count = 0;
    let usedWidth = 0;

    for (let i = 0; i < categories.length; i++) {
      // Category items start at index 1 (after Today)
      const categoryEl = measureItems[i + 1] as HTMLElement;
      if (!categoryEl) break;

      const categoryWidth = categoryEl.offsetWidth;

      // Check if this category fits
      // If there are more categories after this one, we need space for "More" button
      const needsMoreButton = i < categories.length - 1;
      const widthNeeded =
        usedWidth + categoryWidth + (needsMoreButton ? moreButtonWidth : 0);

      if (widthNeeded <= availableWidth) {
        usedWidth += categoryWidth;
        count++;
      } else {
        // This category doesn't fit, but we need to check if we need the More button
        // If count is 0 and no categories fit, we still show the More button
        break;
      }
    }

    // If all categories fit, set to null (show all)
    if (count >= categories.length) {
      setVisibleCount(null);
    } else {
      setVisibleCount(count);
    }
  }, [categories]);

  // Check overflow on mount, resize, and when categories change
  useEffect(() => {
    // Use requestAnimationFrame to ensure layout is complete before measuring
    const rafId = requestAnimationFrame(() => {
      calculateVisibleCount();
    });

    // Also check after a short delay to handle font loading
    const timeoutId = setTimeout(calculateVisibleCount, 100);

    window.addEventListener("resize", calculateVisibleCount);

    // Use ResizeObserver for more reliable container size tracking
    let resizeObserver: ResizeObserver | null = null;
    if (navRef.current) {
      resizeObserver = new ResizeObserver(() => {
        calculateVisibleCount();
      });
      resizeObserver.observe(navRef.current);
    }

    return () => {
      cancelAnimationFrame(rafId);
      clearTimeout(timeoutId);
      window.removeEventListener("resize", calculateVisibleCount);
      resizeObserver?.disconnect();
    };
  }, [calculateVisibleCount, categories]);

  // Re-check when fonts are loaded
  useEffect(() => {
    if (document.fonts?.ready) {
      document.fonts.ready.then(calculateVisibleCount);
    }
  }, [calculateVisibleCount]);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        moreMenuRef.current &&
        !moreMenuRef.current.contains(event.target as Node)
      ) {
        setShowMoreMenu(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Close menu on route change
  useEffect(() => {
    setShowMoreMenu(false);
  }, [location.pathname]);

  const navLinkClass = (active: boolean) =>
    `flex items-center gap-2 px-4 py-3 text-sm font-semibold uppercase tracking-wider whitespace-nowrap border-b-2 transition-colors ${
      active
        ? "border-white bg-newspaper-800"
        : "border-transparent hover:bg-newspaper-800 hover:border-newspaper-500"
    }`;

  return (
    <nav className="bg-newspaper-900 text-white sticky top-0 z-10 shadow-lg">
      <div className="container mx-auto px-4">
        {/* Hidden measure element to calculate widths */}
        <div
          ref={measureContainerRef}
          className="absolute left-0 invisible h-0 overflow-hidden whitespace-nowrap"
          style={{ display: "flex" }}
          aria-hidden="true"
        >
          {/* Today */}
          <span className="px-4 py-3 text-sm font-semibold uppercase tracking-wider whitespace-nowrap flex items-center gap-2">
            <Home className="w-4 h-4" />
            Today
          </span>
          {/* Categories */}
          {categories.map((category) => (
            <span
              key={category.id}
              className="px-4 py-3 text-sm font-semibold uppercase tracking-wider whitespace-nowrap"
            >
              {category.name}
            </span>
          ))}
          {/* All */}
          <span className="px-4 py-3 text-sm font-semibold uppercase tracking-wider whitespace-nowrap flex items-center gap-2">
            <List className="w-4 h-4" />
            All
          </span>
          {/* Saved */}
          <span className="px-4 py-3 text-sm font-semibold uppercase tracking-wider whitespace-nowrap flex items-center gap-2">
            <Bookmark className="w-4 h-4" />
            Saved
          </span>
        </div>

        <ul ref={navRef} className="flex">
          {/* Today - always visible */}
          <li>
            <Link to="/" className={navLinkClass(isActive("/"))}>
              <Home className="w-4 h-4" />
              Today
              <UnreadDot count={unreadCounts.today || 0} />
            </Link>
          </li>

          {/* Visible categories */}
          {visibleCategories.map((category) => (
            <li
              key={category.id}
              ref={(el) => {
                if (el) categoryRefs.current.set(category.id, el);
                else categoryRefs.current.delete(category.id);
              }}
            >
              <Link
                to={`/category/${category.slug}`}
                className={navLinkClass(isActive(`/category/${category.slug}`))}
              >
                {category.name}
                <UnreadDot count={unreadCounts[category.slug] || 0} />
              </Link>
            </li>
          ))}

          {/* More dropdown for overflow categories */}
          {overflowCategories.length > 0 && (
            <li className="relative" ref={moreMenuRef}>
              <button
                onClick={() => setShowMoreMenu(!showMoreMenu)}
                className={navLinkClass(!!activeOverflowCategory)}
              >
                <MoreHorizontal className="w-4 h-4" />
                <span>{activeOverflowCategory?.name || "More"}</span>
                <UnreadDot count={overflowUnreadCount} />
                <ChevronDown
                  className={`w-3 h-3 transition-transform ${
                    showMoreMenu ? "rotate-180" : ""
                  }`}
                />
              </button>

              {/* Dropdown menu */}
              {showMoreMenu && (
                <div className="absolute top-full left-0 mt-0 bg-newspaper-800 shadow-xl rounded-b-lg min-w-[180px] max-h-[60vh] overflow-y-auto z-20">
                  {overflowCategories.map((category) => (
                    <Link
                      key={category.id}
                      to={`/category/${category.slug}`}
                      className={`flex items-center justify-between px-4 py-3 text-sm font-medium transition-colors ${
                        isActive(`/category/${category.slug}`)
                          ? "bg-newspaper-700 text-white"
                          : "text-newspaper-200 hover:bg-newspaper-700 hover:text-white"
                      }`}
                    >
                      <span>{category.name}</span>
                      <UnreadDot
                        count={unreadCounts[category.slug] || 0}
                        showCount
                      />
                    </Link>
                  ))}
                </div>
              )}
            </li>
          )}

          {/* All - always visible */}
          <li>
            <Link to="/all" className={navLinkClass(isActive("/all"))}>
              <List className="w-4 h-4" />
              All
            </Link>
          </li>

          {/* Saved - always visible */}
          <li>
            <Link to="/saved" className={navLinkClass(isActive("/saved"))}>
              <Bookmark className="w-4 h-4" />
              Saved
            </Link>
          </li>
        </ul>
      </div>
    </nav>
  );
}
