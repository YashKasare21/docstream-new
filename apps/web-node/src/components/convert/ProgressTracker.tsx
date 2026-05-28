"use client";

import { useEffect, useState } from "react";
import { Clock, Check, Loader2 } from "lucide-react";
import { motion } from "framer-motion";

const TOTAL_MS = 13000;

const stages = [
  {
    label: "Extracting PDF content",
    subtext: "PyMuPDF parsing text, images and tables",
    startAt: 0,
    endAt: 3000,
  },
  {
    label: "AI structuring document",
    subtext: "Gemini Flash building structured document AST",
    startAt: 3000,
    endAt: 8000,
  },
  {
    label: "Rendering LaTeX",
    subtext: "Pandoc + XeLaTeX compiling publication output",
    startAt: 8000,
    endAt: TOTAL_MS,
  },
];

export default function ProgressTracker() {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const start = Date.now();
    const interval = setInterval(() => {
      setElapsed(Date.now() - start);
    }, 100);
    return () => clearInterval(interval);
  }, []);

  /** 0–100 clamped progress percentage */
  const pct = Math.min((elapsed / TOTAL_MS) * 100, 100);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="glass-card p-6 space-y-6"
    >
      {/* Glowing progress bar */}
      <div className="h-0.5 bg-white/[0.06] rounded-full overflow-hidden mb-8">
        <motion.div
          className="h-full bg-gradient-to-r from-blue-500 to-purple-500 rounded-full shadow-[0_0_8px_rgba(59,130,246,0.8)]"
          initial={{ width: "0%" }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.3, ease: "linear" }}
        />
      </div>

      {/* Stages */}
      <div className="space-y-1">
        {stages.map((stage, i) => {
          const status =
            elapsed >= stage.endAt
              ? "done"
              : elapsed >= stage.startAt
                ? "active"
                : "pending";

          return (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.1 }}
              className={`flex items-start gap-4 p-4 rounded-xl transition-all duration-300 ${
                status === "active"
                  ? "bg-blue-500/10 border border-blue-500/20"
                  : "bg-transparent"
              }`}
            >
              {/* Icon */}
              <div className="flex-shrink-0 mt-0.5">
                {status === "done" ? (
                  <div className="w-8 h-8 rounded-full bg-green-500/20 border border-green-500/40 flex items-center justify-center">
                    <Check className="w-4 h-4 text-green-400" />
                  </div>
                ) : status === "active" ? (
                  <motion.div
                    animate={{
                      boxShadow: [
                        "0 0 0 0 rgba(59,130,246,0.6)",
                        "0 0 0 8px rgba(59,130,246,0)",
                      ],
                    }}
                    transition={{ repeat: Infinity, duration: 1.2 }}
                    className="w-8 h-8 rounded-full bg-blue-500/20 border border-blue-500 flex items-center justify-center"
                  >
                    <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
                  </motion.div>
                ) : (
                  <div className="w-8 h-8 rounded-full bg-white/[0.04] border border-white/[0.1] flex items-center justify-center">
                    <Clock className="w-4 h-4 text-slate-500" />
                  </div>
                )}
              </div>

              {/* Text */}
              <div>
                <p
                  className={`text-sm font-medium ${
                    status === "done"
                      ? "text-green-400"
                      : status === "active"
                        ? "text-white"
                        : "text-slate-500"
                  }`}
                >
                  {stage.label}
                </p>
                <p
                  className={`text-xs mt-0.5 ${
                    status === "active" ? "text-slate-400" : "text-slate-600"
                  }`}
                >
                  {stage.subtext}
                </p>
              </div>
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
}
