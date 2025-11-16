import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";
import { NewspaperProvider } from "./contexts/NewspaperContext";
import ProtectedRoute from "./components/Auth/ProtectedRoute";
import Layout from "./components/Layout/Layout";
import HomePage from "./pages/HomePage";
import SettingsPage from "./pages/SettingsPage";
import CategoryPage from "./pages/CategoryPage";
import AllArticlesPage from "./pages/AllArticlesPage";
import AuthCallbackPage from "./pages/AuthCallbackPage";
import LoginPage from "./pages/LoginPage";

function App() {
  return (
    <Router>
      <AuthProvider>
        <NewspaperProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/auth/callback" element={<AuthCallbackPage />} />
            <Route
              path="/*"
              element={
                <ProtectedRoute>
                  <Layout>
                    <Routes>
                      <Route path="/" element={<HomePage />} />
                      <Route path="/category/:slug" element={<CategoryPage />} />
                      <Route path="/all" element={<AllArticlesPage />} />
                      <Route path="/settings" element={<SettingsPage />} />
                    </Routes>
                  </Layout>
                </ProtectedRoute>
              }
            />
          </Routes>
        </NewspaperProvider>
      </AuthProvider>
    </Router>
  );
}

export default App;
