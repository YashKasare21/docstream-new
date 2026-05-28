import { Suspense } from "react";
import { Star, MessageSquare, BarChart2 } from "lucide-react";

interface FeedbackStats {
  total_count: number;
  average_rating: number;
  rating_distribution: Record<string, number>;
  recent_comments: string[];
}

const EMOJI_MAP: Record<string, string> = {
  "1": "😞",
  "2": "😐",
  "3": "😊",
  "4": "😄",
  "5": "🤩",
};

async function getStats(): Promise<FeedbackStats> {
  try {
    const apiBase =
      process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const res = await fetch(`${apiBase}/api/v2/feedback/stats`, {
      next: { revalidate: 60 },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  } catch {
    return {
      total_count: 0,
      average_rating: 0,
      rating_distribution: {},
      recent_comments: [],
    };
  }
}

function RatingBar({
  rating,
  count,
  max,
}: {
  rating: string;
  count: number;
  max: number;
}) {
  const pct = max > 0 ? Math.round((count / max) * 100) : 0;
  return (
    <div className="flex items-center gap-3">
      <span className="text-lg w-8 flex-shrink-0">{EMOJI_MAP[rating]}</span>
      <div className="flex-1 h-5 bg-white/[0.06] rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-blue-600 to-blue-400 rounded-full transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-sm text-slate-400 w-6 text-right flex-shrink-0">
        {count}
      </span>
    </div>
  );
}

async function StatsContent() {
  const stats = await getStats();
  const maxCount =
    Object.values(stats.rating_distribution).length > 0
      ? Math.max(...Object.values(stats.rating_distribution))
      : 0;

  return (
    <div className="min-h-screen relative text-slate-200">
      <div className="mesh-bg" aria-hidden="true" />

      <div className="max-w-2xl mx-auto px-4 sm:px-6 py-12 sm:py-20">
        <div className="mb-10">
          <h1 className="text-3xl sm:text-4xl font-bold text-white mb-2">
            Feedback Stats
          </h1>
          <p className="text-slate-400">
            Aggregated user ratings for Docstream conversions.
          </p>
        </div>

        {/* Summary cards */}
        <div className="grid grid-cols-2 gap-4 mb-8">
          <div className="glass-card p-5">
            <div className="flex items-center gap-2 mb-1 text-slate-400 text-sm">
              <BarChart2 className="w-4 h-4" />
              Total feedback
            </div>
            <p className="text-3xl font-bold text-white">
              {stats.total_count}
            </p>
          </div>

          <div className="glass-card p-5">
            <div className="flex items-center gap-2 mb-1 text-slate-400 text-sm">
              <Star className="w-4 h-4" />
              Average rating
            </div>
            <p className="text-3xl font-bold text-white">
              {stats.average_rating > 0
                ? stats.average_rating.toFixed(1)
                : "—"}
              <span className="text-lg text-slate-400 font-normal"> / 5</span>
            </p>
          </div>
        </div>

        {/* Distribution */}
        <div className="glass-card p-6 mb-6">
          <h2 className="text-base font-semibold text-white mb-4">
            Rating distribution
          </h2>
          {stats.total_count === 0 ? (
            <p className="text-sm text-slate-500">No ratings yet.</p>
          ) : (
            <div className="space-y-3">
              {["1", "2", "3", "4", "5"].map((r) => (
                <RatingBar
                  key={r}
                  rating={r}
                  count={stats.rating_distribution[r] ?? 0}
                  max={maxCount}
                />
              ))}
            </div>
          )}
        </div>

        {/* Recent comments */}
        <div className="glass-card p-6">
          <div className="flex items-center gap-2 mb-4">
            <MessageSquare className="w-4 h-4 text-slate-400" />
            <h2 className="text-base font-semibold text-white">
              Recent comments
            </h2>
          </div>
          {stats.recent_comments.length === 0 ? (
            <p className="text-sm text-slate-500">No comments yet.</p>
          ) : (
            <ul className="space-y-2">
              {stats.recent_comments.map((c, i) => (
                <li key={i} className="flex gap-2 text-sm text-slate-300">
                  <span className="text-slate-600 flex-shrink-0">•</span>
                  <span>&ldquo;{c}&rdquo;</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

export default function StatsPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center text-slate-400 text-sm">
          Loading stats…
        </div>
      }
    >
      <StatsContent />
    </Suspense>
  );
}
