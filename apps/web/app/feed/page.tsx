import type { Metadata } from "next";
import Link from "next/link";

import { getFlashMessage, toErrorCode } from "@/app/flash-message";
import { MarkdownPreview } from "@/components/markdown-preview";
import { RelativeTime } from "@/components/relative-time";
import { SyncNowButton } from "@/components/sync-now-button";
import { apiClient } from "@/lib/api/client";
import { sanitizeExternalUrl } from "@/lib/api/url";
import { resolveSearchParams, type SearchParamsInput } from "@/lib/search-params";

export const metadata: Metadata = { title: "AI 摘要" };

type FeedPageProps = {
	searchParams?: SearchParamsInput;
};

const CATEGORY_LABELS: Record<string, string> = {
	tech: "科技",
	creator: "创作者",
	macro: "宏观",
	ops: "运维",
	misc: "其他",
};

const SOURCE_OPTIONS = [
	{ value: "", label: "全部来源" },
	{ value: "youtube", label: "YouTube" },
	{ value: "bilibili", label: "Bilibili" },
	{ value: "rss", label: "RSS" },
] as const;

function toSourceSelectValue(source: string): (typeof SOURCE_OPTIONS)[number]["value"] {
	const normalized = source.trim().toLowerCase();
	if (normalized === "youtube" || normalized === "bilibili" || normalized === "rss") {
		return normalized;
	}
	if (normalized === "rss_generic") {
		return "rss";
	}
	return "";
}

