"use client";

import { useReducer, useState, useCallback, useEffect } from "react";
import { ArrowLeft, ArrowRight, AlertTriangle } from "lucide-react";
import Link from "next/link";
import DropZone from "@/components/convert/DropZone";
import TemplateSelector from "@/components/convert/TemplateSelector";
import ProgressTracker from "@/components/convert/ProgressTracker";
import ErrorCard from "@/components/convert/ErrorCard";
import ResultCard from "@/components/convert/ResultCard";
import FormatSelector, { FORMAT_OPTIONS } from "@/components/convert/FormatSelector";
import { convertDocument, checkHealth, type ConvertResult } from "@/lib/api";

// ── State machine ──────────────────────────────────────────────────────────────
type State =
  | { status: "idle" }
  | { status: "file_selected"; file: File }
  | { status: "processing"; file: File; template: string }
  | { status: "complete"; result: ConvertResult }
  | { status: "error"; message: string };

type Action =
  | { type: "SELECT_FILE"; file: File }
  | { type: "REMOVE_FILE" }
  | { type: "START_PROCESSING"; template: string }
  | { type: "COMPLETE"; result: ConvertResult }
  | { type: "FAIL"; message: string }
  | { type: "RESET" };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "SELECT_FILE":
      return { status: "file_selected", file: action.file };
    case "REMOVE_FILE":
      return { status: "idle" };
    case "START_PROCESSING":
      if (state.status !== "file_selected") return state;
      return { status: "processing", file: state.file, template: action.template };
    case "COMPLETE":
      return { status: "complete", result: action.result };
    case "FAIL":
      return { status: "error", message: action.message };
    case "RESET":
      return { status: "idle" };
    default:
      return state;
  }
}

export default function ConvertPage() {
  const [state, dispatch] = useReducer(reducer, { status: "idle" });
  const [template, setTemplate] = useState("report");
  const [selectedFormat, setSelectedFormat] = useState(".pdf");
  const [backendUp, setBackendUp] = useState<boolean | null>(null);

  // Check backend availability once on mount
  useEffect(() => {
    checkHealth().then(setBackendUp);
  }, []);

  const formatOpt =
    FORMAT_OPTIONS.find((f) => f.ext === selectedFormat) ?? FORMAT_OPTIONS[0];

  const handleConvert = useCallback(async () => {
    if (state.status !== "file_selected") return;

    dispatch({ type: "START_PROCESSING", template });

    try {
      const result = await convertDocument(state.file, template);
      dispatch({ type: "COMPLETE", result });
    } catch (err) {
      dispatch({
        type: "FAIL",
        message:
          err instanceof Error ? err.message : "An unexpected error occurred.",
      });
    }
  }, [state, template]);

  const isInputVisible =
    state.status === "idle" || state.status === "file_selected";

  return (
    <div className="min-h-screen relative text-slate-200">
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: `radial-gradient(ellipse 60% 40% at 50% 0%, rgba(59, 130, 246, 0.08) 0%, transparent 60%)`,
        }}
        aria-hidden="true"
      />
      <div className="max-w-2xl mx-auto px-4 sm:px-6 py-12 sm:py-20">
        {/* Back link */}
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-sm text-slate-400 hover:text-white transition-colors mb-8"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to home
        </Link>

        {/* Backend offline banner */}
        {backendUp === null && (
          <div className="mb-6 flex items-center gap-2 px-4 py-3 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-300 text-sm">
            <span>Connecting to server... This may take up to 30 seconds on first load.</span>
          </div>
        )}
        {backendUp === false && (
          <div className="mb-6 flex items-center gap-2 px-4 py-3 rounded-xl bg-yellow-500/10 border border-yellow-500/20 text-yellow-300 text-sm">
            <AlertTriangle className="w-4 h-4 flex-shrink-0" />
            <span>Server is starting up. Please wait a moment and try again.</span>
          </div>
        )}

        {/* Heading */}
        <div className="mb-10">
          <h1 className="text-3xl sm:text-4xl font-bold text-white mb-2">
            Convert your document
          </h1>
          <p className="text-slate-400">
            Upload a file and select a template. We handle the rest.
          </p>
        </div>

        {/* ── Content per state ── */}
        <div className="space-y-8 bg-white/[0.02] backdrop-blur-sm rounded-2xl border border-white/[0.06] p-8">
          {/* Idle / File Selected */}
          {isInputVisible && (
            <>
              <FormatSelector
                selectedFormat={selectedFormat}
                onFormatChange={(fmt) => {
                  setSelectedFormat(fmt);
                  if (state.status === "file_selected") {
                    dispatch({ type: "REMOVE_FILE" });
                  }
                }}
              />

              <DropZone
                file={state.status === "file_selected" ? state.file : null}
                onFileSelect={(file) =>
                  dispatch({ type: "SELECT_FILE", file })
                }
                onFileRemove={() => dispatch({ type: "REMOVE_FILE" })}
                acceptedMime={formatOpt.mime}
                acceptedExt={formatOpt.ext}
                acceptedLabel={`${formatOpt.label} only`}
              />
              <TemplateSelector selected={template} onSelect={setTemplate} />

              {state.status === "file_selected" && (
                <button
                  onClick={handleConvert}
                  className="w-full flex items-center justify-center gap-2 px-6 py-4 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-base transition-all duration-200 shadow-lg shadow-blue-900/20 hover:shadow-blue-900/40"
                >
                  Convert to LaTeX
                  <ArrowRight className="w-4 h-4" />
                </button>
              )}
            </>
          )}

          {/* Processing */}
          {state.status === "processing" && <ProgressTracker />}

          {/* Complete */}
          {state.status === "complete" && (
            <ResultCard
              texUrl={state.result.tex_url}
              pdfUrl={state.result.pdf_url}
              processingTime={state.result.processing_time}
              onConvertAnother={() => dispatch({ type: "RESET" })}
              jobId={state.result.job_id}
              templateUsed={state.result.template_used}
              documentType={state.result.document_type}
            />
          )}

          {/* Error */}
          {state.status === "error" && (
            <ErrorCard
              message={state.message}
              onRetry={() => dispatch({ type: "RESET" })}
            />
          )}
        </div>
      </div>
    </div>
  );
}
