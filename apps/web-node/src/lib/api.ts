const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ConvertResult {
  success: boolean;
  job_id: string;
  tex_url: string;
  pdf_url: string;
  processing_time: number;
  document_type?: string;
  template_used?: string;
  quality_score?: number;
  error?: string;
}

export async function convertDocument(
  file: File,
  template: string,
  onProgress?: (stage: number) => void,
  output_format?: string,
): Promise<ConvertResult> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("template", template);

  onProgress?.(1);

  const query = output_format ? `?output_format=${encodeURIComponent(output_format)}` : "";
  const response = await fetch(`${API_BASE_URL}/api/v2/convert${query}`, {
    method: "POST",
    body: formData,
    // No Content-Type header — browser sets it with multipart boundary
  });

  if (!response.ok) {
    throw new Error(`Server error: ${response.status} ${response.statusText}`);
  }

  const data: ConvertResult = await response.json();

  if (!data.success) {
    throw new Error(data.error ?? "Conversion failed");
  }

  onProgress?.(3);

  // Prefix relative URLs with the API base so downloads work cross-origin
  return {
    ...data,
    tex_url: data.tex_url.startsWith("http") ? data.tex_url : `${API_BASE_URL}${data.tex_url}`,
    pdf_url: data.pdf_url.startsWith("http") ? data.pdf_url : `${API_BASE_URL}${data.pdf_url}`,
  };
}

/** Backward-compatible alias. */
export const convertPDF = convertDocument;

export async function checkHealth(): Promise<boolean> {
  const maxRetries = 3;
  const retryDelay = 10000;

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/health`, {
        signal: AbortSignal.timeout(15000),
        cache: "no-store",
      });
      if (response.ok) return true;
    } catch {
      if (attempt < maxRetries) {
        await new Promise((resolve) => setTimeout(resolve, retryDelay));
      }
    }
  }
  return false;
}

export interface StreamEvent {
  chunk: string;
  progress: number;
  step: string;
  tex_url?: string;
  pdf_url?: string;
  processing_time?: number;
  template_used?: string;
  error?: string;
}

export async function streamDocument(
  file: File,
  template: string,
  onChunk: (event: StreamEvent) => void,
  signal?: AbortSignal,
): Promise<ConvertResult> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("template", template);

  const response = await fetch(`${API_BASE_URL}/api/v2/stream`, {
    method: "POST",
    body: formData,
    signal,
  });

  if (!response.ok) {
    throw new Error(`Server error: ${response.status} ${response.statusText}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("Response body is not readable");
  }

  const decoder = new TextDecoder();
  let buffer = "";
  let result: ConvertResult | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed.startsWith("data: ")) continue;

      const payload = trimmed.slice(6);
      if (payload === "[DONE]") continue;

      try {
        const event: StreamEvent = JSON.parse(payload);
        onChunk(event);

        if (event.step === "done") {
          result = {
            success: true,
            job_id: "",
            tex_url: event.tex_url ?? "",
            pdf_url: event.pdf_url ?? "",
            processing_time: event.processing_time ?? 0,
            template_used: event.template_used,
            document_type: undefined,
            quality_score: undefined,
          };
        } else if (event.step === "error") {
          throw new Error(event.chunk);
        }
      } catch {
        // skip malformed JSON lines
      }
    }
  }

  if (!result) {
    throw new Error("Stream ended without completion signal");
  }

  return result;
}

export async function getFormats(): Promise<string[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v2/formats`);
    const data = await res.json();
    return (data.formats as { extension: string }[]).map((f) => f.extension);
  } catch {
    return [".pdf"];
  }
}

/**
 * Direct LaTeX compilation — uploads a `.tex` file to the standalone
 * `/api/v2/compile` endpoint and returns a blob URL the browser can
 * download. The server runs XeLaTeX without any AI generation step, so
 * this is the path for iteratively recompiling hand-authored sources.
 */
export async function compileLatex(file: File): Promise<{ blob: Blob; url: string; filename: string }> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/v2/compile`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    let detail = `Server error: ${response.status} ${response.statusText}`;
    try {
      const errBody = await response.json();
      if (errBody?.detail) {
        detail = typeof errBody.detail === "string" ? errBody.detail : JSON.stringify(errBody.detail);
      }
    } catch {
      // body wasn't JSON; keep the generic message
    }
    throw new Error(detail);
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);

  const disposition = response.headers.get("Content-Disposition") ?? "";
  const match = disposition.match(/filename="?([^";]+)"?/i);
  const filename = match?.[1] ?? `${file.name.replace(/\.(tex|latex)$/i, "")}.pdf`;

  return { blob, url, filename };
}

/**
 * Wrap a raw LaTeX string in a `File` and send it to the compile endpoint.
 * Used by the in-browser editor's "Recompile" button.
 */
export async function compileLatexText(
  texCode: string,
  jobName = "document",
): Promise<{ blob: Blob; url: string; filename: string }> {
  const safeName = jobName.replace(/[^A-Za-z0-9._-]/g, "_") || "document";
  const file = new File([texCode], `${safeName}.tex`, { type: "application/x-tex" });
  return compileLatex(file);
}
