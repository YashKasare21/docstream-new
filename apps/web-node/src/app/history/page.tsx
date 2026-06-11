"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import Link from "next/link";
import { History as HistoryIcon, Download, LogIn } from "lucide-react";
import { fetchJobs, type JobRow } from "@/lib/api";

/**
 * Job history for the signed-in user.
 *
 * Uses the ``fetchJobs()`` helper which automatically attaches the
 * JWT Bearer token via the token proxy. The backend filters jobs by
 * the authenticated user's email, preventing IDOR attacks.
 */

interface JobsResponse {
  count: number;
  jobs: JobRow[];
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function statusBadgeClass(status: string): string {
  switch (status) {
    case "completed":
      return "bg-emerald-500/15 text-emerald-300 border-emerald-500/30";
    case "failed":
      return "bg-red-500/15 text-red-300 border-red-500/30";
    case "processing":
      return "bg-amber-500/15 text-amber-300 border-amber-500/30";
    default:
      return "bg-slate-500/15 text-slate-300 border-slate-500/30";
  }
}

export default function HistoryPage() {
  const { data: session, status } = useSession();
  const [jobs, setJobs] = useState<JobRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const userEmail = session?.user?.email ?? null;

  useEffect(() => {
    if (status !== "authenticated" || !userEmail) return;
    const controller = new AbortController();
    const loadJobs = async () => {
      setLoading(true);
      setError(null);
      try {
        const data: JobsResponse = await fetchJobs();
        setJobs(data.jobs ?? []);
      } catch (err) {
        if ((err as Error).name === "AbortError") return;
        setError((err as Error).message);
      } finally {
        setLoading(false);
      }
    };
    loadJobs();
    return () => controller.abort();
  }, [status, userEmail]);

  if (status === "loading") {
    return (
      <main className="min-h-screen pt-24 px-4 sm:px-6 lg:px-8">
        <div className="max-w-6xl mx-auto text-muted-foreground">Loading…</div>
      </main>
    );
  }

  if (status !== "authenticated" || !userEmail) {
    return (
      <main className="min-h-screen pt-24 px-4 sm:px-6 lg:px-8">
        <div className="max-w-2xl mx-auto text-center space-y-6 py-20">
          <HistoryIcon className="w-12 h-12 text-blue-400 mx-auto" />
          <h1 className="text-3xl font-bold text-foreground">Sign in to see your history</h1>
          <p className="text-muted-foreground">
            Your conversions are saved and linked to your email address.
            Sign in to view them anytime.
          </p>
          <Link
            href="/login"
            className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-5 py-2.5 rounded-lg text-sm font-medium transition-colors"
          >
            <LogIn className="w-4 h-4" />
            Sign In
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen pt-24 px-4 sm:px-6 lg:px-8 pb-16">
      <div className="max-w-6xl mx-auto space-y-6">
        <header className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <h1 className="text-3xl font-bold text-foreground flex items-center gap-2">
              <HistoryIcon className="w-7 h-7 text-blue-400" />
              Your Conversions
            </h1>
            <p className="text-muted-foreground mt-1 text-sm">
              Signed in as <span className="text-foreground">{userEmail}</span>
            </p>
          </div>
          <Link
            href="/convert"
            className="shimmer-btn bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            New Conversion
          </Link>
        </header>

        {loading && (
          <div className="text-muted-foreground">Loading your jobs…</div>
        )}

        {error && (
          <div className="rounded-lg border border-red-500/40 bg-red-500/10 text-red-300 px-4 py-3 text-sm">
            Failed to load history: {error}
          </div>
        )}

        {!loading && !error && jobs.length === 0 && (
          <div className="rounded-xl border border-border bg-surface/50 backdrop-blur p-10 text-center">
            <p className="text-muted-foreground">
              No conversions yet. Head over to{" "}
              <Link href="/convert" className="text-blue-400 hover:underline">
                Convert
              </Link>{" "}
              to run your first one.
            </p>
          </div>
        )}

        {jobs.length > 0 && (
          <div className="overflow-x-auto rounded-xl border border-border bg-surface/50 backdrop-blur">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-muted-foreground border-b border-border">
                  <th className="px-4 py-3 font-medium">Input File</th>
                  <th className="px-4 py-3 font-medium">Template</th>
                  <th className="px-4 py-3 font-medium">Output</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Date</th>
                  <th className="px-4 py-3 font-medium text-right">Download</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr
                    key={job.id}
                    className="border-b border-border/50 last:border-0 hover:bg-accent/30 transition-colors"
                  >
                    <td className="px-4 py-3 text-foreground font-mono text-xs max-w-[260px] truncate" title={job.input_filename}>
                      {job.input_filename}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">{job.template}</td>
                    <td className="px-4 py-3 text-muted-foreground uppercase text-xs">
                      {job.output_format}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-block text-xs px-2 py-0.5 rounded-full border ${statusBadgeClass(job.status)}`}
                        title={job.error_message ?? undefined}
                      >
                        {job.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground text-xs">
                      {formatDate(job.created_at)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {job.status === "completed" && job.pdf_url ? (
                        <a
                          href={`${process.env.NEXT_PUBLIC_API_BASE_URL ?? ""}${job.pdf_url}`}
                          className="inline-flex items-center gap-1 text-blue-400 hover:text-blue-300 text-xs"
                          download
                        >
                          <Download className="w-3.5 h-3.5" />
                          PDF
                        </a>
                      ) : job.status === "completed" && job.tex_url ? (
                        <a
                          href={`${process.env.NEXT_PUBLIC_API_BASE_URL ?? ""}${job.tex_url}`}
                          className="inline-flex items-center gap-1 text-blue-400 hover:text-blue-300 text-xs"
                          download
                        >
                          <Download className="w-3.5 h-3.5" />
                          TeX
                        </a>
                      ) : (
                        <span className="text-muted-foreground/60 text-xs">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </main>
  );
}
