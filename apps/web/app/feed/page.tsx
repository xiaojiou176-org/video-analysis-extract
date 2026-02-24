import Link from "next/link";

import { MarkdownPreview } from "@/components/markdown-preview";
import { SyncNowButton } from "@/components/sync-now-button";
import { apiClient } from "@/lib/api/client";
import { formatDateTime } from "@/lib/format";
import { resolveSearchParams, type SearchParamsInput } from "@/lib/search-params";

type FeedPageProps = {
  searchParams?: SearchParamsInput;
};

function toSourceLabel(source: string): string {
  const normalized = source.trim().toLowerCase();
  if (normalized === "youtube") {
    return "YouTube";
  }
  if (normalized === "bilibili") {
    return "Bilibili";
  }
  return source || "Unknown";
}

function renderSourceName(source: string, sourceName: string): string {
  const fallback = toSourceLabel(source);
  const name = sourceName.trim();
  if (!name || name.toLowerCase() === source.trim().toLowerCase()) {
    return fallback;
  }
  return `${fallback} · ${name}`;
}

export default async function FeedPage({ searchParams }: FeedPageProps) {
  const { source, category, limit, cursor } = await resolveSearchParams(searchParams, [
    "source",
    "category",
    "limit",
    "cursor",
  ] as const);

  const parsedLimit = Number.parseInt(limit, 10);
  const safeLimit = Number.isFinite(parsedLimit) && parsedLimit > 0 ? Math.min(parsedLimit, 100) : 20;
  const safeCursor = cursor.trim() || undefined;

  let feed: Awaited<ReturnType<typeof apiClient.getDigestFeed>> | null = null;
  let error: string | null = null;
  try {
    feed = await apiClient.getDigestFeed({
      source: source.trim() || undefined,
      category:
        category === "tech" ||
        category === "creator" ||
        category === "macro" ||
        category === "ops" ||
        category === "misc"
          ? category
          : undefined,
      limit: safeLimit,
      cursor: safeCursor,
    });
  } catch (err) {
    error = err instanceof Error ? err.message : "Failed to load AI feed";
  }

  const items = feed?.items ?? [];
  const nextCursor = feed?.next_cursor ?? null;

  return (
    <div className="stack">
      <section className="card stack">
        <div className="inline" style={{ justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{ margin: 0 }}>AI Digest Feed</h2>
          <SyncNowButton />
        </div>
        <p className="small">
          Unified timeline for AI generated digest text. This page prioritizes digest markdown and falls back to
          outline summary when digest is unavailable.
        </p>

        <form method="GET" className="inline">
          <label>
            Source
            <input name="source" defaultValue={source} placeholder="youtube / bilibili / rss_generic" />
          </label>
          <label>
            Category
            <select name="category" defaultValue={category}>
              <option value="">All</option>
              <option value="tech">tech</option>
              <option value="creator">creator</option>
              <option value="macro">macro</option>
              <option value="ops">ops</option>
              <option value="misc">misc</option>
            </select>
          </label>
          <label>
            Page size
            <input name="limit" type="number" min={1} max={100} defaultValue={String(safeLimit)} />
          </label>
          <button type="submit" className="primary">
            Apply
          </button>
        </form>
      </section>

      {error ? <p className="alert error">API error: {error}</p> : null}

      {!error && items.length === 0 ? (
        <section className="card">
          <p className="small">No AI feed items found for the selected filters.</p>
        </section>
      ) : null}

      {items.map((item) => (
        <section className="card stack" key={item.feed_id}>
          <div className="inline" style={{ justifyContent: "space-between", alignItems: "baseline" }}>
            <h3 style={{ margin: 0 }}>{item.title}</h3>
            <span className="small">
              {renderSourceName(item.source, item.source_name)} · {item.category} · {formatDateTime(item.published_at)}
            </span>
          </div>

          <div className="small">
            Artifact type: <code>{item.artifact_type}</code> · Job:{" "}
            <Link href={`/jobs?job_id=${item.job_id}`}>{item.job_id}</Link>
          </div>

          <MarkdownPreview markdown={item.summary_md} />

          <div className="inline">
            <Link href={`/artifacts?job_id=${item.job_id}`}>Open artifacts</Link>
            <a href={item.video_url} target="_blank" rel="noreferrer">
              Open source URL
            </a>
          </div>
        </section>
      ))}

      {!error ? (
        <section className="card inline" style={{ justifyContent: "space-between" }}>
          <span className="small">Cursor pagination</span>
          {nextCursor !== null ? (
            <Link
              href={`/feed?source=${encodeURIComponent(source)}&category=${encodeURIComponent(category)}&limit=${safeLimit}&cursor=${encodeURIComponent(nextCursor)}`}
            >
              Next page
            </Link>
          ) : (
            <span className="small">Next page</span>
          )}
        </section>
      ) : null}
    </div>
  );
}
