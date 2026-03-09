import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { usePathnameMock, useSearchParamsMock } = vi.hoisted(() => ({
	usePathnameMock: vi.fn(),
	useSearchParamsMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
	usePathname: usePathnameMock,
	useSearchParams: useSearchParamsMock,
}));

vi.mock("next/link", () => ({
	default: ({
		href,
		children,
		...rest
	}: React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) => (
		<a href={href} {...rest}>
			{children}
		</a>
	),
}));

vi.mock("@/components/theme-toggle", () => ({
	ThemeToggle: () => <button type="button" data-slot="button">切换主题</button>,
}));

import { Sidebar } from "@/components/sidebar";
import { Sheet, SheetContent, SheetDescription, SheetTitle, SheetTrigger } from "@/components/ui/sheet";

function createSearchParams(value: string): URLSearchParams {
	return new URLSearchParams(value);
}

function mockMatchMedia(matches: boolean) {
	Object.defineProperty(window, "matchMedia", {
		configurable: true,
		writable: true,
		value: vi.fn().mockImplementation(() => ({
			matches,
			media: "(max-width: 768px)",
			onchange: null,
			addEventListener: vi.fn(),
			removeEventListener: vi.fn(),
			addListener: vi.fn(),
			removeListener: vi.fn(),
			dispatchEvent: vi.fn(),
		})),
	});
}

function SidebarSheetHarness() {
	return (
		<Sheet>
			<SheetTrigger>打开导航</SheetTrigger>
			<SheetContent side="left">
				<SheetTitle>移动端导航</SheetTitle>
				<SheetDescription>用于移动端的侧边栏抽屉导航。</SheetDescription>
				<Sidebar
					subscriptions={[
						{
							id: "sub-tech-1",
							platform: "youtube",
							source_type: "url",
							source_value: "https://youtube.com/@tech",
							source_name: "Tech Daily",
							adapter_type: "rss_generic",
							source_url: "https://example.com/feed.xml",
							rsshub_route: "",
							category: "tech",
							tags: [],
							priority: 50,
							enabled: true,
							created_at: "2026-03-01T00:00:00Z",
							updated_at: "2026-03-01T00:00:00Z",
						},
					]}
					apiHealthState="healthy"
					apiHealthUrl="http://127.0.0.1:9000/healthz"
					apiHealthLabel="正常"
				/>
			</SheetContent>
		</Sheet>
	);
}

