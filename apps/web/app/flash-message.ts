export type FlashStatus = "success" | "error";

const FLASH_MESSAGES: Record<string, string> = {
	POLL_INGEST_OK: "已触发采集任务。",
	PROCESS_VIDEO_OK: "已创建处理任务。",
	SUBSCRIPTION_CREATED: "订阅已创建。",
	SUBSCRIPTION_UPDATED: "订阅已更新。",
	SUBSCRIPTION_DELETED: "订阅已删除。",
	NOTIFICATION_CONFIG_SAVED: "通知配置已保存。",
	NOTIFICATION_TEST_SENT: "测试通知已发送。",
	ERR_AUTH_REQUIRED: "会话已失效，请刷新页面后重试。",
	ERR_INVALID_INPUT: "输入参数不合法，请检查后重试。",
	ERR_INVALID_URL: "URL 格式不合法，请输入以 http:// 或 https:// 开头的地址。",
	ERR_INVALID_EMAIL: "邮箱格式不合法，请输入有效的邮箱地址。",
	ERR_INVALID_IDENTIFIER: "标识符格式不合法。",
	ERR_NOTIFICATION_EMAIL_REQUIRED: "启用通知时必须填写收件邮箱。",
	ERR_DAILY_DIGEST_HOUR_REQUIRED: "启用每日摘要时必须设置 UTC 小时。",
	ERR_SENSITIVE_QUERY_KEY: "请求参数包含敏感字段，已被客户端阻止。",
	ERR_REQUEST_FAILED: "请求失败，请稍后重试。",
};

export function getFlashMessage(code: string): string {
	const normalized = code.trim().toUpperCase().split(":")[0] ?? "";
	if (!normalized) {
		return FLASH_MESSAGES.ERR_REQUEST_FAILED;
	}
	return FLASH_MESSAGES[normalized] ?? FLASH_MESSAGES.ERR_REQUEST_FAILED;
}

export function toFlashQuery(status: FlashStatus, code: string): string {
	const query = new URLSearchParams({
		status,
		code: code.trim().toUpperCase() || "ERR_REQUEST_FAILED",
	});
	return query.toString();
}

export function toErrorCode(error: unknown): string {
	if (error instanceof Error) {
		const normalized = error.message.trim().toUpperCase().split(":")[0] ?? "";
		if (normalized.startsWith("ERR_")) {
			return normalized;
		}
	}
	return "ERR_REQUEST_FAILED";
}
