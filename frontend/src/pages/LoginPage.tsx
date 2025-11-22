import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { LogIn } from "lucide-react";

const LoginPage: React.FC = () => {
  const { user, login, isLoading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    // If user is already logged in, redirect to home
    if (user) {
      navigate("/", { replace: true });
    }
  }, [user, navigate]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-newspaper-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-newspaper-900"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-newspaper-50 px-4">
      <div className="max-w-md w-full">
        <div
          className="bg-white shadow-2xl"
          style={{
            boxShadow:
              "0 0 0 1px #1c1917, 0 0 0 4px #1c1917, 0 20px 25px -5px rgba(0, 0, 0, 0.1)",
          }}
        >
          {/* Header with logo */}
          <div className="bg-white py-8 px-6 pb-6">
            <div className="text-center">
              <img
                src="/logo.png"
                alt="Curio - Your Personalized News Digest"
                className="h-32 w-auto mx-auto mb-1"
              />
              <p className="text-sm text-newspaper-600 font-serif italic">
                Your Personalized News Digest
              </p>
            </div>
          </div>

          {/* Divider - double line like newspaper */}
          <div className="border-t border-b border-newspaper-900 mx-6">
            <div className="border-t border-newspaper-900 my-0.5"></div>
          </div>

          {/* Content */}
          <div className="p-8">
            <h2 className="text-2xl font-serif font-bold text-center text-newspaper-900 mb-4 border-b-2 border-newspaper-300 pb-2">
              Sign in to continue
            </h2>

            <p className="text-center text-newspaper-700 mb-8 font-serif">
              Please authenticate to access your personalized news feed
            </p>

            <button
              onClick={login}
              className="w-full flex items-center justify-center gap-3 px-6 py-3 bg-newspaper-900 text-white text-lg font-semibold hover:bg-newspaper-700 transition-colors"
            >
              <LogIn className="w-6 h-6" />
              Sign in with Pocket ID
            </button>

            <p className="mt-6 text-center text-xs text-newspaper-500 font-serif">
              Secure authentication via OAuth2 / OpenID Connect
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
