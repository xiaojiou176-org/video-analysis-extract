import type { Metadata } from "next";
import Link from "next/link";

import { getFlashMessage, toErrorCode } from "@/app/flash-message";
import { toDisplayStatus } from "@/app/status";

export const metadata: Metadata = { title: "任务" };

import { apiClient } from "@/lib/api/client";
import { buildArtifactAssetUrl } from "@/lib/api/url";
import { formatDateTime, formatDateTimeWithSeconds } from "@/lib/format";
import { resolveSearchParams, type SearchParamsInput } from "@/lib/search-params";

type JobsPageProps = { searchParams?: SearchParamsInput };

export default async function JobsPage({ searchParams }: JobsPageProps) {
	const { job_id: jobId } = await resolveSearchParams(searchParams, ["job_id"] as const);

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
	const pipelineStatus = job?.pipeline_final_status
		? toDisplayStatus(job.pipeline_final_status)
		: null;

	return (
		<div className="stack">
			<section className="card stack">
				<h2>任务查询</h2>
				<p className="small">
					输入任务 ID 查看步骤详情和产物。可从 <Link href="/">首页最近视频</Link> 或{" "}
					<Link href="/feed">AI 摘要页</Link> 中的任务链接直接进入。
				</p>
				<form method="GET" className="inline" data-auto-disable-required="true">
					<label className="wide-field">
						任务 ID *
						<input
							name="job_id"
							type="text"
							placeholder="9be4cbe7-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
							defaultValue={jobId}
							required
							data-field-kind="identifier"
						/>
					</label>
					<button type="submit" className="primary">
						查询
					</button>
				</form>
			</section>

			{error ? (
				<p className="alert error" role="alert" aria-live="assertive">
					{error}
				</p>
			) : null}

			{job ? (
				<>
					<section className="card stack">
						<h2>任务概览</h2>
						<div className="grid grid-cols-2">
							<div>
								<div className="small">任务 ID</div>
								<div>{job.id}</div>
							</div>
							<div>
								<div className="small">视频 ID</div>
								<div>{job.video_id}</div>
							</div>
							<div>
								<div className="small">状态</div>
								<span className={`status-chip status-${jobStatus?.css ?? "queued"}`}>
									{jobStatus?.label ?? "-"}
								</span>
							</div>
							<div>
								<div className="small">流水线最终状态</div>
								{pipelineStatus ? (
									<span className={`status-chip status-${pipelineStatus.css}`}>
										{pipelineStatus.label}
									</span>
								) : (
									<div>-</div>
								)}
							</div>
							<div>
								<div className="small">创建时间</div>
								<div>{formatDateTime(job.created_at)}</div>
							</div>
							<div>
								<div className="small">更新时间</div>
								<div>{formatDateTime(job.updated_at)}</div>
							</div>
						</div>
						<div className="inline">
							<Link href={`/artifacts?job_id=${encodeURIComponent(job.id)}`}>查看产物页</Link>
						</div>
					</section>

					<section className="card stack">
						<h2>步骤摘要</h2>
						{job.step_summary.length === 0 ? (
							<p className="small">暂无步骤记录。</p>
						) : (
							<div className="table-scroll">
								<table>
									<caption className="sr-only">任务步骤摘要表</caption>
									<thead>
										<tr>
											<th scope="col">步骤</th>
											<th scope="col">状态</th>
											<th scope="col">重试次数</th>
											<th scope="col">开始时间</th>
											<th scope="col">结束时间</th>
										</tr>
									</thead>
									<tbody>
										{job.step_summary.map((step, index) => {
											const stepStatus = toDisplayStatus(step.status);
											return (
												<tr key={`${step.name}-${index}`}>
													<td>{step.name}</td>
													<td>
														<span className={`status-chip status-${stepStatus.css}`}>
															{stepStatus.label}
														</span>
													</td>
													<td>{step.attempt}</td>
													<td>{formatDateTimeWithSeconds(step.started_at)}</td>
													<td>{formatDateTimeWithSeconds(step.finished_at)}</td>
												</tr>
											);
										})}
									</tbody>
								</table>
							</div>
						)}
					</section>

					<section className="grid grid-cols-2">
						<div className="card stack">
							<h3>降级记录</h3>
							{job.degradations.length === 0 ? (
								<p className="small">无降级记录。</p>
							) : (
								<ul>
									{job.degradations.map((item, index) => {
										const degradationStatus =
											typeof item.status === "string" ? toDisplayStatus(item.status).label : "n/a";
										return (
											<li key={`${item.step ?? "unknown"}-${index}`}>
												<strong>{item.step ?? "unknown"}</strong>:{" "}
												{item.reason ?? degradationStatus}
											</li>
										);
									})}
								</ul>
							)}
						</div>

						<div className="card stack">
							<h3>产物索引</h3>
							{Object.keys(job.artifacts_index).length === 0 ? (
								<p className="small">暂无产物。</p>
							) : (
								<ul>
									{Object.entries(job.artifacts_index).map(([key, value]) => (
										<li key={key}>
											<strong>{key}</strong>:{" "}
											<a
												href={buildArtifactAssetUrl(job.id, value)}
												target="_blank"
												rel="noreferrer"
											>
												<code>{value}</code>（在新标签页打开）
											</a>
										</li>
									))}
								</ul>
							)}
						</div>
					</section>
				</>
			) : null}
		</div>
	);
}
