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

/** Interface for the job history endpoints. */
export interface JobRow {
  id: string;
  user_id: string;
  input_filename: string;
  template: string;
  output_format: string;
  status: string;
  created_at: string | null;
  output_pdf_path: string | null;
  output_tex_path: string | null;
  error_message: string | null;
  pdf_url: string | null;
  tex_url: string | null;
}

export interface JobsResponse {
  count: number;
  jobs: JobRow[];
}

/**
 * Fetch the raw JWT from the Next.js token proxy route.
 *
 * Must be called from the browser — the proxy reads the httpOnly
 * cookie set by NextAuth on the server side. Returns ``null`` when
 * the user is not signed in.
 */
async function getAuthToken(): Promise<string | null> {
  try {
    const res = await fetch("/api/auth/token");
    if (!res.ok) return null;
    const data = await res.json();
    return data.token ?? null;
  } catch {
    return null;
  }
}

/**
 * Build the standard headers used by every backend call.
 * Attaches the Bearer JWT token when available.
 */
async function buildHeaders(): Promise<{ Authorization?: string }> {
  const token = await getAuthToken();
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
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
    headers: await buildHeaders(),
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
    headers: await buildHeaders(),
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

export interface BatchAcceptedResponse {
  success: boolean;
  batch_id: string;
  queued: number;
  skipped: string[];
  job_ids: string[];
  message: string;
}

/**
 * Upload a zip archive of documents to the batch endpoint.
 *
 * The server extracts the archive, validates each entry, creates a
 * ``Job`` row per supported file, and processes them in the
 * background. The response is immediate (``202 Accepted``) and
 * contains the list of ``job_id``s the user can watch on the
 * History page.
 */
export async function batchConvert(
  file: File,
  options?: { template?: string; outputFormat?: string },
): Promise<BatchAcceptedResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const params = new URLSearchParams();
  if (options?.template) params.set("template", options.template);
  if (options?.outputFormat) params.set("output_format", options.outputFormat);
  const query = params.toString() ? `?${params.toString()}` : "";

  const response = await fetch(`${API_BASE_URL}/api/v2/batch${query}`, {
    method: "POST",
    body: formData,
    headers: await buildHeaders(),
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

  return (await response.json()) as BatchAcceptedResponse;
}

/**
 * Fetch the authenticated user's job history from the backend.
 *
 * The JWT token is automatically fetched and attached by ``buildHeaders()``.
 */
export async function fetchJobs(): Promise<JobsResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v2/jobs`, {
    headers: await buildHeaders(),
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch jobs: ${response.status} ${response.statusText}`);
  }
  return (await response.json()) as JobsResponse;
}
