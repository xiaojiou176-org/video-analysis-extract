import type { Metadata } from "next";
import Link from "next/link";

import { getActionSessionTokenForForm } from "@/app/action-security";
import { getFlashMessage } from "@/app/flash-message";
import { sendTestNotificationAction, updateNotificationConfigAction } from "@/app/settings/actions";
import { SubmitButton } from "@/components/submit-button";

export const metadata: Metadata = { title: "设置" };

import { apiClient } from "@/lib/api/client";
import { formatDateTime } from "@/lib/format";
import { resolveSearchParams, type SearchParamsInput } from "@/lib/search-params";

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
		<div className="stack">
			{alert}
			{loadError ? (
				<>
					<p className="alert alert-enter error" role="alert" aria-live="assertive">
						{getFlashMessage(loadError.startsWith("ERR_") ? loadError : "ERR_REQUEST_FAILED")}
					</p>
					<Link href="/settings" className="btn-link" data-interaction="link-muted">
						重试当前页面
					</Link>
				</>
			) : null}

			<section className="card stack">
				<h2>通知配置</h2>
				{config ? (
					<p className="small">
						创建时间：{formatDateTime(config.created_at)} | 更新时间：
						{formatDateTime(config.updated_at)}
					</p>
				) : null}
				<form action={updateNotificationConfigAction} className="stack">
					<input type="hidden" name="session_token" value={sessionToken} />
					<label className="inline">
						<input name="enabled" type="checkbox" defaultChecked={config?.enabled ?? true} />
						启用通知
					</label>

					<label>
						收件人邮箱
						<input
							name="to_email"
							type="email"
							defaultValue={config?.to_email ?? ""}
							placeholder="ops@example.com"
						/>
					</label>

					<label className="inline">
						<input
							name="daily_digest_enabled"
							type="checkbox"
							defaultChecked={config?.daily_digest_enabled ?? false}
						/>
						启用每日摘要
					</label>

					<label>
						每日摘要发送时间（UTC 小时）
						<input
							name="daily_digest_hour_utc"
							type="number"
							min={0}
							max={23}
							defaultValue={config?.daily_digest_hour_utc ?? ""}
							data-disabled-unless-checked="daily_digest_enabled"
							data-field-kind="identifier"
							aria-describedby="daily-digest-hour-utc-help"
							disabled={!config?.daily_digest_enabled}
						/>
					</label>
					<p id="daily-digest-hour-utc-help" className="small">
						本地时间预览：本字段使用 UTC 小时。换算公式为「本地时间 = UTC 时间 + 时区偏移」。
						例如 UTC+8 用户可将本地目标小时减 8 后填写（如本地 09:00 → UTC 01:00）。
					</p>

					<label className="inline">
						<input
							name="failure_alert_enabled"
							type="checkbox"
							defaultChecked={config?.failure_alert_enabled ?? true}
						/>
						启用失败告警
					</label>

					<SubmitButton pendingLabel="保存中…" statusText="正在保存通知配置">
						保存配置
					</SubmitButton>
				</form>
			</section>

			<section className="card stack">
				<h2>发送测试通知</h2>
				<p className="small">
					当前默认收件人：{config?.to_email ? config.to_email : "未设置，请先在上方通知配置中填写收件人邮箱。"}
				</p>
				<form action={sendTestNotificationAction} className="stack">
					<input type="hidden" name="session_token" value={sessionToken} />
					<label>
						覆盖收件人（可选）
						<input name="to_email" type="email" placeholder="留空则使用已配置的收件人" />
					</label>

					<label>
						主题（可选）
						<input name="subject" type="text" placeholder="AI 信息中枢测试通知" />
					</label>

					<label>
						正文（可选）
						<textarea name="body" rows={4} placeholder="这是来自 AI 信息中枢的测试通知邮件。" />
					</label>

					<SubmitButton pendingLabel="发送中…" statusText="正在发送测试通知">
						发送测试邮件
					</SubmitButton>
				</form>
			</section>
		</div>
	);
}