function toSourceLabel(source: string): string {
	const normalized = source.trim().toLowerCase();
	if (normalized === "youtube") {
		return "YouTube";
	}
	if (normalized === "bilibili") {
		return "Bilibili";
	}
	if (normalized === "rss" || normalized === "rss_generic") {
		return "RSS";
	}
	return source || "未知";
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
	const { source, category, limit, cursor, prev_cursor, page } = await resolveSearchParams(searchParams, [
		"source",
		"category",
		"limit",
		"cursor",
		"prev_cursor",
		"page",
	] as const);

	const parsedLimit = Number.parseInt(limit, 10);
	const safeLimit =
		Number.isFinite(parsedLimit) && parsedLimit > 0 ? Math.min(parsedLimit, 100) : 20;
	const safeCursor = cursor.trim() || undefined;
	const safePrevCursor = prev_cursor.trim() || undefined;
	const parsedPage = Number.parseInt(page, 10);
	const inferredPage = safeCursor ? 2 : 1;
	const safePage =
		Number.isFinite(parsedPage) && parsedPage > 0 ? parsedPage : inferredPage;
	const normalizedSource = source.trim().toLowerCase();
	const safeSource = normalizedSource || undefined;
	const sourceSelectValue = toSourceSelectValue(source);
	const isFiltered = Boolean(safeSource || category);
	const hasVisibleFilterLabel = Boolean(safeSource || category);
	const filterSummaryParts = [
		safeSource ? `来源 ${toSourceLabel(safeSource)}` : null,
		category ? `分类 ${CATEGORY_LABELS[category] ?? category}` : null,
	].filter((part): part is string => Boolean(part));
	const filterSummaryText =
		filterSummaryParts.length > 0
			? `，当前筛选：${filterSummaryParts.join("，")}`
			: "，当前为全部内容";

	let feed: Awaited<ReturnType<typeof apiClient.getDigestFeed>> | null = null;
	let errorCode: string | null = null;
	try {
		feed = await apiClient.getDigestFeed({
			source: safeSource,
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
		errorCode = toErrorCode(err);
	}

	const items = feed?.items ?? [];
	const nextCursor = feed?.next_cursor ?? null;
	const isFirstPage = !safeCursor;

	// 构建分页链接
	const buildPageUrl = ({
		cursorValue,
		prevCursorValue,
		pageValue,
	}: {
		cursorValue?: string;
		prevCursorValue?: string;
		pageValue: number;
	}) => {
		const params = new URLSearchParams();
		if (safeSource) {
			params.set("source", safeSource);
		}
		if (category) {
			params.set("category", category);
		}
		if (safeLimit !== 20) {
			params.set("limit", String(safeLimit));
		}
		if (pageValue > 1) {
			params.set("page", String(pageValue));
		}
		if (cursorValue) {
			params.set("cursor", cursorValue);
		}
		if (prevCursorValue) {
			params.set("prev_cursor", prevCursorValue);
		}
		const qs = params.toString();
		return `/feed${qs ? `?${qs}` : ""}`;
	};
	const retryHref = buildPageUrl({
		cursorValue: safeCursor,
		prevCursorValue: safePrevCursor,
		pageValue: safePage,
	});

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
						<select name="source" defaultValue={sourceSelectValue}>
							{SOURCE_OPTIONS.map((option) => (
								<option key={option.value || "all"} value={option.value}>
									{option.label}
								</option>
							))}
						</select>
					</label>
					<label>
						分类
						<select name="category" defaultValue={category}>
							<option value="">全部分类</option>
							<option value="tech">科技</option>
							<option value="creator">创作者</option>
							<option value="macro">宏观</option>
							<option value="ops">运维</option>
							<option value="misc">其他</option>
						</select>
					</label>
					<label>
						每页条数
						<input name="limit" type="number" min={1} max={100} defaultValue={String(safeLimit)} />
					</label>
					<button type="submit" className="primary">
						筛选
					</button>
					{isFiltered && (
						<Link href="/feed" className="btn-link" data-interaction="link-muted">
							清除筛选
						</Link>
					)}
				</form>
			</section>

			{errorCode ? (
				<>
					<p className="alert alert-enter error" role="alert" aria-live="assertive">
						{getFlashMessage(errorCode)}
					</p>
					<Link href={retryHref} className="btn-link" data-interaction="link-muted">
						重试当前页面
					</Link>
				</>
			) : null}
			{!errorCode ? (
				<p className="small" role="status" aria-live="polite">
					已加载 {items.length} 条摘要{filterSummaryText}。
				</p>
			) : null}

			{/* 空状态 */}
			{!errorCode && items.length === 0 ? (
				<section className="card empty-state-card">
					<p className="empty-state-title">暂无 AI 摘要内容</p>
					<p className="small">
						{isFiltered
							? "当前筛选条件下没有结果，试试清除筛选。"
							: "还没有处理过的视频或文章。请先去添加订阅并触发采集。"}
					</p>
					{!isFiltered && (
						<div className="inline mt-8">
							<Link href="/subscriptions" className="btn-cta">
								→ 前往订阅管理
							</Link>
						</div>
					)}
				</section>
			) : null}

			{/* Feed 内容卡列表 */}
			{items.map((item) => {
				const safeVideoUrl = sanitizeExternalUrl(item.video_url);
				return (
					<article
						className="card card-feed stack"
						key={item.feed_id}
						data-category={item.category}
					>
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
								<Link
									href={`/artifacts?job_id=${encodeURIComponent(item.job_id)}`}
									data-interaction="link-primary"
								>
									查看产物
								</Link>
								{safeVideoUrl ? (
									<a
										href={safeVideoUrl}
										target="_blank"
										rel="noreferrer noopener"
										aria-label="打开原始链接（在新标签页打开）"
										data-interaction="link-muted"
									>
										打开原始链接（在新标签页打开）
									</a>
								) : (
									<span className="small">原始链接不可用</span>
								)}
							</div>
							<span className="small feed-item-ops">
								<code>{item.artifact_type}</code>
								{" · "}
								<Link
									href={`/jobs?job_id=${encodeURIComponent(item.job_id)}`}
									className="job-id-link"
									data-interaction="link-muted"
								>
									{item.job_id.slice(0, 8)}…
								</Link>
							</span>
						</div>
					</article>
				);
			})}

			{/* 分页 */}
			{!errorCode && items.length > 0 ? (
				<nav className="card feed-pagination" aria-label="分页">
					<div className="inline">
						{!isFirstPage && (
							<Link
								href={buildPageUrl({
									cursorValue: safePrevCursor,
									pageValue: Math.max(1, safePage - 1),
								})}
								className="btn-page"
							>
								← 上一页
							</Link>
						)}
						{isFiltered && hasVisibleFilterLabel && (
							<span className="small">
								{safeSource && `来源：${toSourceLabel(safeSource)}`}
								{safeSource && category && " · "}
								{category && `分类：${CATEGORY_LABELS[category] ?? category}`}
							</span>
						)}
					</div>
					<div className="inline">
						<span className="small pagination-info">
							{`第 ${safePage} 页`}
							{nextCursor === null ? "  · 已到末页" : ""}
						</span>
						{nextCursor !== null ? (
							<Link
								href={buildPageUrl({
									cursorValue: nextCursor,
									prevCursorValue: safeCursor,
									pageValue: safePage + 1,
								})}
								className="btn-page btn-page-primary"
							>
								下一页 →
							</Link>
						) : (
							<button
								type="button"
								className="btn-page btn-page-disabled"
								disabled
								aria-disabled="true"
							>
								已到末页
							</button>
						)}
					</div>
				</nav>
			) : null}
		</div>
	);
}
