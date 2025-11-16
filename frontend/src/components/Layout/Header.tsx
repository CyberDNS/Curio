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

  const newspaperTitle = titleSetting?.value || "CURIO";

  return (
    <header className="border-b-4 border-newspaper-900 bg-white">
      <div className="container mx-auto px-4 py-6">
        {/* Masthead */}
        <div className="text-center mb-4">
          <Link to="/">
            <h1 className="newspaper-heading text-6xl md:text-7xl lg:text-8xl tracking-tighter">
              {newspaperTitle}
            </h1>
            {newspaperTitle !== "CURIO" && (
              <p className="text-xs text-newspaper-500 mt-1">by Curio</p>
            )}
            <p className="text-sm mt-1 text-newspaper-600 font-serif italic">
              Your Personalized News Digest
            </p>
          </Link>
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
