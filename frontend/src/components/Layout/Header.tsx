import { Link } from "react-router-dom";
import { Settings, LogIn, LogOut } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { getSetting, getAvailableNewspaperDates } from "../../services/api";
import { useAuth } from "../../contexts/AuthContext";
import { useNewspaper } from "../../contexts/NewspaperContext";
import NewspaperDateHeader from "../DatePicker/NewspaperDateHeader";

export default function Header() {
  const { user, login, logout } = useAuth();
  const { selectedDate, setSelectedDate } = useNewspaper();

  const { data: titleSetting } = useQuery({
    queryKey: ["settings", "newspaper_title"],
    queryFn: () => getSetting("newspaper_title"),
    retry: false,
    // Public endpoint - can fetch without auth
  });

  const { data: availableDates = [] } = useQuery({
    queryKey: ["newspapers", "dates"],
    queryFn: () => getAvailableNewspaperDates(7),
    refetchInterval: 60000,
  });

  const newspaperTitle = titleSetting?.value || "Curio Times";

  return (
    <header className="border-b-4 border-newspaper-900 bg-white">
      <div className="container mx-auto px-4 py-4">
        {/* Masthead */}
        <div className="mb-3">
          <div className="text-center">
            <div className="flex flex-col items-center">
              {/* Top decorative line */}
              <div className="w-full border-t border-newspaper-900 mb-3"></div>

              {/* Logo and title row */}
              <div className="relative w-full mb-2">
                {/* Left side: Logo and ornament */}
                <div className="absolute left-0 top-0 flex items-center gap-4">
                  {/* Logo */}
                  <Link to="/" className="flex-shrink-0">
                    <img
                      src="/logo.png"
                      alt="Curio Logo"
                      className="w-20 h-20 md:w-24 md:h-24 object-contain"
                    />
                  </Link>

                  {/* Left ornamental element */}
                  <div className="hidden md:flex flex-col items-center flex-shrink-0">
                    <div className="w-16 h-px bg-newspaper-900 mb-1"></div>
                    <div className="w-12 h-px bg-newspaper-900 mb-1"></div>
                    <div className="w-8 h-px bg-newspaper-900"></div>
                  </div>
                </div>

                {/* Main title - centered */}
                <div className="text-center px-32 md:px-40">
                  <h1 className="newspaper-heading text-5xl md:text-6xl lg:text-7xl tracking-tighter leading-none">
                    {newspaperTitle}
                  </h1>
                  <p className="text-sm mt-1 text-newspaper-600 font-serif italic">
                    Your Personalized News Digest
                  </p>
                </div>

                {/* Right side: Ornament and invisible logo spacer */}
                <div className="absolute right-0 top-0 flex items-center gap-4">
                  {/* Right ornamental element */}
                  <div className="hidden md:flex flex-col items-center flex-shrink-0">
                    <div className="w-16 h-px bg-newspaper-900 mb-1"></div>
                    <div className="w-12 h-px bg-newspaper-900 mb-1"></div>
                    <div className="w-8 h-px bg-newspaper-900"></div>
                  </div>

                  {/* Invisible spacer to maintain centering */}
                  <div className="flex-shrink-0 w-20 h-20 md:w-24 md:h-24"></div>
                </div>
              </div>

              {/* Bottom decorative line */}
              <div className="w-full border-b border-newspaper-900"></div>
            </div>
          </div>
        </div>

        {/* Date and actions */}
        <div className="flex justify-between items-center border-t border-b border-newspaper-300 py-2">
          <NewspaperDateHeader
            currentDate={selectedDate}
            availableDates={availableDates}
            onDateChange={setSelectedDate}
          />
          <div className="flex gap-2 items-center">
            {user && (
              <div className="flex items-center gap-2 text-xs text-newspaper-700">
                {user.picture && (
                  <img
                    src={user.picture}
                    alt={user.name}
                    className="w-6 h-6 rounded-full"
                  />
                )}
                <span className="hidden md:inline">
                  {user.name || user.email}
                </span>
              </div>
            )}

            <Link
              to="/settings"
              className="flex items-center gap-1 px-3 py-1 text-xs md:text-sm bg-newspaper-900 text-white hover:bg-newspaper-700 transition-colors"
            >
              <Settings className="w-4 h-4" />
              <span className="hidden md:inline">Settings</span>
            </Link>

            {user ? (
              <button
                onClick={logout}
                className="flex items-center gap-1 px-3 py-1 text-xs md:text-sm bg-red-600 text-white hover:bg-red-700 transition-colors"
              >
                <LogOut className="w-4 h-4" />
                <span className="hidden md:inline">Logout</span>
              </button>
            ) : (
              <button
                onClick={login}
                className="flex items-center gap-1 px-3 py-1 text-xs md:text-sm bg-blue-600 text-white hover:bg-blue-700 transition-colors"
              >
                <LogIn className="w-4 h-4" />
                <span className="hidden md:inline">Login</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
