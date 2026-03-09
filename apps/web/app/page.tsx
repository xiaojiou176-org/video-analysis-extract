import type { Metadata } from "next";
import Link from "next/link";

import { getActionSessionTokenForForm } from "@/app/action-security";
import { pollIngestAction, processVideoAction } from "@/app/actions";
import { getFlashMessage } from "@/app/flash-message";
import { toDisplayStatus } from "@/app/status";
import {
	FormCheckboxField,
	FormInputField,
	FormSelectField,
} from "@/components/form-field";
import { StatusBadge, mapStatusCssToTone } from "@/components/status-badge";
import { SubmitButton } from "@/components/submit-button";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api/client";
import { resolveSearchParams, type SearchParamsInput } from "@/lib/search-params";

export const metadata: Metadata = { title: "首页" };

type DashboardPageProps = {
	searchParams?: SearchParamsInput;
};

const POLL_PLATFORM_OPTIONS = [
	{ value: "", label: "全部" },
	{ value: "youtube", label: "YouTube" },
	{ value: "bilibili", label: "Bilibili" },
];

const PROCESS_PLATFORM_OPTIONS = [
	{ value: "youtube", label: "YouTube" },
	{ value: "bilibili", label: "Bilibili" },
];

const PROCESS_MODE_OPTIONS = [
	{ value: "full", label: "完整" },
	{ value: "text_only", label: "纯文本" },
	{ value: "refresh_comments", label: "刷新评论" },
	{ value: "refresh_llm", label: "刷新 LLM" },
];

