import { useState, useRef, useEffect, useCallback } from "react";
import { Link, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getCategories, getUnreadCounts } from "../../services/api";
import { Home, List, Bookmark, ChevronDown, Layers } from "lucide-react";

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
  const [showCategoryMenu, setShowCategoryMenu] = useState(false);
  const [useDropdown, setUseDropdown] = useState(false);

  const menuRef = useRef<HTMLLIElement>(null);
  const navRef = useRef<HTMLUListElement>(null);
  const measureRef = useRef<HTMLDivElement>(null);

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
  const isCategoryActive = categories.some(
    (cat) => location.pathname === `/category/${cat.slug}`
  );
  const activeCategory = categories.find(
    (cat) => location.pathname === `/category/${cat.slug}`
  );

  // Calculate total unread for categories (for dropdown indicator)
  const totalCategoryUnread = categories.reduce(
    (sum, cat) => sum + (unreadCounts[cat.slug] || 0),
    0
  );

  // Check if navigation would overflow
  const checkOverflow = useCallback(() => {
    if (measureRef.current && navRef.current) {
      const containerWidth = navRef.current.parentElement?.clientWidth || 0;
      const contentWidth = measureRef.current.scrollWidth;
      setUseDropdown(contentWidth > containerWidth);
    }
  }, []);

  // Check overflow on mount, resize, and when categories change
  useEffect(() => {
    checkOverflow();
    window.addEventListener("resize", checkOverflow);
    return () => window.removeEventListener("resize", checkOverflow);
  }, [checkOverflow, categories]);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowCategoryMenu(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Close menu on route change
  useEffect(() => {
    setShowCategoryMenu(false);
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
        {/* Hidden measure element to calculate full width */}
        <div
          ref={measureRef}
          className="absolute invisible h-0 overflow-hidden flex"
          aria-hidden="true"
        >
          <span className="px-4 py-3 text-sm font-semibold uppercase tracking-wider whitespace-nowrap flex items-center gap-2">
            <Home className="w-4 h-4" />
            Today
          </span>
          {categories.map((category) => (
            <span
              key={category.id}
              className="px-4 py-3 text-sm font-semibold uppercase tracking-wider whitespace-nowrap"
            >
              {category.name}
            </span>
          ))}
          <span className="px-4 py-3 text-sm font-semibold uppercase tracking-wider whitespace-nowrap flex items-center gap-2">
            <List className="w-4 h-4" />
            All
          </span>
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

          {/* Categories - dropdown when overflow, inline otherwise */}
          {categories.length > 0 && (
            <>
              {/* Dropdown mode */}
              {useDropdown && (
                <li className="relative" ref={menuRef}>
                  <button
                    onClick={() => setShowCategoryMenu(!showCategoryMenu)}
                    className={navLinkClass(isCategoryActive)}
                  >
                    <Layers className="w-4 h-4" />
                    <span className="max-w-[120px] truncate">
                      {activeCategory?.name || "Categories"}
                    </span>
                    <UnreadDot count={totalCategoryUnread} />
                    <ChevronDown
                      className={`w-3 h-3 transition-transform ${
                        showCategoryMenu ? "rotate-180" : ""
                      }`}
                    />
                  </button>

                  {/* Dropdown menu */}
                  {showCategoryMenu && (
                    <div className="absolute top-full left-0 mt-0 bg-newspaper-800 shadow-xl rounded-b-lg min-w-[180px] max-h-[60vh] overflow-y-auto z-20">
                      {categories.map((category) => (
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

              {/* Inline mode */}
              {!useDropdown &&
                categories.map((category) => (
                  <li key={category.id}>
                    <Link
                      to={`/category/${category.slug}`}
                      className={navLinkClass(
                        isActive(`/category/${category.slug}`)
                      )}
                    >
                      {category.name}
                      <UnreadDot count={unreadCounts[category.slug] || 0} />
                    </Link>
                  </li>
                ))}
            </>
          )}

          {/* Spacer to push All and Saved to the right when using dropdown */}
          {useDropdown && <li className="flex-1" />}

          {/* All - always visible (no unread indicator) */}
          <li>
            <Link to="/all" className={navLinkClass(isActive("/all"))}>
              <List className="w-4 h-4" />
              {!useDropdown && <span>All</span>}
            </Link>
          </li>

          {/* Saved - always visible */}
          <li>
            <Link to="/saved" className={navLinkClass(isActive("/saved"))}>
              <Bookmark className="w-4 h-4" />
              {!useDropdown && <span>Saved</span>}
            </Link>
          </li>
        </ul>
      </div>
    </nav>
  );
}
