export function messageFromApiBody(body: string, fallback: string): string {
  if (!body) return fallback;
  try {
    const parsed = JSON.parse(body) as {
      detail?: string | { message?: string; errors?: string[] } | { msg: string }[];
    };
    const detail = parsed.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((item) => item.msg).filter(Boolean).join("; ") || body;
    }
  } catch {
    // Plain-text response body.
  }
  return body;
}

export function parseImportError(error: unknown): {
  message: string;
  rows: string[];
} {
  const fallback = error instanceof Error ? error.message : "Import failed";
  try {
    const body = JSON.parse(fallback) as {
      detail?: { message?: string; errors?: string[] };
    };
    return {
      message: body.detail?.message ?? fallback,
      rows: body.detail?.errors ?? [],
    };
  } catch {
    return { message: fallback, rows: [] };
  }
}