describe("Sidebar + Sheet contract", () => {
	const SIDEBAR_TIMEOUT_MS = 15_000;

	beforeEach(() => {
		vi.clearAllMocks();
		usePathnameMock.mockReturnValue("/feed");
		useSearchParamsMock.mockReturnValue(createSearchParams("category=tech&sub=sub-tech-1"));
		mockMatchMedia(false);
	});

	it(
		"renders grouped category links and health chip metadata",
		() => {
		render(
			<Sidebar
				subscriptions={[
					{
						id: "sub-tech-1",
						platform: "youtube",
						source_type: "url",
						source_value: "https://youtube.com/@tech",
						source_name: "Tech Daily",
						adapter_type: "rss_generic",
						source_url: "https://example.com/feed.xml",
						rsshub_route: "",
						category: "tech",
						tags: [],
						priority: 50,
						enabled: true,
						created_at: "2026-03-01T00:00:00Z",
						updated_at: "2026-03-01T00:00:00Z",
					},
					{
						id: "sub-disabled",
						platform: "bilibili",
						source_type: "url",
						source_value: "https://bilibili.com/disabled",
						source_name: "Disabled Source",
						adapter_type: "rss_generic",
						source_url: "https://example.com/disabled.xml",
						rsshub_route: "",
						category: "creator",
						tags: [],
						priority: 50,
						enabled: false,
						created_at: "2026-03-01T00:00:00Z",
						updated_at: "2026-03-01T00:00:00Z",
					},
				]}
				apiHealthState="healthy"
				apiHealthUrl="http://127.0.0.1:9000/healthz"
				apiHealthLabel="正常"
			/>,
		);

		expect(screen.getByRole("complementary", { name: "侧边栏导航" })).toBeInTheDocument();
		expect(screen.getByRole("link", { name: "科技" })).toHaveAttribute("aria-current", "page");
		expect(screen.getByRole("link", { name: "Tech Daily" })).toHaveAttribute("aria-current", "page");
		expect(screen.queryByRole("link", { name: "Disabled Source" })).toBeNull();
			expect(screen.getByRole("link", { name: "API 状态：正常" })).toHaveAttribute(
				"href",
				"http://127.0.0.1:9000/healthz",
			);
		expect(screen.getByRole("button", { name: "切换主题" })).toBeInTheDocument();
		expect(screen.getByRole("button", { name: "切换主题" })).toHaveAttribute("data-slot", "button");
		},
		SIDEBAR_TIMEOUT_MS,
	);

	it(
		"opens sidebar content inside sheet container",
		() => {
		render(<SidebarSheetHarness />);

		fireEvent.click(screen.getByRole("button", { name: "打开导航" }));

		expect(screen.getByRole("dialog")).toBeInTheDocument();
		expect(screen.getByRole("heading", { name: "移动端导航" })).toBeInTheDocument();
		expect(screen.getByRole("complementary", { name: "侧边栏导航" })).toBeInTheDocument();
		},
		SIDEBAR_TIMEOUT_MS,
	);

	it(
		"wires the real mobile sheet trigger in Sidebar when viewport is collapsed",
		() => {
		mockMatchMedia(true);
		render(
			<Sidebar
				subscriptions={[]}
				apiHealthState="healthy"
				apiHealthUrl="http://127.0.0.1:9000/healthz"
				apiHealthLabel="正常"
			/>,
		);

		fireEvent.click(screen.getByRole("button", { name: "展开导航面板" }));

		expect(screen.getByRole("dialog")).toBeInTheDocument();
		expect(screen.getByRole("complementary", { name: "侧边栏导航" })).toBeInTheDocument();
		},
		SIDEBAR_TIMEOUT_MS,
	);

	it(
		"falls back safely when matchMedia is unavailable and supports manual collapse toggle",
		() => {
		Object.defineProperty(window, "matchMedia", {
			configurable: true,
			writable: true,
			value: undefined,
		});
		render(
			<Sidebar
				subscriptions={[]}
				apiHealthState="healthy"
				apiHealthUrl="http://127.0.0.1:9000/healthz"
				apiHealthLabel="正常"
			/>,
		);

		const toggle = screen.getByRole("button", { name: "折叠侧边栏" });
		fireEvent.click(toggle);
		expect(screen.getByRole("button", { name: "展开导航面板" })).toBeInTheDocument();
		},
		SIDEBAR_TIMEOUT_MS,
	);

	it(
		"marks homepage active and skips category grouping when no enabled subscriptions exist",
		() => {
			usePathnameMock.mockReturnValue("/");
			useSearchParamsMock.mockReturnValue(createSearchParams(""));

			render(
				<Sidebar
					subscriptions={[
						{
							id: "sub-disabled-only",
							platform: "rss",
							source_type: "rss_generic",
							source_value: "",
							source_name: "",
							adapter_type: "rss_generic",
							source_url: null,
							rsshub_route: "",
							category: "misc",
							tags: [],
							priority: 10,
							enabled: false,
							created_at: "2026-03-01T00:00:00Z",
							updated_at: "2026-03-01T00:00:00Z",
						},
					]}
					apiHealthState="healthy"
					apiHealthUrl="http://127.0.0.1:9000/healthz"
					apiHealthLabel="正常"
				/>,
			);

			expect(screen.getByRole("link", { name: "首页" })).toHaveAttribute("aria-current", "page");
			expect(screen.queryByRole("link", { name: "科技" })).toBeNull();
			expect(screen.queryByRole("link", { name: "AI 摘要" })).not.toHaveAttribute("aria-current");
		},
		SIDEBAR_TIMEOUT_MS,
	);

	it(
		"shows subscription load failure hint with recovery link",
		() => {
			render(
				<Sidebar
					subscriptions={[]}
					subscriptionsLoadError
					apiHealthState="unhealthy"
					apiHealthUrl="http://127.0.0.1:9000/healthz"
					apiHealthLabel="异常"
				/>,
			);

			expect(screen.getByText("订阅列表加载失败，可在订阅管理中重试。")).toBeInTheDocument();
			expect(screen.getByRole("link", { name: "前往订阅管理" })).toHaveAttribute(
				"href",
				"/subscriptions",
			);
		},
		SIDEBAR_TIMEOUT_MS,
	);

	it(
		"falls back to source value and unnamed labels for subscription links",
		() => {
			usePathnameMock.mockReturnValue("/feed");
			useSearchParamsMock.mockReturnValue(createSearchParams("sub=sub-fallback"));

			render(
				<Sidebar
					subscriptions={[
						{
							id: "sub-fallback",
							platform: "youtube",
							source_type: "url",
							source_value: "https://example.com/source",
							source_name: "",
							adapter_type: "rss_generic",
							source_url: null,
							rsshub_route: "",
							category: "tech",
							tags: [],
							priority: 40,
							enabled: true,
							created_at: "2026-03-01T00:00:00Z",
							updated_at: "2026-03-01T00:00:00Z",
						},
						{
							id: "sub-unnamed",
							platform: "youtube",
							source_type: "url",
							source_value: "",
							source_name: "",
							adapter_type: "rss_generic",
							source_url: null,
							rsshub_route: "",
							category: "tech",
							tags: [],
							priority: 30,
							enabled: true,
							created_at: "2026-03-01T00:00:00Z",
							updated_at: "2026-03-01T00:00:00Z",
						},
					]}
					apiHealthState="timeout_or_unknown"
					apiHealthUrl="http://127.0.0.1:9000/healthz"
					apiHealthLabel="超时/未知"
				/>,
			);

			expect(screen.getByRole("link", { name: "https://example.com/source" })).toHaveAttribute(
				"aria-current",
				"page",
			);
			expect(screen.getByRole("link", { name: "未命名" })).toBeInTheDocument();
			expect(screen.getByRole("link", { name: "API 状态：超时/未知" })).toBeInTheDocument();
		},
		SIDEBAR_TIMEOUT_MS,
	);

	it(
		"marks jobs and settings routes active while feed root stays inactive",
		() => {
			usePathnameMock.mockReturnValue("/jobs/details");
			useSearchParamsMock.mockReturnValue(createSearchParams(""));

			const { rerender } = render(
				<Sidebar
					subscriptions={[]}
					apiHealthState="healthy"
					apiHealthUrl="http://127.0.0.1:9000/healthz"
					apiHealthLabel="正常"
				/>,
			);

			expect(screen.getByRole("link", { name: "任务" })).toHaveAttribute("aria-current", "page");
			expect(screen.getByRole("link", { name: "AI 摘要" })).not.toHaveAttribute("aria-current");

			usePathnameMock.mockReturnValue("/settings/profile");
			rerender(
				<Sidebar
					subscriptions={[]}
					apiHealthState="healthy"
					apiHealthUrl="http://127.0.0.1:9000/healthz"
					apiHealthLabel="正常"
				/>,
			);

			expect(screen.getByRole("link", { name: "设置" })).toHaveAttribute("aria-current", "page");
		},
		SIDEBAR_TIMEOUT_MS,
	);

	it(
		"marks feed root active when no category or subscription filter is selected",
		() => {
			usePathnameMock.mockReturnValue("/feed");
			useSearchParamsMock.mockReturnValue(createSearchParams(""));

			render(
				<Sidebar
					subscriptions={[]}
					apiHealthState="unhealthy"
					apiHealthUrl="http://127.0.0.1:9000/healthz"
					apiHealthLabel="异常"
				/>,
			);

			expect(screen.getByRole("link", { name: "AI 摘要" })).toHaveAttribute("aria-current", "page");
			expect(screen.getByRole("link", { name: "API 状态：异常" })).toBeInTheDocument();
		},
		SIDEBAR_TIMEOUT_MS,
	);
});