function renderAlert(status: string, code: string) {
	if (!status || !code) {
		return null;
	}
	const isError = status === "error";
	return (
		<p
			className={`alert alert-enter ${isError ? "error" : "success"}`}
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

function DashboardStatusBadge({ status }: { status: string | null }) {
	const normalized = status ?? "idle";
	const statusDisplay = toDisplayStatus(normalized);
	return <StatusBadge label={statusDisplay.label} tone={mapStatusCssToTone(statusDisplay.css)} />;
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
	const subscriptionsUnavailable = subscriptionsResult.errorCode !== null;
	const videosUnavailable = videosResult.errorCode !== null;
	const runningJobs = videos.filter((video) => video.status === "running" || video.status === "queued").length;
	const failedJobs = videos.filter((video) => video.status === "failed").length;

	return (
		<div className="folo-page-shell folo-unified-shell">
			<div className="folo-page-header">
				<p className="folo-page-kicker">Folo Command Center</p>
				<h1 className="folo-page-title" data-route-heading>
					运营总览
				</h1>
				<p className="folo-page-subtitle">
					统一管理订阅、采集、处理任务与最近产物，保持日常巡检在一个主视图完成。
				</p>
			</div>

			{renderAlert(status, code)}
			{loadErrorCode ? (
				<Card className="folo-surface border-destructive/40 bg-destructive/5" role="alert" aria-live="assertive">
					<CardHeader className="gap-2">
						<CardTitle className="text-base">加载失败</CardTitle>
						<CardDescription>{getFlashMessage(loadErrorCode)}</CardDescription>
					</CardHeader>
					<CardContent className="pt-0">
						<Button asChild variant="outline" size="sm">
							<Link href="/">重试当前页面</Link>
						</Button>
					</CardContent>
				</Card>
			) : null}

			<section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-label="关键指标">
				<Card className="folo-surface overflow-hidden border-border/70">
					<CardHeader className="gap-2">
						<CardDescription>订阅数</CardDescription>
						<div
							className="text-3xl font-semibold"
							aria-label={subscriptionsUnavailable ? "订阅数数据暂不可用" : undefined}
						>
							{subscriptionsUnavailable ? "--" : subscriptions.length}
						</div>
					</CardHeader>
					<CardContent className="space-y-2 pt-0">
						{subscriptionsUnavailable ? (
							<p className="text-sm text-muted-foreground" role="status" aria-live="polite">
								数据暂不可用
							</p>
						) : null}
							{subscriptions.length === 0 && !subscriptionsUnavailable ? (
								<Button asChild variant="link" size="sm" className="h-auto px-0">
									<Link href="/subscriptions">
										添加第一个订阅 →
									</Link>
								</Button>
							) : null}
					</CardContent>
				</Card>
				<Card className="folo-surface overflow-hidden border-border/70">
					<CardHeader className="gap-2">
						<CardDescription>已发现视频</CardDescription>
						<div
							className="text-3xl font-semibold"
							aria-label={videosUnavailable ? "已发现视频数据暂不可用" : undefined}
						>
							{videosUnavailable ? "--" : videos.length}
						</div>
					</CardHeader>
					<CardContent className="pt-0">
						{videosUnavailable ? (
							<p className="text-sm text-muted-foreground" role="status" aria-live="polite">
								数据暂不可用
							</p>
						) : null}
					</CardContent>
				</Card>
				<Card
					className={
						!videosUnavailable && runningJobs > 0
							? "folo-surface overflow-hidden border-amber-300/70 bg-amber-50/40 dark:border-amber-900 dark:bg-amber-950/15"
							: "folo-surface overflow-hidden border-border/70"
					}
				>
					<CardHeader className="gap-2">
						<CardDescription>运行中/排队</CardDescription>
						<div
							className="text-3xl font-semibold"
							aria-label={videosUnavailable ? "运行中/排队数据暂不可用" : undefined}
						>
							{videosUnavailable ? "--" : runningJobs}
						</div>
					</CardHeader>
					<CardContent className="pt-0">
						{videosUnavailable ? (
							<p className="text-sm text-muted-foreground" role="status" aria-live="polite">
								数据暂不可用
							</p>
						) : null}
					</CardContent>
				</Card>
				<Card
					className={
						!videosUnavailable && failedJobs > 0
							? "folo-surface overflow-hidden border-destructive/40 bg-destructive/5"
							: "folo-surface overflow-hidden border-border/70"
					}
				>
					<CardHeader className="gap-2">
						<CardDescription>失败任务</CardDescription>
						<div
							className="text-3xl font-semibold"
							aria-label={videosUnavailable ? "失败任务数据暂不可用" : undefined}
						>
							{videosUnavailable ? "--" : failedJobs}
						</div>
					</CardHeader>
					<CardContent className="space-y-2 pt-0">
						{videosUnavailable ? (
							<p className="text-sm text-muted-foreground" role="status" aria-live="polite">
								数据暂不可用
							</p>
						) : null}
							{!videosUnavailable && failedJobs > 0 ? (
								<Button asChild variant="link" size="sm" className="h-auto px-0">
									<Link href="/jobs">
										查看失败任务 →
									</Link>
								</Button>
							) : null}
					</CardContent>
				</Card>
			</section>

			<section className="grid gap-4 lg:grid-cols-2">
				<Card className="folo-surface border-border/70">
					<CardHeader>
						<h2 className="text-xl font-semibold">拉取采集</h2>
						<CardDescription id="poll-ingest-help">
							触发后会进入任务队列。可在任务页查看执行进度和失败原因。
						</CardDescription>
					</CardHeader>
					<CardContent>
						<form action={pollIngestAction} className="grid gap-4">
							<input type="hidden" name="session_token" value={sessionToken} suppressHydrationWarning />
							<FormSelectField
								id="poll-platform"
								label="平台（可选）"
								name="platform"
								defaultValue=""
								options={POLL_PLATFORM_OPTIONS}
							/>
							<FormInputField
								id="poll-max-new-videos"
								label="最多拉取视频数"
								name="max_new_videos"
								type="number"
								min={1}
								max={500}
								defaultValue={50}
							/>
							<div className="flex flex-wrap items-center gap-3">
								<SubmitButton pendingLabel="触发中…" statusText="正在触发采集任务">
									触发采集
								</SubmitButton>
								<Button asChild variant="outline" size="sm">
									<Link href="/jobs">查看任务队列 →</Link>
								</Button>
							</div>
						</form>
					</CardContent>
				</Card>

				<Card className="folo-surface border-border/70">
					<CardHeader>
						<h2 className="text-xl font-semibold">处理单个视频</h2>
						<CardDescription id="process-video-help">
							提交后将生成新任务。可在“最近视频”或任务页追踪状态。
						</CardDescription>
					</CardHeader>
					<CardContent>
						<form action={processVideoAction} className="grid gap-4" data-auto-disable-required="true">
							<input type="hidden" name="session_token" value={sessionToken} suppressHydrationWarning />
							<FormSelectField
								id="process-platform"
								label="平台 *"
								name="platform"
								defaultValue="youtube"
								options={PROCESS_PLATFORM_OPTIONS}
								required
							/>
							<FormInputField
								id="process-url"
								label="视频链接 *"
								name="url"
								type="url"
								required
								placeholder="https://www.youtube.com/watch?v=..."
								data-field-kind="url"
							/>
							<FormSelectField
								id="process-mode"
								label="模式 *"
								name="mode"
								defaultValue="full"
								options={PROCESS_MODE_OPTIONS}
								required
							/>
							<FormCheckboxField id="force-run" name="force" label="强制执行" />
							<div className="flex flex-wrap items-center gap-3">
								<SubmitButton pendingLabel="创建任务中…" statusText="正在创建视频处理任务">
									开始处理
								</SubmitButton>
								<Button asChild variant="outline" size="sm">
									<Link href="/jobs">查看任务详情 →</Link>
								</Button>
							</div>
						</form>
					</CardContent>
				</Card>
			</section>

			<section>
				<Card className="folo-surface border-border/70">
					<CardHeader className="flex flex-row items-start justify-between gap-4">
						<div className="space-y-2">
							<h2 className="text-xl font-semibold">最近视频</h2>
							<CardDescription>仅展示最近 10 条视频，点击任务 ID 可查看完整流水线详情。</CardDescription>
						</div>
						<Button asChild variant="link" size="sm" className="h-auto px-0">
							<Link href="/jobs">查看全部任务 →</Link>
						</Button>
					</CardHeader>
					<CardContent className="space-y-3">
						{videos.length === 0 && !loadErrorCode ? (
							<p className="text-sm text-muted-foreground" role="status" aria-live="polite">
								暂无视频。
							</p>
						) : null}
						{videos.length === 0 && loadErrorCode ? (
							<p className="text-sm text-muted-foreground" role="status" aria-live="polite">
								当前无法加载视频列表。
							</p>
						) : null}
						{videos.length > 0 ? (
							<div className="overflow-x-auto rounded-lg border border-border/70">
								<table className="min-w-[680px] w-full text-sm">
									<caption className="sr-only">最近视频列表</caption>
									<thead className="bg-muted/40 text-left text-xs uppercase tracking-wide text-muted-foreground">
										<tr>
											<th scope="col" className="px-4 py-3 font-medium">
												标题
											</th>
											<th scope="col" className="px-4 py-3 font-medium">
												平台
											</th>
											<th scope="col" className="px-4 py-3 font-medium">
												状态
											</th>
											<th scope="col" className="px-4 py-3 font-medium">
												最近任务
											</th>
										</tr>
									</thead>
									<tbody>
										{videos.slice(0, 10).map((video) => (
											<tr key={video.id} className="border-t border-border/60">
												<td className="px-4 py-3 align-top">{video.title ?? video.video_uid}</td>
												<td className="px-4 py-3 align-top">{toPlatformLabel(video.platform)}</td>
												<td className="px-4 py-3 align-top">
													<DashboardStatusBadge status={video.status} />
												</td>
												<td className="px-4 py-3 align-top">
													{video.last_job_id ? (
														<Button asChild variant="link" size="sm" className="h-auto px-0">
															<Link href={`/jobs?job_id=${encodeURIComponent(video.last_job_id)}`}>
																{video.last_job_id}
															</Link>
														</Button>
													) : (
														"-"
													)}
												</td>
											</tr>
										))}
									</tbody>
								</table>
							</div>
						) : null}
					</CardContent>
				</Card>
			</section>
		</div>
	);
}
