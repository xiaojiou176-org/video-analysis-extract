import { describe, expect, it } from "vitest";

import { getFlashMessage, toErrorCode } from "@/app/flash-message";

describe("flash-message mapping", () => {
	it("maps unknown code to generic message", () => {
		expect(getFlashMessage("UNKNOWN")).toBe("请求失败，请稍后重试。");
	});

	it("extracts only internal error code from Error", () => {
		expect(toErrorCode(new Error("ERR_INVALID_INPUT"))).toBe("ERR_INVALID_INPUT");
		expect(toErrorCode(new Error("https://example.com failed"))).toBe("ERR_REQUEST_FAILED");
	});
});
