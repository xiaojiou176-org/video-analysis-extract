import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Sheet, SheetContent, SheetDescription, SheetTitle, SheetTrigger } from "@/components/ui/sheet";

describe("Sheet", () => {
	it(
		"uses localized close label and can hide the close button",
		() => {
		const { rerender } = render(
			<Sheet>
				<SheetTrigger>打开</SheetTrigger>
				<SheetContent side="right">
					<SheetTitle>标题</SheetTitle>
					<SheetDescription>抽屉内容描述</SheetDescription>
					<div>内容</div>
				</SheetContent>
			</Sheet>,
		);

		fireEvent.click(screen.getByRole("button", { name: "打开" }));
		expect(screen.getByText("关闭")).toHaveClass("sr-only");

		rerender(
			<Sheet defaultOpen>
				<SheetContent side="left" showCloseButton={false}>
					<SheetTitle>标题</SheetTitle>
					<SheetDescription>抽屉内容描述</SheetDescription>
					<div>内容</div>
				</SheetContent>
			</Sheet>,
		);

		expect(screen.queryByText("关闭")).not.toBeInTheDocument();
		},
		15_000,
	);

	it("renders top and bottom sheet variants", () => {
		const { rerender } = render(
			<Sheet defaultOpen>
				<SheetContent side="top">
					<SheetTitle>顶部抽屉</SheetTitle>
					<SheetDescription>顶部描述</SheetDescription>
				</SheetContent>
			</Sheet>,
		);

		expect(screen.getByText("顶部抽屉").closest('[data-slot="sheet-content"]')).toHaveClass(
			"inset-x-0",
		);

		rerender(
			<Sheet defaultOpen>
				<SheetContent side="bottom">
					<SheetTitle>底部抽屉</SheetTitle>
					<SheetDescription>底部描述</SheetDescription>
				</SheetContent>
			</Sheet>,
		);

		expect(screen.getByText("底部抽屉").closest('[data-slot="sheet-content"]')).toHaveClass(
			"bottom-0",
		);
	});
});
