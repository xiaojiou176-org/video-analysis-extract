type QueryValue = string | number | boolean | null | undefined;

type ResolveOptions = {
  allowFallback?: boolean;
};

export function resolveApiBaseUrl(options: ResolveOptions = {}): string {
  const { allowFallback = false } = options;
  const rawBase = process.env.NEXT_PUBLIC_API_BASE_URL;
  const base = rawBase?.trim();
  if (!base) {
    if (allowFallback) {
      return "http://127.0.0.1:8000";
    }
    throw new Error("API base URL is not configured. Set NEXT_PUBLIC_API_BASE_URL.");
  }

  let parsed: URL;
  try {
    parsed = new URL(base);
  } catch {
    throw new Error(
      `Invalid API base URL '${base}'. NEXT_PUBLIC_API_BASE_URL must be an absolute http(s) URL.`,
    );
  }

  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    throw new Error(
      `Invalid API base URL protocol '${parsed.protocol}'. Use http:// or https://.`,
    );
  }

  return base.replace(/\/$/, "");
}

const SENSITIVE_QUERY_SEGMENTS = new Set([
  "access",
  "api",
  "auth",
  "authorization",
  "credential",
  "key",
  "password",
  "secret",
  "session",
  "token",
]);

export function isSensitiveQueryKey(key: string): boolean {
  const segments = key
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter((segment) => segment.length > 0);
  return segments.some((segment) => SENSITIVE_QUERY_SEGMENTS.has(segment));
}

export function buildApiUrl(path: string, query?: Record<string, QueryValue>): string {
  const target = new URL(path, resolveApiBaseUrl({ allowFallback: true }));
  if (!query) {
    return target.toString();
  }
  for (const [key, value] of Object.entries(query)) {
    if (isSensitiveQueryKey(key)) {
      throw new Error(`ERR_SENSITIVE_QUERY_KEY:${key}`);
    }
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

const ALLOWED_EXTERNAL_PROTOCOLS = new Set(["http:", "https:"]);

export function sanitizeExternalUrl(rawUrl: string): string | null {
  const trimmed = rawUrl.trim();
  if (!trimmed) {
    return null;
  }
  let parsed: URL;
  try {
    parsed = new URL(trimmed);
  } catch {
    return null;
  }
  if (!ALLOWED_EXTERNAL_PROTOCOLS.has(parsed.protocol)) {
    return null;
  }
  return parsed.toString();
}
