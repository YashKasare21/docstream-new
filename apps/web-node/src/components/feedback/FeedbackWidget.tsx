"use client";

/**
 * FeedbackWidget — shown after a successful conversion.
 *
 * TODO (Phase 14):
 * - Emoji picker: 😞 😐 😊 😄 🤩
 * - Optional text comment (max 500 chars)
 * - Submit button → POST /api/v2/feedback
 * - Show confirmation on success, error message on failure
 */

interface FeedbackWidgetProps {
  /** The job_id of the completed conversion. */
  jobId: string;
}

export default function FeedbackWidget({ jobId: _jobId }: FeedbackWidgetProps) {
  return (
    <div className="text-muted text-xs text-center p-4 border border-dashed border-border rounded-lg">
      Feedback Widget — Coming in Phase 14
    </div>
  );
}
