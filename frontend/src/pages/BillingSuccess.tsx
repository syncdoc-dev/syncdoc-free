import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

export default function BillingSuccess() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  useEffect(() => {
    const sessionId = searchParams.get("session_id");
    if (sessionId) {
      // Stripe will send webhook asynchronously; just redirect to app
      setTimeout(() => navigate("/"), 2000);
    } else {
      navigate("/");
    }
  }, [navigate, searchParams]);

  return (
    <div className="flex items-center justify-center min-h-screen bg-[var(--bg-primary)]">
      <div className="text-center">
        <h1 className="text-2xl font-bold text-[var(--text-primary)] mb-2">Payment successful!</h1>
        <p className="text-[var(--text-secondary)]">Redirecting you to SyncDoc...</p>
      </div>
    </div>
  );
}
