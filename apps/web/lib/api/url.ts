type QueryValue = string | number | boolean | null | undefined;

type ResolveOptions = {
  allowFallback?: boolean;
};

export function resolveApiBaseUrl(options: ResolveOptions = {}): string {
  const { allowFallback = false } = options;
  const rawBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? process.env.VD_API_BASE_URL;
  const base = rawBase?.trim();
  if (!base) {
    if (allowFallback) {
      return "http://127.0.0.1:8000";
    }
    throw new Error(
      "API base URL is not configured. Set NEXT_PUBLIC_API_BASE_URL (preferred) or VD_API_BASE_URL.",
    );
  }

  let parsed: URL;
  try {
    parsed = new URL(base);
  } catch {
    throw new Error(
      `Invalid API base URL '${base}'. NEXT_PUBLIC_API_BASE_URL or VD_API_BASE_URL must be an absolute http(s) URL.`,
    );
  }

  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    throw new Error(
      `Invalid API base URL protocol '${parsed.protocol}'. Use http:// or https://.`,
    );
  }

  return base.replace(/\/$/, "");
}

export function buildApiUrl(path: string, query?: Record<string, QueryValue>): string {
  const target = new URL(path, resolveApiBaseUrl({ allowFallback: true }));
  if (!query) {
    return target.toString();
  }
  for (const [key, value] of Object.entries(query)) {
    if (value === null || value === undefined || value === "") {
      continue;
    }
    target.searchParams.set(key, String(value));
  }
  return target.toString();
}

export function buildArtifactAssetUrl(jobId: string, path: string): string {
  return buildApiUrl("/api/v1/artifacts/assets", { job_id: jobId, path });
}
