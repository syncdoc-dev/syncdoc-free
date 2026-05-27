import { useNavigate } from "react-router-dom";

export default function BillingCanceled() {
  const navigate = useNavigate();

  return (
    <div className="flex items-center justify-center min-h-screen bg-[var(--bg-primary)]">
      <div className="text-center max-w-md mx-4">
        <h1 className="text-2xl font-bold text-[var(--text-primary)] mb-2">Payment canceled</h1>
        <p className="text-[var(--text-secondary)] mb-6">
          You can subscribe anytime from your settings.
        </p>
        <button
          onClick={() => navigate("/")}
          className="py-2 px-4 rounded bg-[var(--accent)] text-[var(--accent-text)] hover:opacity-90 transition-opacity"
        >
          Go to Dashboard
        </button>
      </div>
    </div>
  );
}
