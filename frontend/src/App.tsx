import { useEffect, type ReactNode } from "react";
import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Sources from "./pages/Sources";
import Pages from "./pages/Pages";
import PageDetail from "./pages/PageDetail";
import Graph from "./pages/Graph";
import Drift from "./pages/Drift";
import AuditLog from "./pages/AuditLog";
import Analytics from "./pages/Analytics";
import Search from "./pages/Search";
import Settings from "./pages/Settings";
import Admin from "./pages/Admin";
import Organization from "./pages/Organization";
import OwnerExplorer from "./pages/OwnerExplorer";
import Login from "./pages/Login";
import AuthCallback from "./pages/AuthCallback";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";
import { useAuth } from "./context/AuthContext";

function TokenHandler({ children }: { children: ReactNode }) {
  const { setToken } = useAuth();

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("token");
    if (token) {
      setToken(token);
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, []);

  return <>{children}</>;
}

function RequireAuth({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-[var(--bg-primary)] text-[var(--text-secondary)]">
        Loading...
      </div>
    );
  }
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  return <>{children}</>;
}

export default function App() {
  return (
    <TokenHandler>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/auth/callback" element={<AuthCallback />} />
        <Route
          element={
            <RequireAuth>
              <Layout />
            </RequireAuth>
          }
        >
          <Route path="/" element={<Dashboard />} />
          <Route path="/sources" element={<Sources />} />
          <Route path="/pages" element={<Pages />} />
          <Route path="/pages/:id" element={<PageDetail />} />
          <Route path="/graph" element={<Graph />} />
          <Route path="/drift" element={<Drift />} />
          <Route path="/audit" element={<AuditLog />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/organization" element={<Organization />} />
          <Route path="/owner-explorer" element={<OwnerExplorer />} />
          <Route path="/admin" element={<Admin />} />
          <Route path="/search" element={<Search />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
      </Routes>
    </TokenHandler>
  );
}
