import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { usePathnameMock } = vi.hoisted(() => ({
	usePathnameMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
	usePathname: usePathnameMock,
}));

import { RouteTransition } from "@/components/route-transition";

describe("RouteTransition", () => {
	beforeEach(() => {
		vi.clearAllMocks();
		vi.spyOn(window, "requestAnimationFrame").mockImplementation((callback: FrameRequestCallback) => {
			callback(16);
			return 1;
		});
		vi.spyOn(window, "cancelAnimationFrame").mockImplementation(() => {});
	});

	it("announces mapped route label and focuses the route heading", () => {
		usePathnameMock.mockReturnValue("/settings/profile");
		render(
			<RouteTransition>
				<div>
					<h2 data-route-focus-target="true">旧标题</h2>
					<h1 data-route-heading>通知配置</h1>
				</div>
			</RouteTransition>,
		);

		const heading = screen.getByRole("heading", { name: "通知配置" });
		expect(screen.getByRole("status")).toHaveTextContent("已切换到：设置");
		expect(heading).toHaveAttribute("tabindex", "-1");
		expect(heading).toHaveAttribute("data-route-focus-target", "true");
		expect(document.activeElement).toBe(heading);
		expect(screen.getByRole("heading", { name: "旧标题" })).not.toHaveAttribute(
			"data-route-focus-target",
		);
	});

	it("maps root pathname to homepage label", () => {
		usePathnameMock.mockReturnValue("/");
		render(
			<RouteTransition>
				<h1>首页看板</h1>
			</RouteTransition>,
		);

		expect(screen.getByRole("status")).toHaveTextContent("已切换到：首页");
	});

	it("falls back to generic label for unknown routes", () => {
		usePathnameMock.mockReturnValue("/custom-route");
		render(
			<RouteTransition>
				<h1>自定义页面</h1>
			</RouteTransition>,
		);

		expect(screen.getByRole("status")).toHaveTextContent("已切换到：页面");
	});

	it("skips focus updates when no heading is present", () => {
		usePathnameMock.mockReturnValue("/feed");
		render(
			<RouteTransition>
				<div>无标题内容</div>
			</RouteTransition>,
		);

		expect(screen.getByRole("status")).toHaveTextContent("已切换到：AI 摘要");
	});
});
