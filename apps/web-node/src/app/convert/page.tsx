"use client";

import { useReducer, useState, useCallback, useEffect, useRef } from "react";
import { ArrowLeft, ArrowRight, AlertTriangle, Info, Play, RotateCcw } from "lucide-react";
import Link from "next/link";
import DropZone from "@/components/convert/DropZone";
import TemplateSelector from "@/components/convert/TemplateSelector";
import ProgressTracker from "@/components/convert/ProgressTracker";
import ErrorCard from "@/components/convert/ErrorCard";
import ResultCard from "@/components/convert/ResultCard";
import FormatSelector, { FORMAT_OPTIONS } from "@/components/convert/FormatSelector";
import OutputFormatSelector, {
  OUTPUT_FORMAT_OPTIONS,
  type OutputFormat,
} from "@/components/convert/OutputFormatSelector";
import LatexEditor from "@/components/convert/LatexEditor";
import PdfPreview from "@/components/convert/PdfPreview";
import {
  batchConvert,
  checkHealth,
  compileLatexText,
  convertDocument,
  streamDocument,
  type ConvertResult,
  type StreamEvent,
} from "@/lib/api";

// ── State machine ──────────────────────────────────────────────────────────────
type State =
  | { status: "idle" }
  | { status: "file_selected"; file: File }
  | { status: "processing"; file: File; template: string; outputFormat: OutputFormat }
  | {
      status: "streaming";
      file: File;
      template: string;
      outputFormat: OutputFormat;
      accumulated: string;
      progress: number;
    }
  | { status: "complete"; result: ConvertResult; texCode: string }
  | { status: "error"; message: string };

