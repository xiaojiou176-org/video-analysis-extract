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
          <h2 style={{ margin: 0 }}>AI 摘要订阅流</h2>
          <SyncNowButton />
        </div>
        <p className="small">
          AI 生成摘要的统一时间线。优先展示 digest 全文，无 digest 时回退到 outline 摘要。
        </p>

        <form method="GET" className="inline">
          <label>
            来源平台
            <input name="source" defaultValue={source} placeholder="youtube / bilibili / rss_generic" />
          </label>
          <label>
            分类
            <select name="category" defaultValue={category}>
              <option value="">全部</option>
              <option value="tech">tech</option>
              <option value="creator">creator</option>
              <option value="macro">macro</option>
              <option value="ops">ops</option>
              <option value="misc">misc</option>
            </select>
          </label>
          <label>
            每页条数
            <input name="limit" type="number" min={1} max={100} defaultValue={String(safeLimit)} />
          </label>
          <button type="submit" className="primary">
            筛选
          </button>
        </form>
      </section>

      {error ? <p className="alert error">API error: {error}</p> : null}

      {!error && items.length === 0 ? (
        <section className="card">
          <p className="small">当前筛选条件下暂无 AI 摘要内容。</p>
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
            产物类型：<code>{item.artifact_type}</code> · 任务：{" "}
            <Link href={`/jobs?job_id=${item.job_id}`}>{item.job_id}</Link>
          </div>

          <MarkdownPreview markdown={item.summary_md} />

          <div className="inline">
            <Link href={`/artifacts?job_id=${item.job_id}`}>查看产物</Link>
            <a href={item.video_url} target="_blank" rel="noreferrer">
              打开原始链接
            </a>
          </div>
        </section>
      ))}

      {!error ? (
        <section className="card inline" style={{ justifyContent: "space-between" }}>
          <span className="small">游标分页</span>
          {nextCursor !== null ? (
            <Link
              href={`/feed?source=${encodeURIComponent(source)}&category=${encodeURIComponent(category)}&limit=${safeLimit}&cursor=${encodeURIComponent(nextCursor)}`}
            >
              下一页
            </Link>
          ) : (
            <span className="small">已到末页</span>
          )}
        </section>
      ) : null}
    </div>
  );
}
