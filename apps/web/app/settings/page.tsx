import type { Metadata } from "next";
import Link from "next/link";

import { getActionSessionTokenForForm } from "@/app/action-security";
import { getFlashMessage } from "@/app/flash-message";
import { sendTestNotificationAction, updateNotificationConfigAction } from "@/app/settings/actions";
import {
	FormCheckboxField,
	FormField,
	FormFieldHint,
	FormFieldLabel,
	FormInputField,
} from "@/components/form-field";
import { SubmitButton } from "@/components/submit-button";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { apiClient } from "@/lib/api/client";
import { formatDateTime } from "@/lib/format";
import { resolveSearchParams, type SearchParamsInput } from "@/lib/search-params";

export const metadata: Metadata = { title: "设置" };

type SettingsPageProps = {
	searchParams?: SearchParamsInput;
};

export default async function SettingsPage({ searchParams }: SettingsPageProps) {
	const { status, code } = await resolveSearchParams(searchParams, ["status", "code"] as const);
	const sessionToken = getActionSessionTokenForForm();
	const configResult = await apiClient
		.getNotificationConfig()
		.then((config) => ({ config, error: null as string | null }))
		.catch((err) => ({
			config: null,
			error: err instanceof Error ? err.message : "ERR_REQUEST_FAILED",
		}));
	const { config, error: loadError } = configResult;

	const alert =
		status && code ? (
			<p
				className={status === "error" ? "alert alert-enter error" : "alert alert-enter success"}
				role={status === "error" ? "alert" : "status"}
				aria-live={status === "error" ? "assertive" : "polite"}
			>
				{getFlashMessage(code)}
			</p>
		) : null;

	return (
		<div className="folo-page-shell folo-unified-shell">
			<div className="folo-page-header">
				<p className="folo-page-kicker">Folo Settings</p>
				<h1 className="folo-page-title" data-route-heading>
					通知设置
				</h1>
				<p className="folo-page-subtitle">
					管理摘要通知、失败告警与测试邮件发送策略，保障运营触达链路稳定可控。
				</p>
			</div>

			{alert}
			{loadError ? (
				<Card className="folo-surface border-destructive/40 bg-destructive/5" role="alert" aria-live="assertive">
					<CardHeader className="gap-2">
						<CardTitle className="text-base">加载失败</CardTitle>
						<CardDescription>
							{getFlashMessage(loadError.startsWith("ERR_") ? loadError : "ERR_REQUEST_FAILED")}
						</CardDescription>
					</CardHeader>
					<CardContent className="pt-0">
						<Button asChild variant="outline" size="sm">
							<Link href="/settings">重试当前页面</Link>
						</Button>
					</CardContent>
				</Card>
			) : null}

			<Card className="folo-surface border-border/70">
				<CardHeader className="gap-2">
						<h2 className="text-xl font-semibold">通知配置</h2>
					{config ? (
						<CardDescription>
							创建时间：{formatDateTime(config.created_at)} | 更新时间：{formatDateTime(config.updated_at)}
						</CardDescription>
					) : null}
				</CardHeader>
				<CardContent>
					<form action={updateNotificationConfigAction} className="grid gap-4">
						<input type="hidden" name="session_token" value={sessionToken} suppressHydrationWarning />
						<FormCheckboxField name="enabled" label="启用通知" defaultChecked={config?.enabled ?? true} />
						<FormInputField
							id="to_email"
							name="to_email"
							label="收件人邮箱"
							type="email"
							defaultValue={config?.to_email ?? ""}
							placeholder="ops@example.com"
						/>
						<FormCheckboxField
							name="daily_digest_enabled"
							label="启用每日摘要"
							defaultChecked={config?.daily_digest_enabled ?? false}
						/>
						<FormInputField
							id="daily_digest_hour_utc"
							name="daily_digest_hour_utc"
							label="每日摘要发送时间（UTC 小时）"
							type="number"
							min={0}
							max={23}
							defaultValue={config?.daily_digest_hour_utc ?? ""}
							data-disabled-unless-checked="daily_digest_enabled"
							data-field-kind="identifier"
							aria-describedby="daily-digest-hour-utc-help"
							disabled={!config?.daily_digest_enabled}
						/>
						<FormFieldHint id="daily-digest-hour-utc-help">
							本地时间预览：本字段使用 UTC 小时。换算公式为「本地时间 = UTC 时间 + 时区偏移」。
							例如 UTC+8 用户可将本地目标小时减 8 后填写（如本地 09:00 → UTC 01:00）。
						</FormFieldHint>
						<FormCheckboxField
							name="failure_alert_enabled"
							label="启用失败告警"
							defaultChecked={config?.failure_alert_enabled ?? true}
						/>
						<SubmitButton pendingLabel="保存中…" statusText="正在保存通知配置">
							保存配置
						</SubmitButton>
					</form>
				</CardContent>
			</Card>

			<Card className="folo-surface border-border/70">
				<CardHeader className="gap-2">
						<h2 className="text-xl font-semibold">发送测试通知</h2>
					<CardDescription>
						当前默认收件人：{config?.to_email ? config.to_email : "未设置，请先在上方通知配置中填写收件人邮箱。"}
					</CardDescription>
				</CardHeader>
				<CardContent>
					<form action={sendTestNotificationAction} className="grid gap-4">
						<input type="hidden" name="session_token" value={sessionToken} suppressHydrationWarning />
						<FormInputField
							id="test_to_email"
							name="to_email"
							label="覆盖收件人（可选）"
							type="email"
							placeholder="留空则使用已配置的收件人"
						/>
						<FormInputField
							id="test_subject"
							name="subject"
							label="主题（可选）"
							type="text"
							placeholder="AI 信息中枢测试通知"
						/>
						<FormField>
							<FormFieldLabel htmlFor="test_body">正文（可选）</FormFieldLabel>
							<Textarea id="test_body" name="body" rows={4} placeholder="这是来自 AI 信息中枢的测试通知邮件。" />
						</FormField>
						<SubmitButton pendingLabel="发送中…" statusText="正在发送测试通知">
							发送测试邮件
						</SubmitButton>
					</form>
				</CardContent>
			</Card>
		</div>
	);
}
