import type { Metadata } from "next";

import { getActionSessionTokenForForm } from "@/app/action-security";
import { getFlashMessage } from "@/app/flash-message";
import { sendTestNotificationAction, updateNotificationConfigAction } from "@/app/settings/actions";

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
				className={status === "error" ? "alert error" : "alert success"}
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
				<p className="alert error" role="alert" aria-live="assertive">
					{getFlashMessage(loadError.startsWith("ERR_") ? loadError : "ERR_REQUEST_FAILED")}
				</p>
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
							disabled={!config?.daily_digest_enabled}
						/>
					</label>

					<label className="inline">
						<input
							name="failure_alert_enabled"
							type="checkbox"
							defaultChecked={config?.failure_alert_enabled ?? true}
						/>
						启用失败告警
					</label>

					<button type="submit" className="primary">
						保存配置
					</button>
				</form>
			</section>

			<section className="card stack">
				<h2>发送测试通知</h2>
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

					<button type="submit" className="primary">
						发送测试邮件
					</button>
				</form>
			</section>
		</div>
	);
}
