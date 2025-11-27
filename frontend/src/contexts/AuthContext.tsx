import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from "react";
import { useNavigate } from "react-router-dom";

interface User {
  id: number;
  email: string;
  name: string;
  picture: string;
  preferred_username: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: () => void;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  // Function to check and load auth state from cookie
  const checkAuth = React.useCallback(async () => {
    try {
      console.log("Checking auth state...");
      const API_BASE = import.meta.env.VITE_API_URL || "/api";
      const response = await fetch(`${API_BASE}/auth/me`, {
        credentials: "include", // Include cookies
      });

      console.log("Auth check response status:", response.status);

      if (response.ok) {
        const userData = await response.json();
        console.log("User authenticated:", userData);
        setUser(userData);
        setToken("cookie"); // Token is in HttpOnly cookie, just set a placeholder
      } else {
        console.log("User not authenticated");
        setUser(null);
        setToken(null);
      }
    } catch (error) {
      console.error("Failed to check auth:", error);
      setUser(null);
      setToken(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    // Check auth state on mount
    checkAuth();

    // Listen for custom auth update events
    const handleAuthUpdate = (_e: Event) => {
      console.log("Auth update event received");
      checkAuth();
    };

    // Listen for auth expired events (from API interceptor when refresh fails)
    const handleAuthExpired = (_e: Event) => {
      console.log("Auth expired event received - session ended");
      setUser(null);
      setToken(null);
      navigate("/login");
    };

    window.addEventListener("authUpdate", handleAuthUpdate as EventListener);
    window.addEventListener("authExpired", handleAuthExpired as EventListener);

    return () => {
      window.removeEventListener(
        "authUpdate",
        handleAuthUpdate as EventListener
      );
      window.removeEventListener(
        "authExpired",
        handleAuthExpired as EventListener
      );
    };
  }, [checkAuth, navigate]);

  const login = () => {
    // Redirect to backend OAuth login endpoint
    const API_BASE = import.meta.env.VITE_API_URL || "/api";
    window.location.href = `${API_BASE}/auth/login`;
  };

  const logout = async () => {
    try {
      const API_BASE = import.meta.env.VITE_API_URL || "/api";
      await fetch(`${API_BASE}/auth/logout`, {
        method: "POST",
        credentials: "include", // Include cookies
      });
    } catch (error) {
      console.error("Logout error:", error);
    } finally {
      setToken(null);
      setUser(null);
      navigate("/");
    }
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
};
