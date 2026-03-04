import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";

import { getFlashMessage, toErrorCode } from "@/app/flash-message";
import { MarkdownPreview } from "@/components/markdown-preview";

export const metadata: Metadata = { title: "产物" };

import { apiClient } from "@/lib/api/client";
import type { ArtifactMarkdownWithMeta } from "@/lib/api/types";
import { buildArtifactAssetUrl } from "@/lib/api/url";
import { resolveSearchParams, type SearchParamsInput } from "@/lib/search-params";

type ArtifactsPageProps = {
	searchParams?: SearchParamsInput;
};

function extractFrameFiles(meta: Record<string, unknown> | null): string[] {
	if (!meta) {
		return [];
	}
	const frameFiles = meta.frame_files;
	if (!Array.isArray(frameFiles)) {
		return [];
	}
	return frameFiles.filter((item): item is string => typeof item === "string" && item.length > 0);
}

function extractArtifactJobId(jobId: string, meta: Record<string, unknown> | null): string {
	if (jobId) {
		return jobId;
	}
	if (!meta) {
		return "";
	}

	const job = meta.job;
	if (!job || typeof job !== "object") {
		return "";
	}

	const rawJobId = (job as Record<string, unknown>).id;
	return typeof rawJobId === "string" ? rawJobId : "";
}

function inferImageMime(path: string): string | null {
	const lower = path.toLowerCase();
	if (lower.endsWith(".png")) {
		return "image/png";
	}
	if (lower.endsWith(".webp")) {
		return "image/webp";
	}
	if (lower.endsWith(".jpg") || lower.endsWith(".jpeg")) {
		return "image/jpeg";
	}
	return null;
}

export default async function ArtifactsPage({ searchParams }: ArtifactsPageProps) {
	const { job_id: jobId, video_url: videoUrl } = await resolveSearchParams(searchParams, [
		"job_id",
		"video_url",
	] as const);
	const hasLookupParams = Boolean(jobId || videoUrl);
	const retryParams = new URLSearchParams();
	if (jobId) {
		retryParams.set("job_id", jobId);
	}
	if (videoUrl) {
		retryParams.set("video_url", videoUrl);
	}
	const retryHref = retryParams.toString() ? `/artifacts?${retryParams.toString()}` : "/artifacts";

	let errorCode: string | null = null;
	let payload: ArtifactMarkdownWithMeta | null = null;

	if (hasLookupParams) {
		payload = await apiClient
			.getArtifactMarkdown({
				job_id: jobId || undefined,
				video_url: videoUrl || undefined,
				include_meta: true,
			})
			.catch((err) => {
				errorCode = toErrorCode(err);
				return null;
			});
	}

	const screenshotIndex = payload ? extractFrameFiles(payload.meta) : [];
	const artifactJobId = payload ? extractArtifactJobId(jobId, payload.meta) : "";
	const embeddedScreenshots = screenshotIndex.map((path) => ({
		path,
		mimeType: inferImageMime(path),
		assetUrl: artifactJobId ? buildArtifactAssetUrl(artifactJobId, path) : null,
	}));

	return (
		<div className="stack">
			<section className="card stack">
				<h2>产物查询</h2>
				<p className="small">输入任务 ID 或视频 URL，加载对应的 Markdown 产物和截图。</p>
				<form
					method="GET"
					className="stack"
					data-require-one="job_id,video_url"
					data-require-one-exclusive="true"
				>
					<label>
						任务 ID
						<input
							name="job_id"
							type="text"
							defaultValue={jobId}
							placeholder="9be4cbe7-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
							data-field-kind="identifier"
						/>
					</label>

					<p className="small artifacts-or-divider">或</p>

					<label>
						视频 URL
						<input
							name="video_url"
							type="url"
							defaultValue={videoUrl}
							placeholder="https://www.youtube.com/watch?v=..."
							data-field-kind="url"
						/>
					</label>

					<div>
						<button type="submit" className="primary">
							加载产物
						</button>
					</div>
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

			{payload ? (
				<>
					<section className="card stack">
						<h3>内嵌截图</h3>
						{embeddedScreenshots.length === 0 ? (
							<p className="small">meta.frame_files 中未找到截图。</p>
						) : (
							<ol>
								{embeddedScreenshots.map((item, index) => (
									<li key={item.path} className="stack">
										{item.assetUrl ? (
											<>
												<a
													className="screenshot-link"
													href={item.assetUrl}
													target="_blank"
													rel="noreferrer"
													data-interaction="link-primary"
												>
													查看截图 {index + 1}
												</a>
												{item.mimeType ? (
													<Image
														alt={`截图 ${index + 1}：${item.path}`}
														src={item.assetUrl}
														unoptimized
														width={1280}
														height={720}
														loading="lazy"
														className="artifacts-screenshot-image"
													/>
												) : (
													<p className="small">
														截图文件格式不支持内嵌预览，请通过链接打开：<code>{item.path}</code>
													</p>
												)}
											</>
										) : (
											<p className="small">
												缺少 job_id，无法预览截图，回退路径：<code>{item.path}</code>
											</p>
										)}
									</li>
								))}
							</ol>
						)}
					</section>

					<section className="card stack">
						<h3>截图索引（备用链接）</h3>
						{screenshotIndex.length === 0 ? (
							<p className="small">meta.frame_files 中未找到截图路径。</p>
						) : (
							<ol>
								{screenshotIndex.map((path) => (
									<li key={path}>
										{artifactJobId ? (
											<a
												className="screenshot-link"
												href={buildArtifactAssetUrl(artifactJobId, path)}
												target="_blank"
												rel="noreferrer"
												data-interaction="link-muted"
											>
												打开 <code>{path}</code>
											</a>
										) : (
											<code>{path}</code>
										)}
									</li>
								))}
							</ol>
						)}
					</section>

					<section className="card stack">
						<h3>Markdown 预览</h3>
						<MarkdownPreview markdown={payload.markdown} />
					</section>
				</>
			) : !hasLookupParams ? null : !errorCode ? (
				<p className="small" role="status" aria-live="polite">
					产物请求已完成，但未返回 Markdown 内容。
				</p>
			) : null}
		</div>
	);
}
