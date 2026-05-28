"use client";

import { FileText, File, Monitor, Image, Code, AlignLeft } from "lucide-react";
import type { ReactNode } from "react";

interface FormatOption {
  ext: string;
  mime: string;
  icon: ReactNode;
  label: string;
}

export const FORMAT_OPTIONS: FormatOption[] = [
  {
    ext: ".pdf",
    mime: "application/pdf",
    icon: <FileText className="w-4 h-4" />,
    label: "PDF",
  },
  {
    ext: ".docx",
    mime: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    icon: <File className="w-4 h-4" />,
    label: "Word",
  },
  {
    ext: ".pptx",
    mime: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    icon: <Monitor className="w-4 h-4" />,
    label: "PPT",
  },
  {
    ext: ".png",
    mime: "image/png",
    icon: <Image className="w-4 h-4" />,
    label: "Image",
  },
  {
    ext: ".md",
    mime: "text/markdown",
    icon: <Code className="w-4 h-4" />,
    label: "Markdown",
  },
  {
    ext: ".txt",
    mime: "text/plain",
    icon: <AlignLeft className="w-4 h-4" />,
    label: "Text",
  },
];

interface FormatSelectorProps {
  selectedFormat: string;
  onFormatChange: (format: string) => void;
}

export default function FormatSelector({
  selectedFormat,
  onFormatChange,
}: FormatSelectorProps) {
  return (
    <div>
      <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">
        Input format
      </p>
      <div className="flex flex-wrap gap-2">
        {FORMAT_OPTIONS.map(({ ext, icon, label }) => {
          const isSelected = selectedFormat === ext;
          return (
            <button
              key={ext}
              onClick={() => onFormatChange(ext)}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-all duration-200 ${
                isSelected
                  ? "bg-blue-600 text-white shadow-[0_0_16px_rgba(59,130,246,0.4)]"
                  : "glass-card text-slate-400 hover:text-white hover:border-white/20"
              }`}
              aria-pressed={isSelected}
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
