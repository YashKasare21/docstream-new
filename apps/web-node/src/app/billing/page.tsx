"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";
import Link from "next/link";
import { CreditCard, CheckCircle, AlertTriangle, ArrowLeft } from "lucide-react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function BillingPage() {
  const { data: session, status } = useSession();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const userEmail = session?.user?.email ?? null;
  const isAuthenticated = status === "authenticated";

  const handleUpgrade = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/v2/billing/checkout`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${await getClientToken()}`,
        },
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error((err as { detail?: string }).detail ?? `Server error: ${res.status}`);
      }
      const data = await res.json();
      if (data.url) {
        window.location.href = data.url;
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "An unexpected error occurred.");
    } finally {
      setLoading(false);
    }
  };

  if (status === "loading") {
    return (
      <main className="min-h-screen pt-24 px-4 sm:px-6 lg:px-8">
        <div className="max-w-2xl mx-auto text-muted-foreground">Loading…</div>
      </main>
    );
  }

  if (!isAuthenticated || !userEmail) {
    return (
      <main className="min-h-screen pt-24 px-4 sm:px-6 lg:px-8">
        <div className="max-w-2xl mx-auto text-center space-y-6 py-20">
          <CreditCard className="w-12 h-12 text-blue-400 mx-auto" />
          <h1 className="text-3xl font-bold text-foreground">Sign in to manage billing</h1>
          <p className="text-muted-foreground">
            You need to sign in before you can upgrade to Pro.
          </p>
          <Link
            href="/login"
            className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-5 py-2.5 rounded-lg text-sm font-medium transition-colors"
          >
            Sign In
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen pt-24 px-4 sm:px-6 lg:px-8 pb-16">
      <div className="max-w-2xl mx-auto">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors mb-8"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to home
        </Link>

        <div className="space-y-8">
          {/* Header */}
          <div>
            <h1 className="text-3xl font-bold text-foreground flex items-center gap-2">
              <CreditCard className="w-7 h-7 text-blue-400" />
              Billing
            </h1>
            <p className="text-muted-foreground mt-1 text-sm">
              Signed in as <span className="text-foreground">{userEmail}</span>
            </p>
          </div>

          {/* Current Plan */}
          <div className="rounded-xl border border-border bg-surface/50 backdrop-blur p-6 space-y-4">
            <h2 className="text-lg font-semibold text-foreground">Current Plan</h2>
            <div className="flex items-center gap-3">
              <span className="text-sm px-3 py-1 rounded-full bg-blue-500/15 text-blue-300 border border-blue-500/30">
                Free
              </span>
              <span className="text-sm text-muted-foreground">
                5 conversions per month
              </span>
            </div>
          </div>

          {/* Pro Plan */}
          <div className="rounded-xl border border-blue-500/30 bg-blue-500/5 backdrop-blur p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-foreground flex items-center gap-2">
                  Pro Plan
                  <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/15 text-blue-300 border border-blue-500/30">
                    Recommended
                  </span>
                </h2>
                <p className="text-muted-foreground text-sm mt-1">
                  Unlimited conversions, priority support, and early access to new features.
                </p>
              </div>
            </div>

            <ul className="space-y-2">
              {[
                "Unlimited document conversions",
                "All templates and output formats",
                "Priority support",
                "No usage limits",
              ].map((feature) => (
                <li key={feature} className="flex items-center gap-2 text-sm text-foreground">
                  <CheckCircle className="w-4 h-4 text-blue-400 flex-shrink-0" />
                  {feature}
                </li>
              ))}
            </ul>

            {error && (
              <div className="flex items-start gap-2 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300 text-sm">
                <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            <button
              onClick={handleUpgrade}
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:opacity-60 disabled:cursor-not-allowed text-white font-semibold text-base transition-all duration-200 shadow-lg shadow-blue-900/20"
            >
              {loading ? "Redirecting to Stripe…" : "Upgrade to Pro"}
            </button>
          </div>
        </div>
      </div>
    </main>
  );
}

/**
 * Fetch the auth token from the Next.js token proxy.
 * Duplicated here to keep this page self-contained.
 */
async function getClientToken(): Promise<string> {
  const res = await fetch("/api/auth/token");
  if (!res.ok) throw new Error("Not authenticated");
  const data = await res.json();
  return data.token ?? "";
}
