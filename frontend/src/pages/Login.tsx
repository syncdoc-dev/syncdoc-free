import { Github, Loader } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { apiFetch, getApiBase } from "../api/client";

type AuthMode = "login" | "register";

export default function Login() {
  const navigate = useNavigate();
  const { setToken } = useAuth();
  const [mode, setMode] = useState<AuthMode>("login");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [formData, setFormData] = useState({
    login: "",
    email: "",
    password: "",
    name: "",
    marketing_opt_in: false,
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value =
      e.target.type === "checkbox" ? e.target.checked : e.target.value;
    setFormData({ ...formData, [e.target.name]: value });
    setError("");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const path = mode === "login" ? "/auth/login" : "/auth/register";
      const payload =
        mode === "login"
          ? { login: formData.login, password: formData.password }
          : {
              login: formData.login,
              email: formData.email,
              password: formData.password,
              name: formData.name || null,
              marketing_opt_in: formData.marketing_opt_in,
            };

      const response = await apiFetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const contentType = response.headers.get("content-type") || "";
      if (contentType.includes("text/html")) {
        throw new Error("API endpoint misconfigured (received HTML). Check /api routing.");
      }

      if (!response.ok) {
        const data = await response.json();
        throw new Error(
          data.detail || "Authentication failed"
        );
      }

      const data = await response.json();
      setToken(data.access_token);
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-[var(--bg-primary)]">
      <div className="w-full max-w-sm">
        {/* Logo / Brand */}
        <div className="flex items-center justify-center gap-3 mb-8">
          <img
            src="/branding/syncdoc-logo.png"
            alt="SyncDoc logo"
            className="w-8 h-8 rounded-md object-contain"
          />
          <span className="text-2xl font-semibold tracking-tight text-[var(--text-white)]">
            SyncDoc
          </span>
        </div>

        {/* Card */}
        <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-8">
          <h1 className="text-lg font-semibold text-[var(--text-white)] text-center mb-1">
            {mode === "login" ? "Sign in" : "Create account"}
          </h1>
          <p className="text-sm text-[var(--text-secondary)] text-center mb-6">
            Infrastructure-aware living documentation for your team
          </p>

          {/* Tabs */}
          <div className="flex gap-2 mb-6 border-b border-[var(--border)]">
            <button
              onClick={() => {
                setMode("login");
                setError("");
                setFormData({
                  login: "",
                  email: "",
                  password: "",
                  name: "",
                  marketing_opt_in: false,
                });
              }}
              className={`flex-1 pb-2 text-sm font-medium transition-colors ${
                mode === "login"
                  ? "text-[var(--accent)] border-b-2 border-[var(--accent)]"
                  : "text-[var(--text-secondary)] hover:text-[var(--text-white)]"
              }`}
            >
              Login
            </button>
            <button
              onClick={() => {
                setMode("register");
                setError("");
                setFormData({
                  login: "",
                  email: "",
                  password: "",
                  name: "",
                  marketing_opt_in: false,
                });
              }}
              className={`flex-1 pb-2 text-sm font-medium transition-colors ${
                mode === "register"
                  ? "text-[var(--accent)] border-b-2 border-[var(--accent)]"
                  : "text-[var(--text-secondary)] hover:text-[var(--text-white)]"
              }`}
            >
              Register
            </button>
          </div>

          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
              {error}
            </div>
          )}

          {/* Local Auth Form */}
          <form onSubmit={handleSubmit} className="mb-4 space-y-3">
            <div>
              <label className="block text-sm font-medium text-[var(--text-white)] mb-1">
                {mode === "login" ? "Username or Email" : "Username"}
              </label>
              <input
                type="text"
                name="login"
                value={formData.login}
                onChange={handleChange}
                required
                minLength={3}
                maxLength={50}
                className="w-full px-3 py-2 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border)] text-[var(--text-white)] placeholder-[var(--text-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)] focus:border-transparent"
                placeholder={mode === "login" ? "Username or email" : "Username"}
              />
            </div>

            {mode === "register" && (
              <>
                <div>
                  <label className="block text-sm font-medium text-[var(--text-white)] mb-1">
                    Email
                  </label>
                  <input
                    type="email"
                    name="email"
                    value={formData.email}
                    onChange={handleChange}
                    required
                    className="w-full px-3 py-2 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border)] text-[var(--text-white)] placeholder-[var(--text-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)] focus:border-transparent"
                    placeholder="your@email.com"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[var(--text-white)] mb-1">
                    Name (optional)
                  </label>
                  <input
                    type="text"
                    name="name"
                    value={formData.name}
                    onChange={handleChange}
                    maxLength={100}
                    className="w-full px-3 py-2 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border)] text-[var(--text-white)] placeholder-[var(--text-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)] focus:border-transparent"
                    placeholder="Your Full Name"
                  />
                </div>
                <label className="flex items-start gap-3 rounded-lg border border-[var(--border)] bg-[var(--bg-secondary)] p-3 text-sm text-[var(--text-secondary)]">
                  <input
                    type="checkbox"
                    name="marketing_opt_in"
                    checked={formData.marketing_opt_in}
                    onChange={handleChange}
                    className="mt-1 h-4 w-4 rounded border-[var(--border)] bg-[var(--bg-card)] text-[var(--accent)] focus:ring-[var(--accent)]"
                  />
                  <span>
                    I agree to receive product updates and marketing emails from SyncDoc.
                    Registration details may also be used for internal sign-up notifications.
                  </span>
                </label>
              </>
            )}

            <div>
              <label className="block text-sm font-medium text-[var(--text-white)] mb-1">
                Password
              </label>
              <input
                type="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                required
                minLength={8}
                maxLength={72}
                className="w-full px-3 py-2 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border)] text-[var(--text-white)] placeholder-[var(--text-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)] focus:border-transparent"
                placeholder="••••••••"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full px-4 py-2.5 rounded-lg bg-[var(--accent-bg)] text-[var(--accent)] border border-[var(--border)] text-sm font-medium hover:bg-[var(--hover-bg)] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {loading && <Loader className="w-4 h-4 animate-spin" />}
              {mode === "login" ? "Sign in" : "Create account"}
            </button>
          </form>

          {mode === "login" && (
            <p className="mb-4 text-right text-xs text-[var(--text-secondary)]">
              <Link to="/forgot-password" className="text-[var(--accent)] hover:underline">
                Forgot password?
              </Link>
            </p>
          )}

          {/* Divider */}
          <div className="relative mb-4">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-[var(--border)]"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-[var(--bg-card)] text-[var(--text-secondary)]">
                or
              </span>
            </div>
          </div>

          {/* GitHub OAuth */}
          <a
            href={`${getApiBase()}/auth/github`}
            className="flex items-center justify-center gap-2 w-full px-4 py-2.5 rounded-lg bg-[var(--accent-bg)] text-[var(--accent)] border border-[var(--border)] text-sm font-medium hover:bg-[var(--hover-bg)] transition-colors"
          >
            <Github className="w-4 h-4" />
            {mode === "login"
              ? "Login with GitHub"
              : "Register with GitHub"}
          </a>
        </div>

        {/* Footer */}
        <p className="text-xs text-[var(--text-secondary)] text-center mt-4">
          {mode === "login"
            ? "Don't have an account? "
            : "Already have an account? "}
          <button
            onClick={() => {
              setMode(mode === "login" ? "register" : "login");
              setError("");
              setFormData({
                login: "",
                email: "",
                password: "",
                name: "",
                marketing_opt_in: false,
              });
            }}
            className="text-[var(--accent)] hover:underline"
          >
            {mode === "login" ? "Register" : "Sign in"}
          </button>
        </p>
      </div>
    </div>
  );
}
