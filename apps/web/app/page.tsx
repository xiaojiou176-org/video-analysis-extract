import type { Metadata } from "next";
import Link from "next/link";

import { getActionSessionTokenForForm } from "@/app/action-security";
import { pollIngestAction, processVideoAction } from "@/app/actions";
import { getFlashMessage } from "@/app/flash-message";
import { toDisplayStatus } from "@/app/status";
import { apiClient } from "@/lib/api/client";
import { resolveSearchParams, type SearchParamsInput } from "@/lib/search-params";

export const metadata: Metadata = { title: "首页" };

type DashboardPageProps = {
	searchParams?: SearchParamsInput;
};

function renderAlert(status: string, code: string) {
	if (!status || !code) {
		return null;
	}
	const isError = status === "error";
	const className = status === "error" ? "alert error" : "alert success";
	return (
		<p
			className={className}
			role={isError ? "alert" : "status"}
			aria-live={isError ? "assertive" : "polite"}
		>
			{getFlashMessage(code)}
		</p>
	);
}

function toPlatformLabel(platform: string): string {
	const normalized = platform.trim().toLowerCase();
	if (normalized === "youtube") {
		return "YouTube";
	}
	if (normalized === "bilibili") {
		return "Bilibili";
	}
	return platform;
}

export default async function DashboardPage({ searchParams }: DashboardPageProps) {
	const { status, code } = await resolveSearchParams(searchParams, ["status", "code"] as const);
	const sessionToken = getActionSessionTokenForForm();

	const [subscriptionsResult, videosResult] = await Promise.all([
		apiClient
			.listSubscriptions()
			.then((data) => ({ data, errorCode: null as string | null }))
			.catch(() => ({
				data: [] as Awaited<ReturnType<typeof apiClient.listSubscriptions>>,
				errorCode: "ERR_REQUEST_FAILED",
			})),
		apiClient
			.listVideos({ limit: 200 })
			.then((data) => ({ data, errorCode: null as string | null }))
			.catch(() => ({
				data: [] as Awaited<ReturnType<typeof apiClient.listVideos>>,
				errorCode: "ERR_REQUEST_FAILED",
			})),
	]);

	const subscriptions = subscriptionsResult.data;
	const videos = videosResult.data;
	const loadErrorCode = subscriptionsResult.errorCode ?? videosResult.errorCode;
	const runningJobs = videos.filter(
		(video) => video.status === "running" || video.status === "queued",
	).length;
	const failedJobs = videos.filter((video) => video.status === "failed").length;

	return (
		<div className="stack">
			{renderAlert(status, code)}
			{loadErrorCode ? (
				<p className="alert error" role="alert" aria-live="assertive">
					{getFlashMessage(loadErrorCode)}
				</p>
			) : null}

			<section className="grid grid-cols-2">
				<div className="card metric">
					<span className="metric-label">订阅数</span>
					<span className="metric-value">{subscriptions.length}</span>
					{subscriptions.length === 0 && !loadErrorCode ? (
						<Link
							href="/subscriptions"
							className="metric-cta"
							aria-label="添加第一个订阅，前往订阅管理"
						>
							添加第一个订阅 →
						</Link>
					) : null}
				</div>
				<div className="card metric">
					<span className="metric-label">已发现视频</span>
					<span className="metric-value">{videos.length}</span>
				</div>
				<div className="card metric" data-accent={runningJobs > 0 ? "warning" : undefined}>
					<span className="metric-label">运行中/排队</span>
					<span className="metric-value">{runningJobs}</span>
				</div>
				<div className="card metric" data-accent={failedJobs > 0 ? "error" : undefined}>
					<span className="metric-label">失败任务</span>
					<span className="metric-value">{failedJobs}</span>
					{failedJobs > 0 ? (
						<Link
							href="/jobs"
							className="metric-cta metric-cta-error"
							aria-label="查看失败任务，前往任务列表"
						>
							查看失败任务 →
						</Link>
					) : null}
				</div>
			</section>

			<section className="grid grid-cols-2">
				<div className="card stack">
					<h2>拉取采集</h2>
					<form action={pollIngestAction} className="stack form-fill">
						<input type="hidden" name="session_token" value={sessionToken} />
						<label>
							平台（可选）
							<select name="platform" defaultValue="">
								<option value="">全部</option>
								<option value="youtube">YouTube</option>
								<option value="bilibili">Bilibili</option>
							</select>
						</label>
						<label>
							最多拉取视频数
							<input name="max_new_videos" type="number" min={1} max={500} defaultValue={50} />
						</label>
						<div className="submit-row">
							<button className="primary" type="submit">
								触发采集
							</button>
						</div>
					</form>
				</div>

				<div className="card stack">
					<h2>处理单个视频</h2>
					<form
						action={processVideoAction}
						className="stack form-fill"
						data-auto-disable-required="true"
					>
						<input type="hidden" name="session_token" value={sessionToken} />
						<label>
							平台 *
							<select name="platform" defaultValue="youtube">
								<option value="youtube">YouTube</option>
								<option value="bilibili">Bilibili</option>
							</select>
						</label>
						<label>
							视频链接 *
							<input
								name="url"
								type="url"
								required
								placeholder="https://www.youtube.com/watch?v=..."
								data-field-kind="url"
							/>
						</label>
						<label>
							模式 *
							<select name="mode" defaultValue="full">
								<option value="full">完整</option>
								<option value="text_only">纯文本</option>
								<option value="refresh_comments">刷新评论</option>
								<option value="refresh_llm">刷新 LLM</option>
							</select>
						</label>
						<div className="checkbox-row">
							<input id="force-run" name="force" type="checkbox" />
							<label htmlFor="force-run">强制执行</label>
						</div>
						<div className="submit-row">
							<button className="primary" type="submit">
								开始处理
							</button>
						</div>
					</form>
				</div>
			</section>

			<section className="card stack">
				<h2>最近视频</h2>
				{videos.length === 0 && !loadErrorCode ? (
					<output className="small empty-state" aria-live="polite">
						暂无视频。
					</output>
				) : null}
				{videos.length === 0 && loadErrorCode ? (
					<output className="small" aria-live="polite">
						当前无法加载视频列表。
					</output>
				) : null}
				{videos.length > 0 ? (
					<div className="table-scroll">
						<table>
							<caption className="sr-only">最近视频列表</caption>
							<thead>
								<tr>
									<th scope="col">标题</th>
									<th scope="col">平台</th>
									<th scope="col">状态</th>
									<th scope="col">最近任务</th>
								</tr>
							</thead>
							<tbody>
								{videos.slice(0, 10).map((video) => {
									const statusDisplay = toDisplayStatus(video.status);
									return (
										<tr key={video.id}>
											<td>{video.title ?? video.video_uid}</td>
											<td>{toPlatformLabel(video.platform)}</td>
											<td>
												<span className={`status-chip status-${statusDisplay.css}`}>
													{statusDisplay.label}
												</span>
											</td>
											<td>
												{video.last_job_id ? (
													<Link href={`/jobs?job_id=${encodeURIComponent(video.last_job_id)}`}>
														{video.last_job_id}
													</Link>
												) : (
													"-"
												)}
											</td>
										</tr>
									);
								})}
							</tbody>
						</table>
					</div>
				) : null}
			</section>
		</div>
	);
}
