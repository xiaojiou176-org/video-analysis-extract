import type { Metadata } from "next";
import Link from "next/link";

import { getActionSessionTokenForForm } from "@/app/action-security";
import { getFlashMessage } from "@/app/flash-message";
import { upsertSubscriptionAction } from "@/app/subscriptions/actions";
import { SubmitButton } from "@/components/submit-button";

export const metadata: Metadata = { title: "订阅管理" };

import { SubscriptionBatchPanel } from "@/components/subscription-batch-panel";
import { apiClient } from "@/lib/api/client";
import { resolveSearchParams, type SearchParamsInput } from "@/lib/search-params";

type SubscriptionsPageProps = {
	searchParams?: SearchParamsInput;
};

function renderAlert(status: string, code: string) {
	if (!status || !code) {
		return null;
	}
	const isError = status === "error";
	const className = status === "error" ? "alert alert-enter error" : "alert alert-enter success";
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

export default async function SubscriptionsPage({ searchParams }: SubscriptionsPageProps) {
	const { status, code } = await resolveSearchParams(searchParams, ["status", "code"] as const);
	const sessionToken = getActionSessionTokenForForm();
	const subscriptionsResult = await apiClient
		.listSubscriptions()
		.then((data) => ({ data, errorCode: null as string | null }))
		.catch(() => ({
			data: [] as Awaited<ReturnType<typeof apiClient.listSubscriptions>>,
			errorCode: "ERR_REQUEST_FAILED",
		}));
	const subscriptions = subscriptionsResult.data;

	return (
		<div className="stack">
			{renderAlert(status, code)}
			{subscriptionsResult.errorCode ? (
				<>
					<p className="alert alert-enter error" role="alert" aria-live="assertive">
						{getFlashMessage(subscriptionsResult.errorCode)}
					</p>
					<Link href="/subscriptions" className="btn-link" data-interaction="link-muted">
						重试当前页面
					</Link>
				</>
			) : null}

			<section className="card stack">
				<h2>创建或更新订阅</h2>
				<p className="small">
					先选择“来源类型”，再填写对应来源值；仅在使用通用 RSS 时填写“来源 URL”。
				</p>
				<form action={upsertSubscriptionAction} className="grid grid-cols-2" data-auto-disable-required="true">
					<input type="hidden" name="session_token" value={sessionToken} />
					<label>
						平台
						<select name="platform" defaultValue="youtube">
							<option value="youtube">YouTube</option>
							<option value="bilibili">Bilibili</option>
						</select>
					</label>

					<label>
						来源类型
						<select name="source_type" defaultValue="url">
							<option value="url">来源链接（URL）</option>
							<option value="youtube_channel_id">YouTube 频道 ID</option>
							<option value="bilibili_uid">Bilibili 用户 UID</option>
						</select>
					</label>

					<label>
						来源值
						<input name="source_value" required placeholder="频道 ID / UID / URL" />
					</label>

					<label>
						适配器类型
						<select name="adapter_type" defaultValue="rsshub_route">
							<option value="rsshub_route">RSSHub 路由</option>
							<option value="rss_generic">通用 RSS</option>
						</select>
					</label>

					<label>
						来源 URL（rss_generic 时使用）
						<input name="source_url" type="url" placeholder="https://example.com/feed.xml" />
					</label>

					<label>
						RSSHub 路由（可选）
						<input name="rsshub_route" placeholder="/youtube/channel/UCxxxx" />
					</label>

					<label>
						分类
						<select name="category" defaultValue="misc">
							<option value="misc">其他</option>
							<option value="tech">科技</option>
							<option value="creator">创作者</option>
							<option value="macro">宏观</option>
							<option value="ops">运维</option>
						</select>
					</label>

					<label>
						标签（逗号分隔，可选）
						<input name="tags" placeholder="ai,weekly,high-priority" />
					</label>
					<label>
						优先级 (0-100)
						<input name="priority" type="number" min={0} max={100} defaultValue={50} />
					</label>

					<label className="inline">
						<input name="enabled" type="checkbox" defaultChecked />
						启用
					</label>

					<div className="inline">
						<SubmitButton pendingLabel="保存中…" statusText="正在保存订阅配置">
							保存订阅
						</SubmitButton>
					</div>
				</form>
			</section>

			<section className="card stack">
				<h2>当前订阅列表</h2>
				<p className="small" role="status" aria-live="polite">
					已加载 {subscriptions.length} 条订阅。
				</p>
				<p className="small">勾选多行可批量更新分类，底部将出现操作栏。</p>
				<SubscriptionBatchPanel subscriptions={subscriptions} />
			</section>
		</div>
	);
}
