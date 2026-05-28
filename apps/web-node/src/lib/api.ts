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
): Promise<ConvertResult> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("template", template);

  onProgress?.(1);

  const response = await fetch(`${API_BASE_URL}/api/v2/convert`, {
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

export async function getFormats(): Promise<string[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v2/formats`);
    const data = await res.json();
    return (data.formats as { extension: string }[]).map((f) => f.extension);
  } catch {
    return [".pdf"];
  }
}
