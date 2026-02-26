import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import RouteError from "@/app/error";
import GlobalError from "@/app/global-error";

describe("App Router error boundaries", () => {
	it("renders route error boundary with accessible alert semantics", () => {
		const reset = vi.fn();
		const error = Object.assign(new Error("boom"), { digest: "ERR-001" });

		render(<RouteError error={error} reset={reset} />);

		expect(screen.getByRole("heading", { name: "页面加载失败" })).toBeInTheDocument();
		expect(screen.getByRole("alert")).toBeInTheDocument();
		expect(screen.getByText("错误编号：")).toBeInTheDocument();

		fireEvent.click(screen.getByRole("button", { name: "重试" }));
		expect(reset).toHaveBeenCalledTimes(1);
	});

	it("renders global error boundary and supports retry", () => {
		const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
		const reset = vi.fn();
		const error = Object.assign(new Error("fatal"), { digest: "GLOBAL-001" });
		try {
			render(<GlobalError error={error} reset={reset} />);

			expect(screen.getByRole("heading", { name: "应用发生错误" })).toBeInTheDocument();
			expect(screen.getByRole("alert")).toBeInTheDocument();

			fireEvent.click(screen.getByRole("button", { name: "重试" }));
			expect(reset).toHaveBeenCalledTimes(1);
		} finally {
			consoleErrorSpy.mockRestore();
		}
	});
});
