"use client";

import { useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { Loader2, FileText, AlertTriangle } from "lucide-react";
import { pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

// react-pdf subcomponents must be client-only (uses canvas / worker).
const Document = dynamic(
  () => import("react-pdf").then((m) => m.Document),
  {
    ssr: false,
    loading: () => (
      <div className="flex items-center justify-center h-full w-full text-slate-400 text-sm gap-2">
        <Loader2 className="w-4 h-4 animate-spin" />
        Loading PDF viewer...
      </div>
    ),
  },
);

const Page = dynamic(() => import("react-pdf").then((m) => m.Page), {
  ssr: false,
});

let workerConfigured = false;
function configureWorker() {
  if (workerConfigured || typeof window === "undefined") return;
  // Prefer the locally-hosted worker (copied to /public at build time);
  // fall back to the unpkg CDN if the local copy is missing.
  const local = "/pdf.worker.min.mjs";
  const cdn = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;
  pdfjs.GlobalWorkerOptions.workerSrc = local;
  fetch(local, { method: "HEAD" })
    .then((res) => {
      if (!res.ok) pdfjs.GlobalWorkerOptions.workerSrc = cdn;
    })
    .catch(() => {
      pdfjs.GlobalWorkerOptions.workerSrc = cdn;
    });
  workerConfigured = true;
}

interface PdfPreviewProps {
  pdfUrl: string;
  /** Optional loading hint shown while the URL is being refreshed. */
  loadingHint?: string;
}

export default function PdfPreview({ pdfUrl, loadingHint }: PdfPreviewProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [containerWidth, setContainerWidth] = useState<number>(800);
  const [numPages, setNumPages] = useState<number | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    configureWorker();
  }, []);

  // Revoke old blob URLs when the URL changes to avoid memory leaks.
  useEffect(() => {
    return () => {
      if (pdfUrl.startsWith("blob:")) {
        URL.revokeObjectURL(pdfUrl);
      }
    };
  }, [pdfUrl]);

  // Reset error when URL changes (e.g. after a recompile).
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- Intentional reset when PDF URL changes
    setLoadError(null);
  }, [pdfUrl]);

  // Track container width with ResizeObserver so the PDF scales with the layout.
  useEffect(() => {
    const node = containerRef.current;
    if (!node) return;
    const update = () => {
      const w = node.clientWidth - 32;
      if (w > 0) setContainerWidth(w);
    };
    update();
    const observer = new ResizeObserver(update);
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return (
    <div className="h-full w-full flex flex-col rounded-lg border border-white/[0.08] bg-[#0d1117] overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 border-b border-white/[0.06] bg-[#0a0c12] text-xs text-slate-400">
        <div className="flex items-center gap-2">
          <FileText className="w-3.5 h-3.5" />
          <span className="font-medium">PDF preview</span>
          {numPages !== null && (
            <span className="text-slate-500">
              · {numPages} page{numPages === 1 ? "" : "s"}
            </span>
          )}
        </div>
        {loadingHint && (
          <div className="flex items-center gap-1.5 text-blue-300">
            <Loader2 className="w-3 h-3 animate-spin" />
            <span>{loadingHint}</span>
          </div>
        )}
      </div>
      <div ref={containerRef} className="flex-1 overflow-auto p-4">
        {loadError ? (
          <div className="flex items-start gap-2 text-sm text-red-300 bg-red-500/10 border border-red-500/20 rounded-lg p-3">
            <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium">Failed to render PDF</p>
              <p className="text-xs text-red-300/80 mt-1">{loadError}</p>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-4">
            <Document
              file={pdfUrl}
              onLoadSuccess={({ numPages: n }) => setNumPages(n)}
              onLoadError={(err) => setLoadError(err.message)}
              loading={
                <div className="flex items-center justify-center py-8 text-slate-400 text-sm gap-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Compiling...
                </div>
              }
              className="flex flex-col items-center gap-4"
            >
              {numPages === null ? (
                <Page
                  pageNumber={1}
                  width={containerWidth}
                  renderTextLayer
                  renderAnnotationLayer
                  className="shadow-[0_4px_24px_rgba(0,0,0,0.4)]"
                />
              ) : (
                Array.from(new Array(numPages), (_, index) => (
                  <Page
                    key={`page_${index + 1}`}
                    pageNumber={index + 1}
                    width={containerWidth}
                    renderTextLayer
                    renderAnnotationLayer
                    className="shadow-[0_4px_24px_rgba(0,0,0,0.4)]"
                  />
                ))
              )}
            </Document>
          </div>
        )}
      </div>
    </div>
  );
}
