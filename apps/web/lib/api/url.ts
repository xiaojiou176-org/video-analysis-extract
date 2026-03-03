type QueryValue = string | number | boolean | null | undefined;

type ResolveOptions = {
	allowFallback?: boolean;
	strict?: boolean;
};

const DEFAULT_LOCAL_API_BASE_URL = "http://127.0.0.1:8000";

export function resolveApiBaseUrl(options: ResolveOptions = {}): string {
	const strict = options.strict === true;
	const allowFallback = strict ? false : options.allowFallback ?? true;
	const rawBase = process.env.NEXT_PUBLIC_API_BASE_URL;
	const base = rawBase?.trim();
	if (!base) {
		if (allowFallback) {
			return DEFAULT_LOCAL_API_BASE_URL;
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
		throw new Error(`Invalid API base URL protocol '${parsed.protocol}'. Use http:// or https://.`);
	}

	if (parsed.username || parsed.password) {
		throw new Error("Invalid API base URL credentials. Do not include username/password.");
	}

	if (parsed.search || parsed.hash) {
		throw new Error("Invalid API base URL suffix. Query/hash is not allowed.");
	}

	if (parsed.pathname !== "/" && parsed.pathname !== "") {
		throw new Error("Invalid API base URL path. Use bare origin like https://api.example.com.");
	}

	return parsed.origin;
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
	return buildApiUrlWithOptions(path, query);
}

export function buildApiUrlWithOptions(
	path: string,
	query?: Record<string, QueryValue>,
	resolveOptions: ResolveOptions = {},
): string {
	const normalizedPath = path.trim();
	if (!normalizedPath.startsWith("/") || normalizedPath.startsWith("//")) {
		throw new Error("ERR_INVALID_API_PATH");
	}

	const target = new URL(normalizedPath, resolveApiBaseUrl(resolveOptions));
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
	return buildApiUrlWithOptions("/api/v1/artifacts/assets", { job_id: jobId, path });
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
	if (parsed.username || parsed.password) {
		return null;
	}
	return parsed.toString();
}

export function getWebActionSessionToken(): string {
	return (process.env.WEB_ACTION_SESSION_TOKEN ?? "").trim();
}
