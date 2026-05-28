"use client";

import { useEffect } from "react";
import { AlertTriangle, RefreshCcw } from "lucide-react";

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function ErrorPage({ error, reset }: ErrorPageProps) {
  useEffect(() => {
    // Log to observability (Sentry etc.) in production
    // eslint-disable-next-line no-console
    console.error(error);
  }, [error]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-6 px-4">
      <div className="w-14 h-14 rounded-full bg-red-500/10 flex items-center justify-center">
        <AlertTriangle className="w-7 h-7 text-red-400" />
      </div>

      <div className="text-center space-y-2 max-w-md">
        <h1 className="text-2xl font-bold text-white">Something went wrong</h1>
        <p className="text-slate-400 text-sm leading-relaxed">
          {error.message || "An unexpected error occurred. Please try again."}
        </p>
      </div>

      <button
        onClick={reset}
        className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-xl transition-all duration-200"
      >
        <RefreshCcw className="w-4 h-4" />
        Try Again
      </button>
    </div>
  );
}
