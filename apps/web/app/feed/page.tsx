import type { Metadata } from "next";
import Link from "next/link";

import { MarkdownPreview } from "@/components/markdown-preview";
import { RelativeTime } from "@/components/relative-time";
import { SyncNowButton } from "@/components/sync-now-button";
import { apiClient } from "@/lib/api/client";
import { resolveSearchParams, type SearchParamsInput } from "@/lib/search-params";

export const metadata: Metadata = { title: "AI 摘要" };

type FeedPageProps = {
  searchParams?: SearchParamsInput;
};

const CATEGORY_LABELS: Record<string, string> = {
  tech: "科技",
  creator: "创作者",
  macro: "宏观",
  ops: "运营",
  misc: "其他",
};

function toSourceLabel(source: string): string {
  const normalized = source.trim().toLowerCase();
  if (normalized === "youtube") return "YouTube";
  if (normalized === "bilibili") return "Bilibili";
  return source || "未知";
}

function renderSourceName(source: string, sourceName: string): string {
  const fallback = toSourceLabel(source);
  const name = sourceName.trim();
  if (!name || name.toLowerCase() === source.trim().toLowerCase()) return fallback;
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
  const isFiltered = Boolean(source.trim() || category);

  let feed: Awaited<ReturnType<typeof apiClient.getDigestFeed>> | null = null;
  let error: string | null = null;
  try {
    feed = await apiClient.getDigestFeed({
      source: source.trim() || undefined,
      category:
        category === "tech" || category === "creator" || category === "macro" ||
        category === "ops" || category === "misc"
          ? category
          : undefined,
      limit: safeLimit,
      cursor: safeCursor,
    });
  } catch (err) {
    error = err instanceof Error ? err.message : "加载 AI 摘要失败";
  }

  const items = feed?.items ?? [];
  const nextCursor = feed?.next_cursor ?? null;
  const isFirstPage = !safeCursor;

  // 构建分页链接
  const buildPageUrl = (cur: string | null) => {
    const params = new URLSearchParams();
    if (source.trim()) params.set("source", source.trim());
    if (category) params.set("category", category);
    if (safeLimit !== 20) params.set("limit", String(safeLimit));
    if (cur) params.set("cursor", cur);
    const qs = params.toString();
    return `/feed${qs ? `?${qs}` : ""}`;
  };

  return (
    <div className="stack">
      {/* 筛选控件 */}
      <section className="card stack">
        <div className="flex-between">
          <h2 className="m-0">AI 摘要订阅流</h2>
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
              <option value="">全部分类</option>
              <option value="tech">科技</option>
              <option value="creator">创作者</option>
              <option value="macro">宏观</option>
              <option value="ops">运营</option>
              <option value="misc">其他</option>
            </select>
          </label>
          <label>
            每页条数
            <input name="limit" type="number" min={1} max={100} defaultValue={String(safeLimit)} />
          </label>
          <button type="submit" className="primary">筛选</button>
          {isFiltered && (
            <Link href="/feed" className="btn-link">清除筛选</Link>
          )}
        </form>
      </section>

      {error ? <p className="alert error">{error}</p> : null}

      {/* 空状态 */}
      {!error && items.length === 0 ? (
        <section className="card empty-state-card">
          <p className="empty-state-title">暂无 AI 摘要内容</p>
          <p className="small">
            {isFiltered
              ? "当前筛选条件下没有结果，试试清除筛选。"
              : "还没有处理过的视频或文章。请先去添加订阅并触发采集。"}
          </p>
          {!isFiltered && (
            <div className="inline" style={{ marginTop: "8px" }}>
              <Link href="/subscriptions" className="btn-cta">→ 前往订阅管理</Link>
            </div>
          )}
        </section>
      ) : null}

      {/* Feed 内容卡列表 */}
      {items.map((item) => (
        <article className="card card-feed stack" key={item.feed_id} data-category={item.category}>
          <div className="flex-between feed-item-header">
            <h3 className="m-0 feed-item-title">{item.title}</h3>
            <span className="feed-item-meta">
              {renderSourceName(item.source, item.source_name)}
              <span className="feed-category-chip" data-category={item.category}>
                {CATEGORY_LABELS[item.category] ?? item.category}
              </span>
              <RelativeTime dateTime={item.published_at} />
            </span>
          </div>

          <MarkdownPreview markdown={item.summary_md} />

          <div className="feed-item-footer">
            <div className="inline">
              <Link href={`/artifacts?job_id=${item.job_id}`}>查看产物</Link>
              <a href={item.video_url} target="_blank" rel="noreferrer">打开原始链接</a>
            </div>
            <span className="small feed-item-ops">
              <code>{item.artifact_type}</code>
              {" · "}
              <Link href={`/jobs?job_id=${item.job_id}`} className="job-id-link">
                {item.job_id.slice(0, 8)}…
              </Link>
            </span>
          </div>
        </article>
      ))}

      {/* 分页 */}
      {!error && items.length > 0 ? (
        <nav className="card feed-pagination" aria-label="分页">
          <div className="inline">
            {!isFirstPage && (
              <Link href="/feed" className="btn-page">
                ← 首页
              </Link>
            )}
            {isFiltered && (
              <span className="small">
                {source.trim() && `来源：${source}`}
                {source.trim() && category && " · "}
                {category && `分类：${CATEGORY_LABELS[category] ?? category}`}
              </span>
            )}
          </div>
          <div className="inline">
            <span className="small pagination-info">
              {isFirstPage ? "第 1 页" : "已翻页"}
              {nextCursor === null ? "  · 已到末页" : ""}
            </span>
            {nextCursor !== null ? (
              <Link href={buildPageUrl(nextCursor)} className="btn-page btn-page-primary">
                下一页 →
              </Link>
            ) : (
              <span className="btn-page btn-page-disabled">已到末页</span>
            )}
          </div>
        </nav>
      ) : null}
    </div>
  );
}
