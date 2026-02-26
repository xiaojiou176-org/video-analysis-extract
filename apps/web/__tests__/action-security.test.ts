import { beforeEach, describe, expect, it, vi } from "vitest";

const { cookiesMock } = vi.hoisted(() => ({
	cookiesMock: vi.fn(),
}));

vi.mock("next/headers", () => ({
	cookies: cookiesMock,
}));

import {
	assertActionSession,
	getActionSessionTokenForForm,
	isNextRedirectError,
	schemas,
} from "@/app/action-security";

function buildEmptyCookieStore() {
	return {
		get: vi.fn(() => undefined),
	};
}

describe("action security session token", () => {
	beforeEach(() => {
		process.env.WEB_ACTION_SESSION_TOKEN = "server-secret-value";
		cookiesMock.mockResolvedValue(buildEmptyCookieStore());
	});

	it("issues signed form token instead of exposing raw secret", () => {
		const token = getActionSessionTokenForForm();

		expect(token).toContain(".");
		expect(token).not.toBe(process.env.WEB_ACTION_SESSION_TOKEN);
	});

	it("accepts valid signed form token", async () => {
		const formData = new FormData();
		formData.set("session_token", getActionSessionTokenForForm());

		await expect(assertActionSession(formData)).resolves.toBeUndefined();
	});

	it("rejects malformed form token", async () => {
		const formData = new FormData();
		formData.set("session_token", "plain-text-secret");

		await expect(assertActionSession(formData)).rejects.toThrow("ERR_AUTH_REQUIRED");
	});
});

describe("isNextRedirectError", () => {
	it("matches Next redirect digest", () => {
		const err = Object.assign(new Error("redirect"), { digest: "NEXT_REDIRECT;/" });
		expect(isNextRedirectError(err)).toBe(true);
	});

	it("ignores non redirect errors", () => {
		expect(isNextRedirectError(new Error("boom"))).toBe(false);
	});
});

describe("action security URL schema hardening", () => {
	it("rejects javascript protocol for processVideo payload", () => {
		expect(() =>
			schemas.processVideo.parse({
				platform: "youtube",
				url: "javascript:alert(1)",
				mode: "full",
				force: false,
			}),
		).toThrow();
	});

	it("rejects javascript protocol for subscription source_url", () => {
		expect(() =>
			schemas.subscriptionUpsert.parse({
				platform: "youtube",
				source_type: "url",
				source_value: "https://example.com/source",
				adapter_type: "rss_generic",
				source_url: "javascript:alert(1)",
				rsshub_route: null,
				category: "misc",
				tags: [],
				priority: 50,
				enabled: true,
			}),
		).toThrow();
	});
});
