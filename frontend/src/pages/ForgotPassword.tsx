import { Loader } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { forgotPassword } from "../api/client";

export default function ForgotPassword() {
  const [loginOrEmail, setLoginOrEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setMessage("");

    try {
      const response = await forgotPassword(loginOrEmail.trim());
      setMessage(response.detail);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to send reset email");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-[var(--bg-primary)]">
      <div className="w-full max-w-sm rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-8">
        <h1 className="mb-2 text-lg font-semibold text-[var(--text-white)]">Forgot Password</h1>
        <p className="mb-6 text-sm text-[var(--text-secondary)]">
          Enter your username or email and we&apos;ll send you a reset link.
        </p>

        {error && (
          <div className="mb-4 rounded-lg border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-400">
            {error}
          </div>
        )}
        {message && (
          <div className="mb-4 rounded-lg border border-[var(--border)] bg-[var(--bg-secondary)] p-3 text-sm text-[var(--text-white)]">
            {message}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-[var(--text-white)]">
              Username or Email
            </label>
            <input
              type="text"
              value={loginOrEmail}
              onChange={(e) => setLoginOrEmail(e.target.value)}
              required
              className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg-secondary)] px-3 py-2 text-[var(--text-white)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
              placeholder="you@example.com"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="flex w-full items-center justify-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--accent-bg)] px-4 py-2.5 text-sm font-medium text-[var(--accent)] transition-colors hover:bg-[var(--hover-bg)] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading && <Loader className="h-4 w-4 animate-spin" />}
            Send reset email
          </button>
        </form>

        <p className="mt-4 text-center text-xs text-[var(--text-secondary)]">
          <Link to="/login" className="text-[var(--accent)] hover:underline">
            Back to sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
