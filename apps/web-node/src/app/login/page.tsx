"use client";

import { useState, FormEvent, Suspense } from "react";
import { signIn } from "next-auth/react";
import { useRouter, useSearchParams } from "next/navigation";
import { LogIn } from "lucide-react";

/**
 * Demo login form. NextAuth's Credentials provider only requires an
 * email — any well-formed value authenticates the user. The form
 * surfaces a "Sign in" button and a single email input.
 */
function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const callbackUrl = searchParams.get("callbackUrl") ?? "/convert";
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    setPending(true);
    const result = await signIn("credentials", {
      email,
      redirect: false,
      callbackUrl,
    });
    setPending(false);
    if (!result || result.error) {
      setError(result?.error ?? "Sign-in failed. Please try again.");
      return;
    }
    router.push(callbackUrl);
  };

  return (
    <main className="min-h-screen pt-24 px-4 sm:px-6 lg:px-8 flex items-center justify-center">
      <div className="w-full max-w-md rounded-xl border border-border bg-surface/60 backdrop-blur p-8 space-y-6">
        <div className="space-y-1 text-center">
          <LogIn className="w-8 h-8 text-blue-400 mx-auto" />
          <h1 className="text-2xl font-bold text-foreground">Sign in</h1>
          <p className="text-sm text-muted-foreground">
            Demo mode — any email will sign you in.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label
              htmlFor="email"
              className="text-sm font-medium text-foreground"
            >
              Email
            </label>
            <input
              id="email"
              name="email"
              type="email"
              required
              autoComplete="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-border bg-background/60 px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/60 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            />
          </div>

          {error && (
            <p className="text-sm text-red-400" role="alert">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={pending || !email}
            className="w-full rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white px-4 py-2.5 text-sm font-medium transition-colors"
          >
            {pending ? "Signing in…" : "Sign In"}
          </button>
        </form>
      </div>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <main className="min-h-screen pt-24 px-4 sm:px-6 lg:px-8 flex items-center justify-center text-muted-foreground">
          Loading…
        </main>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
