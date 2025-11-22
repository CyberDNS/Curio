import { Link, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getCategories } from "../../services/api";
import { Home, List } from "lucide-react";

export default function Navigation() {
  const location = useLocation();
  const { data: categories = [] } = useQuery({
    queryKey: ["categories"],
    queryFn: getCategories,
  });

  const isActive = (path: string) => location.pathname === path;

  return (
    <nav className="bg-newspaper-900 text-white sticky top-0 z-10 shadow-lg">
      <div className="container mx-auto px-4">
        <ul className="flex overflow-x-auto scrollbar-hide">
          <li>
            <Link
              to="/"
              className={`flex items-center gap-2 px-4 py-3 text-sm font-semibold uppercase tracking-wider whitespace-nowrap border-b-2 transition-colors ${
                isActive("/")
                  ? "border-white bg-newspaper-800"
                  : "border-transparent hover:bg-newspaper-800 hover:border-newspaper-500"
              }`}
            >
              <Home className="w-4 h-4" />
              Today
            </Link>
          </li>
          {categories.map((category) => (
            <li key={category.id}>
              <Link
                to={`/category/${category.slug}`}
                className={`block px-4 py-3 text-sm font-semibold uppercase tracking-wider whitespace-nowrap border-b-2 transition-colors ${
                  isActive(`/category/${category.slug}`)
                    ? "border-white bg-newspaper-800"
                    : "border-transparent hover:bg-newspaper-800 hover:border-newspaper-500"
                }`}
              >
                {category.name}
              </Link>
            </li>
          ))}
          <li>
            <Link
              to="/all"
              className={`flex items-center gap-2 px-4 py-3 text-sm font-semibold uppercase tracking-wider whitespace-nowrap border-b-2 transition-colors ${
                isActive("/all")
                  ? "border-white bg-newspaper-800"
                  : "border-transparent hover:bg-newspaper-800 hover:border-newspaper-500"
              }`}
            >
              <List className="w-4 h-4" />
              All
            </Link>
          </li>
        </ul>
      </div>
    </nav>
  );
}
