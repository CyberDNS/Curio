import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";

const AuthCallbackPage: React.FC = () => {
  const navigate = useNavigate();

  useEffect(() => {
    // Auth token is now set via HttpOnly cookie by the backend
    // No need to extract from URL or store in localStorage
    console.log("Auth callback - triggering auth check");

    // Dispatch custom event to notify AuthContext to check auth
    window.dispatchEvent(new Event("authUpdate"));
    console.log("Auth update event dispatched");

    // Navigate to home after a short delay to allow auth check
    setTimeout(() => {
      console.log("Navigating to home page");
      navigate("/", { replace: true });
    }, 500);
  }, [navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p className="text-gray-600">Completing authentication...</p>
      </div>
    </div>
  );
};

export default AuthCallbackPage;
