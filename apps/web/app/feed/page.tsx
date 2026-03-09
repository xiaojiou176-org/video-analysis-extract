import type { Metadata } from "next";
import Link from "next/link";

import { getActionSessionTokenForForm } from "@/app/action-security";
import { getFlashMessage, toErrorCode } from "@/app/flash-message";
import { EntryList } from "@/components/entry-list";
import { FormSelectField } from "@/components/form-field";
import { ReadingPane } from "@/components/reading-pane";
import { SyncNowButton } from "@/components/sync-now-button";
import { Button } from "@/components/ui/button";
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
	if (normalized === "youtube") return "YouTube";
	if (normalized === "bilibili") return "Bilibili";
	if (normalized === "rss" || normalized === "rss_generic") return "RSS";
	return source || "未知";
}

function formatPublishedDateLabel(value: string | undefined): string | undefined {
	if (!value) return undefined;
	const parsed = new Date(value);
	if (Number.isNaN(parsed.getTime())) return value;
	return new Intl.DateTimeFormat("zh-CN", {
		year: "numeric",
		month: "long",
		day: "numeric",
		timeZone: "UTC",
	}).format(parsed);
}

export default async function FeedPage({ searchParams }: FeedPageProps) {
	const sessionToken = getActionSessionTokenForForm();
	const { source, category, sub, limit, cursor, prev_cursor, page, item } = await resolveSearchParams(
		searchParams,
		["source", "category", "sub", "limit", "cursor", "prev_cursor", "page", "item"],
	);

	const parsedLimit = Number.parseInt(limit, 10);
	const safeLimit = Number.isFinite(parsedLimit) && parsedLimit > 0 ? Math.min(parsedLimit, 100) : 20;
	const safeCursor = cursor.trim() || undefined;
	const safePrevCursor = prev_cursor.trim() || undefined;
	const parsedPage = Number.parseInt(page, 10);
	const inferredPage = safeCursor ? 2 : 1;
	const safePage = Number.isFinite(parsedPage) && parsedPage > 0 ? parsedPage : inferredPage;
	const normalizedSource = source.trim().toLowerCase();
	const safeSource = normalizedSource || undefined;
	const safeSubscriptionId = sub.trim() || undefined;
	const sourceSelectValue = toSourceSelectValue(source);
	const isFiltered = Boolean(safeSource || category || safeSubscriptionId);
	const hasVisibleFilterLabel = Boolean(safeSource || category || safeSubscriptionId);
	const selectedJobId = item.trim() || null;

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
			subscription_id: safeSubscriptionId,
			limit: safeLimit,
			cursor: safeCursor,
		});
	} catch (err) {
		errorCode = toErrorCode(err);
	}

	const items = feed?.items ?? [];
	const nextCursor = feed?.next_cursor ?? null;
	const isFirstPage = !safeCursor;

	const buildPageUrl = ({
		cursorValue,
		prevCursorValue,
		pageValue,
		itemValue,
	}: {
		cursorValue?: string;
		prevCursorValue?: string;
		pageValue: number;
		itemValue?: string;
	}) => {
		const params = new URLSearchParams();
		if (safeSource) params.set("source", safeSource);
		if (category) params.set("category", category);
		if (safeSubscriptionId) params.set("sub", safeSubscriptionId);
		if (safeLimit !== 20) params.set("limit", String(safeLimit));
		if (pageValue > 1) params.set("page", String(pageValue));
		if (cursorValue) params.set("cursor", cursorValue);
		if (prevCursorValue) params.set("prev_cursor", prevCursorValue);
		if (itemValue) params.set("item", itemValue);
		const qs = params.toString();
		return `/feed${qs ? `?${qs}` : ""}`;
	};

	const buildItemUrl = ({ item: itemId }: { item?: string }) =>
		buildPageUrl({
			cursorValue: safeCursor,
			prevCursorValue: safePrevCursor,
			pageValue: safePage,
			itemValue: itemId ?? undefined,
		});

	const retryHref = buildPageUrl({
		cursorValue: safeCursor,
		prevCursorValue: safePrevCursor,
		pageValue: safePage,
		itemValue: selectedJobId ?? undefined,
	});

	const selectedItem = selectedJobId ? items.find((feedItem) => feedItem.job_id === selectedJobId) : null;

	return (
		<div className="folo-page-shell folo-unified-shell">
			<div className="folo-page-header">
				<div className="folo-page-title-row">
					<div>
						<p className="folo-page-kicker">Folo Feed</p>
						<h1 className="folo-page-title" data-route-heading>
							主阅读流
						</h1>
						<p className="folo-page-subtitle">
							在同一阅读流中浏览摘要条目与正文，并保留按来源、分类快速筛选的工作路径。
						</p>
					</div>
					<div className="folo-page-toolbar">
						<SyncNowButton sessionToken={sessionToken} />
					</div>
				</div>
			</div>

				<section className="folo-panel folo-surface feed-filter-panel" aria-label="摘要筛选">
					<form method="GET" className="feed-filter-form">
						<input type="hidden" name="item" value={selectedJobId ?? ""} />
						<div className="feed-filter-selects">
							<FormSelectField
								name="source"
								label="来源"
								defaultValue={sourceSelectValue}
								options={SOURCE_OPTIONS.map((option) => ({ value: option.value, label: option.label }))}
								fieldClassName="feed-filter-field"
								labelClassName="sr-only"
								selectClassName="feed-filter-select"
							/>
							<FormSelectField
								name="category"
								label="分类"
								defaultValue={category}
								options={[
									{ value: "", label: "全部分类" },
									...Object.entries(CATEGORY_LABELS).map(([key, value]) => ({ value: key, label: value })),
								]}
								fieldClassName="feed-filter-field"
								labelClassName="sr-only"
								selectClassName="feed-filter-select"
							/>
						</div>
					{safeSubscriptionId ? <input type="hidden" name="sub" value={safeSubscriptionId} /> : null}
					<input type="hidden" name="limit" value={String(safeLimit)} />
					<div className="feed-filter-actions">
						<Button
							type="submit"
							variant="hero"
							size="sm"
							data-interaction="control"
							data-testid="feed-filter-submit"
						>
							筛选
						</Button>
						{isFiltered ? (
							<Button asChild variant="ghost" size="sm" className="feed-filter-clear" data-testid="feed-filter-clear">
								<Link href={selectedJobId ? `/feed?item=${encodeURIComponent(selectedJobId)}` : "/feed"}>清除</Link>
							</Button>
						) : null}
					</div>
				</form>
			</section>

			{errorCode ? (
				<>
					<p className="alert alert-enter error" role="alert" aria-live="assertive">
						{getFlashMessage(errorCode)}
					</p>
					<Button asChild variant="surface" size="sm" data-interaction="link-muted">
						<Link href={retryHref}>重试当前页面</Link>
					</Button>
				</>
			) : null}

			{!errorCode && items.length === 0 ? (
				<section className="folo-panel folo-surface folo-empty-panel">
					<p className="folo-empty-title">暂无 AI 摘要内容</p>
					<p className="folo-empty-description">
						{isFiltered
							? "当前筛选条件下没有结果，试试清除筛选。"
							: "还没有处理过的视频或文章。请先去添加订阅并触发采集。"}
					</p>
					{!isFiltered ? (
						<Button asChild variant="hero" size="sm" data-interaction="cta">
							<Link href="/subscriptions">前往订阅管理</Link>
						</Button>
					) : null}
				</section>
			) : (
				<div className="feed-main-flow">
					<EntryList
						items={items.map((feedItem) => ({
							...feedItem,
							href: buildItemUrl({ item: feedItem.job_id }),
						}))}
						selectedJobId={selectedJobId}
					/>
					<ReadingPane
						jobId={selectedJobId}
						title={selectedItem?.title}
						source={selectedItem?.source}
						sourceName={selectedItem?.source_name}
						videoUrl={selectedItem?.video_url}
						publishedAt={selectedItem?.published_at}
						publishedDateLabel={formatPublishedDateLabel(selectedItem?.published_at)}
					/>
				</div>
			)}

			{!errorCode && items.length > 0 ? (
				<nav className="folo-panel folo-surface folo-pagination-shell" aria-label="分页">
					<div className="folo-pagination-group">
						{!isFirstPage ? (
							<Button asChild variant="surface" size="sm">
								<Link
									href={buildPageUrl({
										cursorValue: safePrevCursor,
										pageValue: Math.max(1, safePage - 1),
										itemValue: selectedJobId ?? undefined,
									})}
								>
									← 上一页
								</Link>
							</Button>
						) : null}
						{isFiltered && hasVisibleFilterLabel ? (
							<span className="folo-filter-label">
								{safeSource && `${toSourceLabel(safeSource)}`}
								{safeSource && category ? " · " : ""}
								{category && `${CATEGORY_LABELS[category] ?? category}`}
								{(safeSource || category) && safeSubscriptionId ? " · " : ""}
								{safeSubscriptionId ? "订阅源" : ""}
							</span>
						) : null}
					</div>
					<div className="folo-pagination-group">
						<span className="folo-filter-label">页码 {safePage}</span>
						{nextCursor !== null ? (
							<Button asChild variant="surface" size="sm">
								<Link
									href={buildPageUrl({
										cursorValue: nextCursor,
										prevCursorValue: safeCursor,
										pageValue: safePage + 1,
										itemValue: selectedJobId ?? undefined,
									})}
								>
									下一页 →
								</Link>
							</Button>
						) : null}
					</div>
				</nav>
			) : null}
		</div>
	);
}
