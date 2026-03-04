import { describe, expect, it } from "vitest";

import { getFlashMessage, toErrorCode } from "@/app/flash-message";

describe("flash-message mapping", () => {
	it("maps unknown code to generic message", () => {
		expect(getFlashMessage("UNKNOWN")).toBe("请求失败，请稍后重试。");
	});

	it("maps field-level codes to actionable messages", () => {
		expect(getFlashMessage("ERR_INVALID_URL")).toBe(
			"URL 格式不合法，请输入以 http:// 或 https:// 开头的地址。",
		);
		expect(getFlashMessage("ERR_INVALID_EMAIL")).toBe("邮箱格式不合法，请输入有效的邮箱地址。");
		expect(getFlashMessage("ERR_INVALID_IDENTIFIER")).toBe("标识符格式不合法。");
		expect(getFlashMessage("ERR_NOTIFICATION_EMAIL_REQUIRED")).toBe(
			"启用通知时必须填写收件邮箱。",
		);
		expect(getFlashMessage("ERR_DAILY_DIGEST_HOUR_REQUIRED")).toBe(
			"启用每日摘要时必须设置 UTC 小时。",
		);
	});

	it("extracts only internal error code from Error", () => {
		expect(toErrorCode(new Error("ERR_INVALID_INPUT"))).toBe("ERR_INVALID_INPUT");
		expect(toErrorCode(new Error("https://example.com failed"))).toBe("ERR_REQUEST_FAILED");
	});
});
