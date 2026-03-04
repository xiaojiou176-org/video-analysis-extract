import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import RootLayout from "@/app/layout";

vi.mock("next/link", () => ({
	default: ({ href, children, ...rest }: { href: string; children: React.ReactNode }) => (
		<a href={href} {...rest}>
			{children}
		</a>
	),
}));

vi.mock("@/components/nav", () => ({
	AppNav: () => <nav data-testid="app-nav-stub">nav</nav>,
}));

vi.mock("@/components/form-validation-controller", () => ({
	FormValidationController: () => <div data-testid="form-validation-controller-stub" />,
}));

describe("RootLayout", () => {
	it("shows healthy api state chip", async () => {
		const fetchMock = vi.fn().mockResolvedValue({ ok: true });
		vi.stubGlobal("fetch", fetchMock);

		const html = renderToStaticMarkup(await RootLayout({ children: <div>content</div> }));

		expect(html).toContain("API 状态：正常");
		expect(html).toContain('href="http://127.0.0.1:8000/healthz"');
		expect(fetchMock).toHaveBeenCalledWith(
			"http://127.0.0.1:8000/healthz",
			expect.objectContaining({
				cache: "force-cache",
				next: { revalidate: 30 },
			}),
		);
	});

	it("shows unhealthy api state chip", async () => {
		vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false }));

		const html = renderToStaticMarkup(await RootLayout({ children: <div>content</div> }));

		expect(html).toContain("API 状态：异常");
	});

	it("shows timeout/unknown api state chip when fetch throws", async () => {
		vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));

		const html = renderToStaticMarkup(await RootLayout({ children: <div>content</div> }));

		expect(html).toContain("api-health-dot-timeout_or_unknown");
		expect(html).toContain("API 状态：超时/未知");
		expect(html).toContain('aria-live="polite"');
		expect(html).toContain("跳至主内容");
		expect(html).toContain('id="main-content"');
		expect(html).toContain('tabindex="-1"');
	});
});
