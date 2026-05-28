'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { CheckCircle, Download, FileCode, Zap, RotateCcw } from 'lucide-react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

interface ResultCardProps {
  texUrl: string
  pdfUrl: string
  processingTime?: number
  onConvertAnother: () => void
  jobId: string
  templateUsed?: string
  documentType?: string
}

const EMOJIS = [
  { value: 1, emoji: '😞', label: 'Poor' },
  { value: 2, emoji: '😐', label: 'Okay' },
  { value: 3, emoji: '😊', label: 'Good' },
  { value: 4, emoji: '😄', label: 'Great' },
  { value: 5, emoji: '🤩', label: 'Amazing' },
]

export default function ResultCard({
  texUrl,
  pdfUrl,
  processingTime,
  onConvertAnother,
  jobId,
  templateUsed,
  documentType,
}: ResultCardProps) {
  const [selectedEmoji, setSelectedEmoji] = useState<number | null>(null)
  const [comment, setComment] = useState('')
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const handleFeedbackSubmit = async () => {
    if (!selectedEmoji || submitting) return
    setSubmitting(true)
    try {
      await fetch(`${API_BASE}/api/v2/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          job_id: jobId,
          emoji_rating: selectedEmoji,
          comment: comment.trim() || null,
          template_used: templateUsed,
          document_type: documentType,
          processing_time: processingTime,
        }),
      })
    } catch {
      // Silently ignore — feedback is optional
    } finally {
      setSubmitting(false)
      setFeedbackSubmitted(true)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="glass-card border-t-2 border-t-green-500/60 p-8 w-full"
    >
      {/* Success header */}
      <div className="flex flex-col items-center text-center mb-8">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', stiffness: 200, damping: 12 }}
          className="w-16 h-16 rounded-full bg-green-500/10 border border-green-500/20 flex items-center justify-center mb-4 shadow-[0_0_30px_rgba(34,197,94,0.15)]"
        >
          <CheckCircle className="w-8 h-8 text-green-400" />
        </motion.div>

        <h2 className="text-xl font-semibold text-white mb-1">
          Conversion Complete
        </h2>

        {processingTime !== undefined && (
          <p className="text-sm text-slate-400 flex items-center gap-1.5">
            <Zap className="w-3.5 h-3.5 text-yellow-400" />
            Converted in {processingTime.toFixed(1)}s
          </p>
        )}

        {(documentType || templateUsed) && (
          <div className="flex items-center gap-3 mt-2">
            {documentType && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-300">
                {documentType.replace('_', ' ')}
              </span>
            )}
            {templateUsed && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-purple-500/10 border border-purple-500/20 text-purple-300">
                {templateUsed} template
              </span>
            )}
          </div>
        )}
      </div>

      {/* Download buttons */}
      <div className="flex gap-3 mb-8">
        <a
          href={texUrl}
          download="document.tex"
          className="flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-sm font-medium border border-white/10 hover:border-blue-500/40 text-slate-300 hover:text-blue-300 transition-all duration-200"
        >
          <FileCode className="w-4 h-4" />
          Download .tex
        </a>
        <a
          href={pdfUrl}
          download="document.pdf"
          className="flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-sm font-medium bg-blue-600 hover:bg-blue-500 text-white shadow-[0_0_20px_rgba(59,130,246,0.3)] transition-all duration-200 shimmer-btn"
        >
          <Download className="w-4 h-4" />
          Download .pdf
        </a>
      </div>

      {/* Divider */}
      <div className="border-t border-white/[0.06] mb-6" />

      {/* Feedback */}
      {feedbackSubmitted ? (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="flex flex-col items-center gap-2 py-2"
        >
          <CheckCircle className="w-6 h-6 text-green-400" />
          <p className="text-sm text-slate-300">Thanks for your feedback!</p>
        </motion.div>
      ) : (
        <div className="space-y-3">
          <p className="text-sm text-slate-400 text-center">How was the quality?</p>

          <div className="flex justify-center gap-2">
            {EMOJIS.map(({ value, emoji, label }) => (
              <button
                key={value}
                onClick={() => setSelectedEmoji(value)}
                title={label}
                className={`text-2xl p-2 rounded-xl transition-all duration-200 hover:scale-110 ${
                  selectedEmoji === value
                    ? 'ring-2 ring-blue-500 bg-blue-500/10 scale-110'
                    : 'hover:bg-white/[0.05]'
                }`}
              >
                {emoji}
              </button>
            ))}
          </div>

          {selectedEmoji && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              className="space-y-2"
            >
              <textarea
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="What could be better? (optional)"
                maxLength={500}
                rows={2}
                className="w-full px-3 py-2 rounded-xl text-sm bg-white/[0.04] border border-white/[0.08] text-slate-300 placeholder-slate-600 focus:outline-none focus:border-blue-500/40 resize-none"
              />
              <button
                onClick={handleFeedbackSubmit}
                disabled={submitting}
                className="w-full py-2 rounded-xl text-sm bg-white/[0.06] hover:bg-white/[0.10] text-slate-300 border border-white/[0.08] transition-all duration-200 disabled:opacity-50"
              >
                {submitting ? 'Submitting...' : 'Submit feedback'}
              </button>
            </motion.div>
          )}
        </div>
      )}

      {/* Divider */}
      <div className="border-t border-white/[0.06] mt-6 mb-6" />

      {/* Convert another */}
      <button
        onClick={onConvertAnother}
        className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm text-slate-400 hover:text-white hover:bg-white/[0.05] border border-transparent hover:border-white/[0.08] transition-all duration-200"
      >
        <RotateCcw className="w-4 h-4" />
        Convert Another PDF
      </button>
    </motion.div>
  )
}
