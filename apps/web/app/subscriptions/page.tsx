import type { Metadata } from "next";
import Link from "next/link";

import { getActionSessionTokenForForm } from "@/app/action-security";
import { getFlashMessage } from "@/app/flash-message";
import { upsertSubscriptionAction } from "@/app/subscriptions/actions";
import {
	FormCheckboxField,
	FormInputField,
	FormSelectField,
} from "@/components/form-field";
import { SubmitButton } from "@/components/submit-button";
import { SubscriptionBatchPanel } from "@/components/subscription-batch-panel";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api/client";
import { resolveSearchParams, type SearchParamsInput } from "@/lib/search-params";

export const metadata: Metadata = { title: "订阅管理" };

type SubscriptionsPageProps = {
	searchParams?: SearchParamsInput;
};

const PLATFORM_OPTIONS = [
	{ value: "youtube", label: "YouTube" },
	{ value: "bilibili", label: "Bilibili" },
];

const SOURCE_TYPE_OPTIONS = [
	{ value: "url", label: "来源链接（URL）" },
	{ value: "youtube_channel_id", label: "YouTube 频道 ID" },
	{ value: "bilibili_uid", label: "Bilibili 用户 UID" },
];

const ADAPTER_TYPE_OPTIONS = [
	{ value: "rsshub_route", label: "RSSHub 路由" },
	{ value: "rss_generic", label: "通用 RSS" },
];

const CATEGORY_OPTIONS = [
	{ value: "misc", label: "其他" },
	{ value: "tech", label: "科技" },
	{ value: "creator", label: "创作者" },
	{ value: "macro", label: "宏观" },
	{ value: "ops", label: "运维" },
];

function renderAlert(status: string, code: string) {
	if (!status || !code) {
		return null;
	}
	const isError = status === "error";
	const className = status === "error" ? "alert alert-enter error" : "alert alert-enter success";
	return (
		<p className={className} role={isError ? "alert" : "status"} aria-live={isError ? "assertive" : "polite"}>
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
		<div className="folo-page-shell folo-unified-shell">
			<div className="folo-page-header">
				<p className="folo-page-kicker">Folo Sources</p>
				<h1 className="folo-page-title" data-route-heading>
					订阅管理
				</h1>
				<p className="folo-page-subtitle">
					维护来源配置、分类与优先级，确保后续采集与摘要链路拥有稳定输入。
				</p>
			</div>

			{renderAlert(status, code)}
			{subscriptionsResult.errorCode ? (
				<Card className="folo-surface border-destructive/40 bg-destructive/5" role="alert" aria-live="assertive">
					<CardHeader className="gap-2">
						<CardTitle className="text-base">加载失败</CardTitle>
						<CardDescription>{getFlashMessage(subscriptionsResult.errorCode)}</CardDescription>
					</CardHeader>
					<CardContent className="pt-0">
						<Button asChild variant="outline" size="sm">
							<Link href="/subscriptions">重试当前页面</Link>
						</Button>
					</CardContent>
				</Card>
			) : null}

			<section>
				<Card className="folo-surface border-border/70">
					<CardHeader className="gap-2">
						<h2 className="text-xl font-semibold">创建或更新订阅</h2>
						<CardDescription>先选择“来源类型”，再填写对应来源值；仅在使用通用 RSS 时填写“来源 URL”。</CardDescription>
					</CardHeader>
					<CardContent>
						<form action={upsertSubscriptionAction} className="grid gap-5 md:grid-cols-2" data-auto-disable-required="true">
							<input type="hidden" name="session_token" value={sessionToken} suppressHydrationWarning />
							<FormSelectField id="platform" name="platform" label="平台" defaultValue="youtube" options={PLATFORM_OPTIONS} />
							<FormSelectField
								id="source_type"
								name="source_type"
								label="来源类型"
								defaultValue="url"
								options={SOURCE_TYPE_OPTIONS}
							/>
							<FormInputField id="source_value" name="source_value" label="来源值" required placeholder="频道 ID / UID / URL" />
							<FormSelectField
								id="adapter_type"
								name="adapter_type"
								label="适配器类型"
								defaultValue="rsshub_route"
								options={ADAPTER_TYPE_OPTIONS}
							/>
							<FormInputField
								id="source_url"
								name="source_url"
								label="来源 URL（rss_generic 时使用）"
								type="url"
								placeholder="https://example.com/feed.xml"
							/>
							<FormInputField
								id="rsshub_route"
								name="rsshub_route"
								label="RSSHub 路由（可选）"
								placeholder="/youtube/channel/UCxxxx"
							/>
							<FormSelectField
								id="category"
								name="category"
								label="分类"
								defaultValue="misc"
								options={CATEGORY_OPTIONS}
							/>
							<FormInputField id="tags" name="tags" label="标签（逗号分隔，可选）" placeholder="ai,weekly,high-priority" />
							<FormInputField
								id="priority"
								name="priority"
								label="优先级 (0-100)"
								type="number"
								min={0}
								max={100}
								defaultValue={50}
							/>
							<FormCheckboxField name="enabled" label="启用" defaultChecked fieldClassName="md:col-span-2" />
							<div className="md:col-span-2">
								<SubmitButton pendingLabel="保存中…" statusText="正在保存订阅配置">
									保存订阅
								</SubmitButton>
							</div>
						</form>
					</CardContent>
				</Card>
			</section>

			<section>
				<Card className="folo-surface border-border/70">
					<CardHeader className="gap-2">
						<h2 className="text-xl font-semibold">当前订阅列表</h2>
						<CardDescription>
							<p className="text-sm text-muted-foreground" role="status" aria-live="polite">
								已加载 {subscriptions.length} 条订阅。
							</p>
							<p className="text-sm text-muted-foreground">勾选多行可批量更新分类，底部将出现操作栏。</p>
						</CardDescription>
					</CardHeader>
					<CardContent>
							<SubscriptionBatchPanel subscriptions={subscriptions} sessionToken={sessionToken} />
					</CardContent>
				</Card>
			</section>
		</div>
	);
}
