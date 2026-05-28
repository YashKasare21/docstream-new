"use client";

import { useRef, useState, useCallback } from "react";
import { CloudUpload, FileText, CheckCircle, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";

type DropZoneState = "idle" | "dragging" | "selected" | "uploading";

interface DropZoneProps {
  file: File | null;
  onFileSelect: (file: File) => void;
  onFileRemove: () => void;
  state?: DropZoneState;
  /** MIME type to accept — defaults to "application/pdf" */
  acceptedMime?: string;
  /** File extension label — defaults to ".pdf" */
  acceptedExt?: string;
  /** Short label for the "X only" badge — defaults to "PDF only" */
  acceptedLabel?: string;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

/** Truncate long filenames to keep the layout clean. */
function truncateFilename(name: string, max = 28): string {
  if (name.length <= max) return name;
  const ext = name.slice(name.lastIndexOf("."));
  return name.slice(0, max - ext.length - 3) + "..." + ext;
}

export default function DropZone({
  file,
  onFileSelect,
  onFileRemove,
  state: externalState,
  acceptedMime = "application/pdf",
  acceptedExt = ".pdf",
  acceptedLabel = "PDF only",
}: DropZoneProps) {
  const [internalDragging, setInternalDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const currentState: DropZoneState =
    externalState === "uploading"
      ? "uploading"
      : internalDragging
        ? "dragging"
        : file
          ? "selected"
          : "idle";

  const validateFile = useCallback(
    (f: File): boolean => {
      // Accept any MIME that matches, or fall back to extension check
      const extMatch = f.name.toLowerCase().endsWith(acceptedExt);
      const mimeMatch = f.type === acceptedMime || f.type === "";
      if (!extMatch && !mimeMatch) {
        alert(`Only ${acceptedLabel} files are accepted.`);
        return false;
      }
      if (f.size > 20 * 1024 * 1024) {
        alert("File size must be under 20 MB.");
        return false;
      }
      onFileSelect(f);
      return true;
    },
    [onFileSelect, acceptedMime, acceptedExt, acceptedLabel]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setInternalDragging(false);
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile) validateFile(droppedFile);
    },
    [validateFile]
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const selected = e.target.files?.[0];
      if (selected) validateFile(selected);
    },
    [validateFile]
  );

  const borderClass =
    currentState === "dragging"
      ? "border-blue-400/70 border-solid bg-blue-950/30 shadow-[0_0_60px_rgba(59,130,246,0.2),inset_0_0_60px_rgba(59,130,246,0.08)]"
      : currentState === "selected"
        ? "border-green-500/30 bg-white/[0.02]"
        : "border-slate-700/60 bg-slate-900/40 hover:border-blue-500/50 hover:bg-blue-950/20 hover:shadow-[0_0_40px_rgba(59,130,246,0.12),inset_0_0_40px_rgba(59,130,246,0.04)]";

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setInternalDragging(true);
      }}
      onDragLeave={() => setInternalDragging(false)}
      onDrop={handleDrop}
      onClick={() => currentState === "idle" && inputRef.current?.click()}
      className={`relative rounded-2xl border-2 border-dashed flex flex-col items-center justify-center p-12 cursor-pointer transition-all duration-300 ${borderClass}`}
    >
      <input
        ref={inputRef}
        type="file"
        accept={`${acceptedMime},${acceptedExt}`}
        onChange={handleChange}
        className="hidden"
      />

      <AnimatePresence mode="wait">
        {/* ── Idle / Dragging ── */}
        {(currentState === "idle" || currentState === "dragging") && (
          <motion.div
            key="idle"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex flex-col items-center text-center gap-4"
          >
            <motion.div
              animate={
                currentState === "dragging"
                  ? { scale: 1.15, rotate: [0, -5, 5, 0], y: 0 }
                  : { y: [0, -6, 0], scale: 1 }
              }
              transition={
                currentState === "dragging"
                  ? { duration: 0.3 }
                  : { duration: 3, repeat: Infinity, ease: "easeInOut" }
              }
              className={`w-16 h-16 rounded-2xl flex items-center justify-center transition-colors duration-300 ${
                currentState === "dragging"
                  ? "bg-blue-500/20"
                  : "bg-blue-500/10"
              }`}
            >
              <CloudUpload className="w-14 h-14 text-blue-400" />
            </motion.div>
            <div>
              <p className="text-lg font-semibold text-white">
                {currentState === "dragging"
                  ? "Release to upload"
                  : "Drop your PDF here"}
              </p>
              <div className="flex items-center gap-2 flex-wrap justify-center mt-3">
                <span className="flex items-center gap-1.5 text-xs text-slate-400 bg-white/[0.04] border border-white/[0.08] rounded-full px-3 py-1">
                  {acceptedLabel}
                </span>
                <span className="flex items-center gap-1.5 text-xs text-slate-400 bg-white/[0.04] border border-white/[0.08] rounded-full px-3 py-1">
                  Max 10 MB
                </span>
                <span className="flex items-center gap-1.5 text-xs text-slate-400 bg-white/[0.04] border border-white/[0.08] rounded-full px-3 py-1">
                  Click or drag
                </span>
              </div>
            </div>
          </motion.div>
        )}

        {/* ── Selected ── */}
        {currentState === "selected" && file && (
          <motion.div
            key="selected"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="glass-card p-4 flex items-center gap-4 w-full max-w-sm"
          >
            <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-red-500/20 border border-red-500/30 flex items-center justify-center">
              <FileText className="w-5 h-5 text-red-400" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">
                {truncateFilename(file.name)}
              </p>
              <p className="text-sm text-slate-400">
                {formatFileSize(file.size)}
              </p>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <CheckCircle className="w-5 h-5 text-green-500" />
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onFileRemove();
                  if (inputRef.current) inputRef.current.value = "";
                }}
                className="w-8 h-8 rounded-lg bg-white/[0.06] hover:bg-white/[0.1] flex items-center justify-center transition-colors group"
              >
                <X className="w-4 h-4 text-slate-400 group-hover:text-red-400 transition-colors" />
              </button>
            </div>
          </motion.div>
        )}

        {/* ── Uploading ── */}
        {currentState === "uploading" && (
          <motion.div
            key="uploading"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex flex-col items-center gap-4"
          >
            <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-sm font-medium text-slate-300">Uploading...</p>
            <div className="w-full h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-gradient-to-r from-blue-500 to-purple-500 rounded-full shadow-[0_0_8px_rgba(59,130,246,0.8)]"
                initial={{ width: "0%" }}
                animate={{ width: "100%" }}
                transition={{ duration: 2, ease: "easeInOut" }}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
