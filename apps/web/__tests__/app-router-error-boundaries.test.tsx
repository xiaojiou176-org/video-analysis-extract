import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import RouteError from "@/app/error";
import GlobalError from "@/app/global-error";

describe("App Router error boundaries", () => {
	it("renders route error boundary with accessible alert semantics", () => {
		const reset = vi.fn();
		const error = Object.assign(new Error("boom"), { digest: "ERR-001" });

		render(<RouteError error={error} reset={reset} />);

		const panel = screen.getByText("页面异常").closest("section");
		expect(panel).not.toBeNull();
		expect(panel).toHaveClass("mx-auto");
		expect(screen.getByRole("heading", { name: "页面加载失败" })).toBeInTheDocument();
		const alert = screen.getByRole("alert");
		expect(alert).toHaveAttribute("aria-live", "assertive");
		expect(alert).toHaveAttribute("aria-atomic", "true");
		expect(screen.getByText("错误编号：")).toBeInTheDocument();
		expect(screen.getByText("ERR-001")).toBeInTheDocument();
		expect(screen.getByRole("button", { name: "重试页面" })).toBeInTheDocument();

		fireEvent.click(screen.getByRole("button", { name: "重试页面" }));
		expect(reset).toHaveBeenCalledTimes(1);
	});

	it("renders global error boundary and supports retry", () => {
		const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
		const reset = vi.fn();
		const error = Object.assign(new Error("fatal"), { digest: "GLOBAL-001" });
		try {
			render(<GlobalError error={error} reset={reset} />);

			expect(document.documentElement).toHaveAttribute("lang", "zh-Hans");
			expect(screen.getByRole("main")).toHaveClass("mx-auto");
			expect(screen.getByRole("heading", { name: "应用发生错误" })).toBeInTheDocument();
			const alert = screen.getByRole("alert");
			expect(alert).toHaveAttribute("aria-live", "assertive");
			expect(alert).toHaveAttribute("aria-atomic", "true");
			expect(screen.getByText("GLOBAL-001")).toBeInTheDocument();
			expect(screen.getByRole("button", { name: "重试页面" })).toBeInTheDocument();

			fireEvent.click(screen.getByRole("button", { name: "重试页面" }));
			expect(reset).toHaveBeenCalledTimes(1);
		} finally {
			consoleErrorSpy.mockRestore();
		}
	});
});
