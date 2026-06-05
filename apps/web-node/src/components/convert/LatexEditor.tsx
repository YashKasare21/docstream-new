"use client";

import dynamic from "next/dynamic";
import type { OnChange } from "@monaco-editor/react";
import { Loader2 } from "lucide-react";

const MonacoEditor = dynamic(
  async () => {
    const mod = await import("@monaco-editor/react");
    return mod.default;
  },
  {
    ssr: false,
    loading: () => (
      <div className="flex items-center justify-center h-full w-full bg-[#0d1117] text-slate-400 text-sm gap-2">
        <Loader2 className="w-4 h-4 animate-spin" />
        Loading editor...
      </div>
    ),
  },
);

interface LatexEditorProps {
  texCode: string;
  onCodeChange: (newCode: string) => void;
  height?: string | number;
}

export default function LatexEditor({
  texCode,
  onCodeChange,
  height = "100%",
}: LatexEditorProps) {
  const handleChange: OnChange = (value) => {
    onCodeChange(value ?? "");
  };

  return (
    <div className="h-full w-full overflow-hidden rounded-lg border border-white/[0.08] bg-[#0d1117]">
      <MonacoEditor
        height={height}
        defaultLanguage="latex"
        language="latex"
        theme="vs-dark"
        value={texCode}
        onChange={handleChange}
        options={{
          minimap: { enabled: false },
          fontSize: 13,
          fontFamily: "'JetBrains Mono', 'Fira Code', Menlo, monospace",
          wordWrap: "on",
          scrollBeyondLastLine: false,
          smoothScrolling: true,
          tabSize: 2,
          renderLineHighlight: "all",
          padding: { top: 12, bottom: 12 },
          automaticLayout: true,
        }}
      />
    </div>
  );
}
