import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { LogIn, Newspaper } from "lucide-react";

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
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <div className="flex justify-center mb-4">
            <Newspaper className="w-16 h-16 text-blue-600" />
          </div>
          <h1 className="text-4xl font-bold text-gray-900 mb-2">CURIO</h1>
          <p className="text-lg text-gray-600">Your Personalized News Digest</p>
        </div>

        <div className="bg-white shadow-lg rounded-lg p-8">
          <h2 className="text-2xl font-semibold text-center text-gray-800 mb-6">
            Sign in to continue
          </h2>

          <p className="text-center text-gray-600 mb-8">
            Please authenticate to access your personalized news feed
          </p>

          <button
            onClick={login}
            className="w-full flex items-center justify-center gap-3 px-6 py-3 bg-blue-600 text-white text-lg font-medium rounded-lg hover:bg-blue-700 transition-colors shadow-md hover:shadow-lg"
          >
            <LogIn className="w-6 h-6" />
            Sign in with Pocket ID
          </button>

          <p className="mt-6 text-center text-sm text-gray-500">
            Secure authentication via OAuth2 / OpenID Connect
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
