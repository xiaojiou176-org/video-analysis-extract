"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { MarkdownPreview } from "@/components/markdown-preview";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { ScrollArea } from "@/components/ui/scroll-area";
import { apiClient } from "@/lib/api/client";
import { sanitizeExternalUrl } from "@/lib/api/url";
import { ChevronDownIcon, ChevronRightIcon, ExternalLinkIcon } from "lucide-react";

function extractHeadings(markdown: string): { level: number; text: string; id: string }[] {
	const headings: { level: number; text: string; id: string }[] = [];
	const lines = markdown.split("\n");
	for (const line of lines) {
		const match = line.match(/^(#{1,6})\s+(.+)$/);
		if (match) {
			const level = match[1].length;
			const text = match[2].trim();
			const id = text
				.toLowerCase()
				.replace(/\s+/g, "-")
				.replace(/[^\p{L}\p{N}-]/gu, "");
			headings.push({ level, text, id });
		}
	}
	return headings;
}

function toSourceLabel(source: string): string {
	const normalized = source.trim().toLowerCase();
	if (normalized === "youtube") return "YouTube";
	if (normalized === "bilibili") return "Bilibili";
	if (normalized === "rss" || normalized === "rss_generic") return "RSS";
	return source || "未知";
}

type ReadingPaneProps = {
	jobId: string | null;
	title?: string;
	source?: string;
	sourceName?: string;
	videoUrl?: string;
	publishedAt?: string;
	publishedDateLabel?: string;
};

export function ReadingPane({
	jobId,
	title,
	source,
	sourceName,
	videoUrl,
	publishedAt,
	publishedDateLabel,
}: ReadingPaneProps) {
	const [markdown, setMarkdown] = useState<string | null>(null);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState(false);
	const [reloadNonce, setReloadNonce] = useState(0);
	const [outlineOpen, setOutlineOpen] = useState(true);

	useEffect(() => {
		if (!jobId) {
			queueMicrotask(() => {
				setMarkdown(null);
				setError(false);
			});
			return;
		}
		let cancelled = false;
		queueMicrotask(() => {
			setLoading(true);
			setError(false);
		});
		apiClient
			.getArtifactMarkdown({ job_id: jobId, include_meta: true })
			.then((payload) => {
				if (cancelled) return;
				setMarkdown(payload.markdown);
				setLoading(false);
			})
			.catch(() => {
				if (cancelled) return;
				setError(true);
				setMarkdown(null);
				setLoading(false);
			});
		return () => {
			cancelled = true;
		};
	}, [jobId, reloadNonce]);

	if (!jobId) {
		return (
			<div className="feed-reading-pane-shell feed-reading-state" data-reading-state="empty">
				<p className="feed-reading-state-title">选择左侧条目查看摘要与正文</p>
				<p className="feed-reading-state-meta">视频与文章均支持 AI 摘要与大纲</p>
			</div>
		);
	}

	if (loading) {
		return (
			<div className="feed-reading-pane-shell feed-reading-state" data-reading-state="loading">
				<div className="feed-reading-spinner" aria-hidden="true" />
				<p className="feed-reading-state-meta">加载中…</p>
			</div>
		);
	}

	if (error) {
		return (
			<div className="feed-reading-pane-shell feed-reading-state" data-reading-state="error">
				<p className="feed-reading-error">正文暂时不可用，请稍后重试。</p>
				<Button
					type="button"
					variant="link"
					className="btn-link h-auto p-0"
					onClick={() => {
						setError(false);
						setLoading(true);
						setReloadNonce((value) => value + 1);
					}}
					data-testid="reading-pane-retry"
				>
					重试
				</Button>
			</div>
		);
	}

	const headings = markdown ? extractHeadings(markdown) : [];
	const safeVideoUrl = videoUrl ? sanitizeExternalUrl(videoUrl) : null;
	const sourceLabel = source ? toSourceLabel(source) : null;

	return (
		<div className="feed-reading-pane-shell" data-reading-state="content">
			<ScrollArea className="flex-1">
				<article className="prose prose-sm dark:prose-invert reading-pane-prose feed-reading-article">
					<header className="feed-reading-header">
						<h2 className="feed-reading-title">{title || "无标题"}</h2>
						<div className="feed-reading-meta">
							{sourceLabel ? <span>{sourceName ? `${sourceLabel} · ${sourceName}` : sourceLabel}</span> : null}
							{publishedAt ? <time dateTime={publishedAt}>{publishedDateLabel ?? publishedAt}</time> : null}
						</div>
						<div className="feed-reading-links">
							<Link
								href={`/jobs?job_id=${encodeURIComponent(jobId)}`}
								className="feed-reading-link"
								data-interaction="link-muted"
							>
								{jobId.slice(0, 8)}…
							</Link>
							{safeVideoUrl ? (
								<a
									href={safeVideoUrl}
									target="_blank"
									rel="noreferrer noopener"
									className="feed-reading-link"
									data-interaction="link-primary"
								>
									打开原文
									<ExternalLinkIcon className="size-3" />
								</a>
							) : null}
						</div>
					</header>

					{headings.length > 0 ? (
						<Collapsible open={outlineOpen} onOpenChange={setOutlineOpen}>
							<CollapsibleTrigger className="feed-outline-trigger">
								{outlineOpen ? (
									<ChevronDownIcon className="size-4 text-muted-foreground" />
								) : (
									<ChevronRightIcon className="size-4 text-muted-foreground" />
								)}
								大纲
							</CollapsibleTrigger>
							<CollapsibleContent>
								<nav className="feed-outline-panel">
									<ul className="space-y-1.5">
										{headings.map((heading) => (
											<li
												key={heading.id}
												className="text-sm"
												style={{ paddingLeft: `${(heading.level - 1) * 14}px` }}
											>
												<a href={`#${heading.id}`} className="feed-outline-link" data-interaction="link-muted">
													{heading.text}
												</a>
											</li>
										))}
									</ul>
								</nav>
							</CollapsibleContent>
						</Collapsible>
					) : null}

					{markdown ? (
						<div className="markdown-body">
							<MarkdownPreview markdown={markdown} />
						</div>
					) : (
						<p className="text-muted-foreground">无正文内容</p>
					)}
				</article>
			</ScrollArea>
		</div>
	);
}
