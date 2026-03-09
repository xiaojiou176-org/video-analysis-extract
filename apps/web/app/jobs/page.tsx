import type { Metadata } from "next";
import Link from "next/link";

import { getFlashMessage, toErrorCode } from "@/app/flash-message";
import { toDisplayStatus } from "@/app/status";
import { FormInputField } from "@/components/form-field";
import { StatusBadge, mapStatusCssToTone } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api/client";
import { buildArtifactAssetUrl } from "@/lib/api/url";
import { formatDateTime, formatDateTimeWithSeconds } from "@/lib/format";
import { resolveSearchParams, type SearchParamsInput } from "@/lib/search-params";

export const metadata: Metadata = { title: "任务" };

type JobsPageProps = { searchParams?: SearchParamsInput };

function JobStatusBadge({ status }: { status: string }) {
	const statusDisplay = toDisplayStatus(status);
	return <StatusBadge label={statusDisplay.label} tone={mapStatusCssToTone(statusDisplay.css)} />;
}

export default async function JobsPage({ searchParams }: JobsPageProps) {
	const { job_id: jobId } = await resolveSearchParams(searchParams, ["job_id"] as const);
	const retryHref = jobId ? `/jobs?job_id=${encodeURIComponent(jobId)}` : "/jobs";

	let error: string | null = null;
	let job: Awaited<ReturnType<typeof apiClient.getJob>> | null = null;
	if (jobId) {
		try {
			job = await apiClient.getJob(jobId);
		} catch (err) {
			error = getFlashMessage(toErrorCode(err));
		}
	}
	const jobStatus = job ? toDisplayStatus(job.status) : null;
	const pipelineStatus = job?.pipeline_final_status ? toDisplayStatus(job.pipeline_final_status) : null;

	return (
		<div className="folo-page-shell folo-unified-shell">
			<div className="folo-page-header">
				<p className="folo-page-kicker">Folo Pipeline</p>
				<h1 className="folo-page-title" data-route-heading>
					任务追踪
				</h1>
				<p className="folo-page-subtitle">
					按任务 ID 查询完整流水线状态、重试信息与产物索引，定位失败链路与处理耗时。
				</p>
			</div>

			<Card className="folo-surface border-border/70">
				<CardHeader>
					<h2 className="text-xl font-semibold">任务查询</h2>
					<CardDescription>
						输入任务 ID 查看步骤详情和产物。可从 <Link href="/">首页最近视频</Link> 或{" "}
						<Link href="/feed">AI 摘要页</Link> 中的任务链接直接进入。
					</CardDescription>
				</CardHeader>
				<CardContent>
					<form method="GET" className="flex flex-wrap items-end gap-3" data-auto-disable-required="true">
						<FormInputField
							id="job-id-field"
							name="job_id"
							label="任务 ID *"
							type="text"
							placeholder="9be4cbe7-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
							defaultValue={jobId}
							required
							data-field-kind="identifier"
							fieldClassName="min-w-[280px] flex-1"
						/>
						<Button type="submit" data-interaction="control">
							查询
						</Button>
					</form>
				</CardContent>
			</Card>

			{error ? (
				<Card className="folo-surface border-destructive/40 bg-destructive/5" role="alert" aria-live="assertive">
					<CardHeader className="gap-2">
						<CardTitle className="text-base">查询失败</CardTitle>
						<CardDescription>{error}</CardDescription>
					</CardHeader>
					<CardContent className="pt-0">
						<Button asChild variant="outline" size="sm">
							<Link href={retryHref}>重试当前页面</Link>
						</Button>
					</CardContent>
				</Card>
			) : null}

			{job ? (
				<>
					<p className="text-sm text-muted-foreground" role="status" aria-live="polite">
						当前任务状态：{jobStatus?.label ?? "-"}，流水线状态：{pipelineStatus?.label ?? "-"}，共{" "}
						{job.step_summary.length} 个步骤。
					</p>
					<section>
						<Card className="folo-surface border-border/70">
							<CardHeader>
								<h2 className="text-xl font-semibold">任务概览</h2>
							</CardHeader>
							<CardContent className="space-y-4">
								<dl className="grid gap-3 sm:grid-cols-2">
									<div className="space-y-1 rounded-lg border border-border/60 bg-muted/20 p-3">
										<dt className="text-xs uppercase tracking-wide text-muted-foreground">任务 ID</dt>
										<dd className="break-all text-sm font-medium">{job.id}</dd>
									</div>
									<div className="space-y-1 rounded-lg border border-border/60 bg-muted/20 p-3">
										<dt className="text-xs uppercase tracking-wide text-muted-foreground">视频 ID</dt>
										<dd className="break-all text-sm font-medium">{job.video_id}</dd>
									</div>
									<div className="space-y-1 rounded-lg border border-border/60 bg-muted/20 p-3">
										<dt className="text-xs uppercase tracking-wide text-muted-foreground">状态</dt>
										<dd>
											<JobStatusBadge status={jobStatus?.css ?? "queued"} />
										</dd>
									</div>
									<div className="space-y-1 rounded-lg border border-border/60 bg-muted/20 p-3">
										<dt className="text-xs uppercase tracking-wide text-muted-foreground">流水线最终状态</dt>
										<dd>{pipelineStatus ? <JobStatusBadge status={pipelineStatus.css} /> : "-"}</dd>
									</div>
									<div className="space-y-1 rounded-lg border border-border/60 bg-muted/20 p-3">
										<dt className="text-xs uppercase tracking-wide text-muted-foreground">创建时间</dt>
										<dd className="text-sm">{formatDateTime(job.created_at)}</dd>
									</div>
									<div className="space-y-1 rounded-lg border border-border/60 bg-muted/20 p-3">
										<dt className="text-xs uppercase tracking-wide text-muted-foreground">更新时间</dt>
										<dd className="text-sm">{formatDateTime(job.updated_at)}</dd>
									</div>
								</dl>
								<Button asChild variant="link" size="sm" className="h-auto px-0">
									<Link href={`/feed?item=${encodeURIComponent(job.id)}`}>在摘要流中查看</Link>
								</Button>
							</CardContent>
						</Card>
					</section>

					<section>
						<Card className="folo-surface border-border/70">
							<CardHeader>
								<h2 className="text-xl font-semibold">步骤摘要</h2>
							</CardHeader>
							<CardContent>
								{job.step_summary.length === 0 ? (
									<p className="text-sm text-muted-foreground">暂无步骤记录。</p>
								) : (
									<div className="table-scroll overflow-x-auto rounded-lg border border-border/70">
										<table className="min-w-[720px] w-full text-sm">
											<caption className="sr-only">任务步骤摘要表</caption>
											<thead className="bg-muted/40 text-left text-xs uppercase tracking-wide text-muted-foreground">
												<tr>
													<th scope="col" className="px-4 py-3 font-medium">
														步骤
													</th>
													<th scope="col" className="px-4 py-3 font-medium">
														状态
													</th>
													<th scope="col" className="px-4 py-3 font-medium">
														重试次数
													</th>
													<th scope="col" className="px-4 py-3 font-medium">
														开始时间
													</th>
													<th scope="col" className="px-4 py-3 font-medium">
														结束时间
													</th>
												</tr>
											</thead>
											<tbody>
												{job.step_summary.map((step, index) => (
													<tr key={`${step.name}-${index}`} className="border-t border-border/60">
														<td className="px-4 py-3">{step.name}</td>
														<td className="px-4 py-3">
															<JobStatusBadge status={step.status} />
														</td>
														<td className="px-4 py-3">{step.attempt}</td>
														<td className="px-4 py-3">{formatDateTimeWithSeconds(step.started_at)}</td>
														<td className="px-4 py-3">{formatDateTimeWithSeconds(step.finished_at)}</td>
													</tr>
												))}
											</tbody>
										</table>
									</div>
								)}
							</CardContent>
						</Card>
					</section>

					<section className="grid gap-4 lg:grid-cols-2">
						<Card className="folo-surface border-border/70">
							<CardHeader>
									<h2 className="text-xl font-semibold">降级记录</h2>
							</CardHeader>
							<CardContent>
								{job.degradations.length === 0 ? (
									<p className="text-sm text-muted-foreground">无降级记录。</p>
								) : (
									<ul className="space-y-2 text-sm">
										{job.degradations.map((item, index) => {
											const degradationStatus =
												typeof item.status === "string" ? toDisplayStatus(item.status).label : "n/a";
											return (
												<li key={`${item.step ?? "unknown"}-${index}`} className="leading-6">
													<strong>{item.step ?? "unknown"}</strong>: {item.reason ?? degradationStatus}
												</li>
											);
										})}
									</ul>
								)}
							</CardContent>
						</Card>

						<Card className="folo-surface border-border/70">
							<CardHeader>
									<h2 className="text-xl font-semibold">产物索引</h2>
							</CardHeader>
							<CardContent>
								{Object.keys(job.artifacts_index).length === 0 ? (
									<p className="text-sm text-muted-foreground">暂无产物。</p>
								) : (
									<ul className="space-y-2 text-sm">
										{Object.entries(job.artifacts_index).map(([key, value]) => (
											<li key={key}>
												<strong>{key}</strong>: {" "}
												<a
													href={buildArtifactAssetUrl(job.id, value)}
													target="_blank"
													rel="noreferrer"
													className="text-primary underline-offset-4 hover:underline"
												>
													<code>{value}</code>（在新标签页打开）
												</a>
											</li>
										))}
									</ul>
								)}
							</CardContent>
						</Card>
					</section>
				</>
			) : null}
		</div>
	);
}