type Action =
  | { type: "SELECT_FILE"; file: File }
  | { type: "REMOVE_FILE" }
  | { type: "START_PROCESSING"; template: string; outputFormat: OutputFormat }
  | { type: "STREAM_CHUNK"; chunk: string; progress: number }
  | { type: "COMPLETE"; result: ConvertResult; texCode: string }
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
      return {
        status: "processing",
        file: state.file,
        template: action.template,
        outputFormat: action.outputFormat,
      };
    case "STREAM_CHUNK": {
      if (state.status !== "processing" && state.status !== "streaming") return state;
      const prevAccumulated = state.status === "streaming" ? state.accumulated : "";
      return {
        status: "streaming",
        file: state.file,
        template: state.template,
        outputFormat: state.outputFormat,
        accumulated: prevAccumulated + action.chunk,
        progress: action.progress,
      };
    }
    case "COMPLETE":
      return { status: "complete", result: action.result, texCode: action.texCode };
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
  const [outputFormat, setOutputFormat] = useState<OutputFormat>("pdf");
  const [backendUp, setBackendUp] = useState<boolean | null>(null);

  // ── Editor mode state ──
  const [texCode, setTexCode] = useState<string>("");
  const [editorPdfUrl, setEditorPdfUrl] = useState<string>("");
  const [isRecompiling, setIsRecompiling] = useState(false);
  const [recompileError, setRecompileError] = useState<string | null>(null);
  const editorVersionRef = useRef(0);

  // Check backend availability once on mount
  useEffect(() => {
    checkHealth().then(setBackendUp);
  }, []);

  const formatOpt = FORMAT_OPTIONS.find((f) => f.ext === selectedFormat) ?? FORMAT_OPTIONS[0];

  // The SSE streaming endpoint is PDF-only — non-PDF outputs must use the
  // standard POST /api/v2/convert endpoint.
  const canStream = outputFormat === "pdf";
  const outputFormatMeta = OUTPUT_FORMAT_OPTIONS.find((o) => o.id === outputFormat);
  const isEditorMode = state.status === "complete" && canStream;

  // Promote streaming text into editor state once conversion completes.
  useEffect(() => {
    if (state.status === "complete" && canStream) {
      setTexCode(state.texCode);
      setEditorPdfUrl(state.result.pdf_url);
      setRecompileError(null);
    }
  }, [state, canStream]);

  const handleConvert = useCallback(async () => {
    if (state.status !== "file_selected") return;

    // Batch path: zip archive → /api/v2/batch. The server returns
    // 202 immediately and processes files in the background, so we
    // surface a toast and let the user track progress on /history.
    if (selectedFormat === ".zip") {
      try {
        const result = await batchConvert(state.file, {
          template,
          outputFormat,
        });
        if (typeof window !== "undefined") {
          window.alert(
            `Batch uploaded! ${result.queued} document(s) queued for conversion. Check your History page for progress.`,
          );
        }
        // Reset to idle so the user can upload another archive.
        dispatch({ type: "RESET" });
      } catch (err) {
        dispatch({
          type: "FAIL",
          message: err instanceof Error ? err.message : "An unexpected error occurred.",
        });
      }
      return;
    }

    dispatch({ type: "START_PROCESSING", template, outputFormat });

    try {
      if (canStream) {
        let accumulated = "";
        const result = await streamDocument(
          state.file,
          template,
          (event: StreamEvent) => {
            accumulated += event.chunk;
            dispatch({ type: "STREAM_CHUNK", chunk: event.chunk, progress: event.progress });
          },
        );
        dispatch({ type: "COMPLETE", result, texCode: accumulated });
      } else {
        const result = await convertDocument(
          state.file,
          template,
          (stage) => {
            if (stage === 1) {
              dispatch({ type: "STREAM_CHUNK", chunk: "", progress: 0.2 });
            } else if (stage === 3) {
              dispatch({ type: "STREAM_CHUNK", chunk: "", progress: 1 });
            }
          },
          outputFormat,
        );
        dispatch({ type: "COMPLETE", result, texCode: "" });
      }
    } catch (err) {
      dispatch({
        type: "FAIL",
        message: err instanceof Error ? err.message : "An unexpected error occurred.",
      });
    }
  }, [state, template, outputFormat, canStream, selectedFormat]);

  const handleRecompile = useCallback(async () => {
    if (state.status !== "complete" || !canStream) return;
    setIsRecompiling(true);
    setRecompileError(null);
    const version = ++editorVersionRef.current;
    try {
      const jobName = state.result.job_id || "document";
      const { url } = await compileLatexText(texCode, jobName);
      // Guard against stale requests: only apply the latest result.
      if (version !== editorVersionRef.current) {
        URL.revokeObjectURL(url);
        return;
      }
      setEditorPdfUrl((prev) => {
        if (prev.startsWith("blob:")) URL.revokeObjectURL(prev);
        return url;
      });
    } catch (err) {
      if (version === editorVersionRef.current) {
        setRecompileError(err instanceof Error ? err.message : "Recompile failed.");
      }
    } finally {
      if (version === editorVersionRef.current) {
        setIsRecompiling(false);
      }
    }
  }, [state, texCode, canStream]);

  const isInputVisible = state.status === "idle" || state.status === "file_selected";

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
          <h1 className="text-3xl sm:text-4xl font-bold text-white mb-2">Convert your document</h1>
          <p className="text-slate-400">Upload a file and select a template. We handle the rest.</p>
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

              <OutputFormatSelector
                selected={outputFormat}
                onChange={(fmt) => {
                  setOutputFormat(fmt);
                  if (state.status === "file_selected") {
                    dispatch({ type: "REMOVE_FILE" });
                  }
                }}
              />

              {!canStream && outputFormatMeta && (
                <div className="flex items-start gap-2 px-4 py-3 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-300 text-xs">
                  <Info className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                  <span>
                    {outputFormatMeta.label} export uses Pandoc and is processed via a single
                    request (streaming is only available for PDF).
                  </span>
                </div>
              )}

              <DropZone
                file={state.status === "file_selected" ? state.file : null}
                onFileSelect={(file) => dispatch({ type: "SELECT_FILE", file })}
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
                  {outputFormat === "pdf"
                    ? "Convert to LaTeX"
                    : `Convert to ${outputFormatMeta?.label ?? outputFormat}`}
                  <ArrowRight className="w-4 h-4" />
                </button>
              )}
            </>
          )}

          {/* Processing / Streaming */}
          {(state.status === "processing" || state.status === "streaming") && (
            <div className="space-y-4">
              <ProgressTracker />
              {state.status === "streaming" && (
                <>
                  {/* Progress bar */}
                  <div className="w-full bg-muted rounded-full h-2 overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-300 ease-out rounded-full"
                      style={{ width: `${Math.round(state.progress * 100)}%` }}
                    />
                  </div>
                  <p className="text-xs text-muted-foreground text-right">
                    {Math.round(state.progress * 100)}%
                  </p>
                  {/* Terminal-style LaTeX preview */}
                  <div className="rounded-xl overflow-hidden border border-border shadow-lg">
                    {/* Terminal title bar */}
                    <div className="flex items-center gap-2 px-4 py-2.5 bg-[#1a1b26] border-b border-[#2a2b3e]">
                      <div className="flex items-center gap-1.5">
                        <span className="w-3 h-3 rounded-full bg-red-500" />
                        <span className="w-3 h-3 rounded-full bg-yellow-500" />
                        <span className="w-3 h-3 rounded-full bg-green-500" />
                      </div>
                      <span className="text-xs text-[#565f89] font-mono ml-2">stream — LaTeX output</span>
                    </div>
                    {/* Terminal content */}
                    <div className="max-h-72 overflow-y-auto bg-[#0d1117] p-4">
                      <pre className="text-sm text-[#7ec8e3] font-mono whitespace-pre-wrap break-all leading-relaxed">
                        {state.accumulated || (
                          <span className="text-[#565f89] italic">Waiting for output...</span>
                        )}
                        <span className="inline-block w-2 h-4.5 bg-[#7ec8e3] align-text-bottom ml-0.5 animate-pulse" />
                      </pre>
                    </div>
                  </div>
                </>
              )}
            </div>
          )}

          {/* Complete — Editor Mode (PDF only) */}
          {isEditorMode && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-white">Live editor</h2>
                  <p className="text-xs text-slate-400">
                    Edit your LaTeX on the left, recompile to refresh the PDF preview.
                  </p>
                </div>
                <button
                  onClick={handleRecompile}
                  disabled={isRecompiling}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-60 disabled:cursor-not-allowed text-white font-medium text-sm transition-all duration-200 shadow-lg shadow-blue-900/20"
                >
                  <Play className={`w-3.5 h-3.5 ${isRecompiling ? "animate-pulse" : ""}`} />
                  {isRecompiling ? "Recompiling..." : "Recompile"}
                </button>
              </div>

              {recompileError && (
                <div className="flex items-start gap-2 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300 text-sm">
                  <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="font-medium">LaTeX compilation failed</p>
                    <p className="text-xs text-red-300/80 mt-1 whitespace-pre-wrap">
                      {recompileError}
                    </p>
                  </div>
                </div>
              )}

              <div
                className="grid gap-3"
                style={{ gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr)" }}
              >
                <div className="h-[640px] min-h-[400px]">
                  <LatexEditor texCode={texCode} onCodeChange={setTexCode} />
                </div>
                <div className="h-[640px] min-h-[400px]">
                  <PdfPreview
                    pdfUrl={editorPdfUrl}
                    loadingHint={isRecompiling ? "Recompiling..." : undefined}
                  />
                </div>
              </div>

              <button
                onClick={() => {
                  setTexCode("");
                  setEditorPdfUrl("");
                  setRecompileError(null);
                  dispatch({ type: "RESET" });
                }}
                className="inline-flex items-center gap-1.5 text-sm text-slate-400 hover:text-white transition-colors"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                Convert another document
              </button>
            </div>
          )}

          {/* Complete — Non-PDF (single file download) */}
          {state.status === "complete" && !canStream && (
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
            <ErrorCard message={state.message} onRetry={() => dispatch({ type: "RESET" })} />
          )}
        </div>
      </div>
    </div>
  );
}
