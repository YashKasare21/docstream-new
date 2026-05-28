"use client";

import { XCircle, RotateCcw, ExternalLink } from "lucide-react";
import { motion } from "framer-motion";

interface ErrorCardProps {
  message: string;
  onRetry: () => void;
}

export default function ErrorCard({ message, onRetry }: ErrorCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="rounded-2xl border border-red-500/30 bg-slate-900/60 p-8 text-center"
    >
      {/* Error header */}
      <div className="flex flex-col items-center gap-3 mb-6">
        <div className="w-14 h-14 rounded-full bg-red-500/10 flex items-center justify-center">
          <XCircle className="w-8 h-8 text-red-500" />
        </div>
        <h3 className="text-xl font-bold text-white">Conversion Failed</h3>
        <p className="text-sm text-slate-400 max-w-sm">{message}</p>
      </div>

      {/* Actions */}
      <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
        <button
          onClick={onRetry}
          className="flex items-center gap-2 px-5 py-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-medium transition-all duration-200"
        >
          <RotateCcw className="w-4 h-4" />
          Try Again
        </button>
        <a
          href="https://github.com/YashKasare21/docstream-web/issues"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 text-sm text-slate-400 hover:text-white transition-colors duration-200"
        >
          <ExternalLink className="w-4 h-4" />
          Report Issue
        </a>
      </div>
    </motion.div>
  );
}
