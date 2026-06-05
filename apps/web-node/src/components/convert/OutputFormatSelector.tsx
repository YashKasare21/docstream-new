"use client";

import { FileText, File, Globe, Code, BookOpen } from "lucide-react";
import type { ReactNode } from "react";

export type OutputFormat = "pdf" | "docx" | "html" | "md" | "epub";

interface OutputFormatOption {
  id: OutputFormat;
  label: string;
  description: string;
  icon: ReactNode;
  /** True for the only format supported by the SSE streaming endpoint. */
  streamable: boolean;
}

export const OUTPUT_FORMAT_OPTIONS: OutputFormatOption[] = [
  {
    id: "pdf",
    label: "PDF",
    description: "Compiled via XeLaTeX (streaming supported)",
    icon: <FileText className="w-4 h-4" />,
    streamable: true,
  },
  {
    id: "docx",
    label: "DOCX",
    description: "Microsoft Word — Pandoc export",
    icon: <File className="w-4 h-4" />,
    streamable: false,
  },
  {
    id: "html",
    label: "HTML",
    description: "Web page — Pandoc export",
    icon: <Globe className="w-4 h-4" />,
    streamable: false,
  },
  {
    id: "md",
    label: "Markdown",
    description: "Plain Markdown — Pandoc export",
    icon: <Code className="w-4 h-4" />,
    streamable: false,
  },
  {
    id: "epub",
    label: "EPUB",
    description: "E-reader — Pandoc export",
    icon: <BookOpen className="w-4 h-4" />,
    streamable: false,
  },
];

interface OutputFormatSelectorProps {
  selected: OutputFormat;
  onChange: (format: OutputFormat) => void;
}

export default function OutputFormatSelector({ selected, onChange }: OutputFormatSelectorProps) {
  return (
    <div>
      <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">
        Output format
      </p>
      <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Output format">
        {OUTPUT_FORMAT_OPTIONS.map(({ id, label, icon }) => {
          const isSelected = selected === id;
          return (
            <button
              key={id}
              type="button"
              role="radio"
              aria-checked={isSelected}
              onClick={() => onChange(id)}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-all duration-200 ${
                isSelected
                  ? "bg-blue-600 text-white shadow-[0_0_16px_rgba(59,130,246,0.4)]"
                  : "glass-card text-slate-400 hover:text-white hover:border-white/20"
              }`}
            >
              {icon}
              {label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
