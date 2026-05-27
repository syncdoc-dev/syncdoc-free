import { useState, useEffect } from "react";
import { getBillingStatus, createCheckoutSession, createPortalSession, getConfig } from "../api/client";
import type { BillingStatus, AppConfig } from "../types";

interface BillingGateProps {
  children: React.ReactNode;
}

export default function BillingGate({ children }: BillingGateProps) {
  const [billing, setBilling] = useState<BillingStatus | null>(null);
  const [config, setConfig] = useState<AppConfig["stripe"] | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      getBillingStatus().catch(() => null),
      getConfig().then((c) => c.stripe).catch(() => ({} as AppConfig["stripe"])),
    ])
      .then(([billingData, stripeConfig]) => {
        setBilling(billingData);
        setConfig(stripeConfig);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-[var(--bg-primary)] text-[var(--text-secondary)]">
        Loading...
      </div>
    );
  }

  // Billing not enabled — allow through
  if (!billing || !billing.billing_enabled) {
    return <>{children}</>;
  }

  // Active subscription, valid trial, paid subscription, or owner plan — allow through
  if (
    billing.status === "active" ||
    billing.stripe_subscription_id ||
    billing.plan === "owner" ||
    (billing.status === "trialing" && (billing.trial_days_remaining ?? 0) > 0)
  ) {
    return <>{children}</>;
  }

  // Needs payment — show subscribe screen
  const handleSubscribe = async (priceId: string, quantity = 1) => {
    if (!priceId) {
      alert("Price ID not configured. Please contact support.");
      return;
    }
    try {
      const { checkout_url } = await createCheckoutSession(priceId, quantity);
      window.location.href = checkout_url;
    } catch {
      alert("Could not start checkout. Please try again.");
    }
  };

  const isTrialExpired = billing.status === "trialing" && (billing.trial_days_remaining ?? 0) <= 0;
  const proPriceId = config && "pro_price_id" in config ? config.pro_price_id : "";
  const teamPriceId = config && "team_price_id" in config ? config.team_price_id : "";

  return (
    <div className="flex items-center justify-center min-h-screen bg-[var(--bg-primary)]">
      <div className="max-w-md w-full mx-4 p-8 rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)]">
        <div className="text-center mb-6">
          <h1 className="text-2xl font-bold text-[var(--text-primary)] mb-2">
            {isTrialExpired ? "Your trial has expired" : "Subscribe to SyncDoc"}
          </h1>
          <p className="text-[var(--text-secondary)]">
            {isTrialExpired
              ? "To continue using SyncDoc, please choose a plan."
              : billing.trial_days_remaining
                ? `Your ${billing.trial_days_remaining}-day trial is active. Subscribe now to keep full access.`
                : "Choose a plan to get started."}
          </p>
        </div>

        <div className="space-y-4">
          <div className="p-4 rounded border border-[var(--border-color)]">
            <div className="flex justify-between items-center mb-2">
              <span className="font-semibold text-[var(--text-primary)]">Pro</span>
              <span className="text-[var(--text-secondary)]">£10 / month</span>
            </div>
            <p className="text-sm text-[var(--text-secondary)] mb-3">
              Full access for individuals. 14-day free trial.
            </p>
            <button
              onClick={() => handleSubscribe(proPriceId)}
              className="w-full py-2 px-4 rounded bg-[var(--accent)] text-[var(--accent-text)] hover:opacity-90 transition-opacity"
            >
              Start Pro Trial
            </button>
          </div>

          <div className="p-4 rounded border border-[var(--border-color)]">
            <div className="flex justify-between items-center mb-2">
              <span className="font-semibold text-[var(--text-primary)]">Team</span>
              <span className="text-[var(--text-secondary)]">£9 / seat / month</span>
            </div>
            <p className="text-sm text-[var(--text-secondary)] mb-3">
              For teams of 2+. Collaborate with shared workspaces.
            </p>
            <button
              onClick={() => {
                const seats = parseInt(prompt("How many seats? (minimum 2)") || "2", 10);
                if (seats >= 2) {
                  handleSubscribe(teamPriceId, seats);
                }
              }}
              className="w-full py-2 px-4 rounded bg-[var(--accent)] text-[var(--accent-text)] hover:opacity-90 transition-opacity"
            >
              Start Team Subscription
            </button>
          </div>
        </div>

        {billing.status !== "trialing" && (
          <p className="text-center text-sm text-[var(--text-secondary)] mt-4">
            Already subscribed?{" "}
            <button
              onClick={async () => {
                try {
                  const { portal_url } = await createPortalSession();
                  window.location.href = portal_url;
                } catch {
                  alert("Could not open billing portal.");
                }
              }}
              className="underline hover:text-[var(--accent)]"
            >
              Manage billing
            </button>
          </p>
        )}
      </div>
    </div>
  );
}
