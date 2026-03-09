import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SubscriptionBatchPanel } from "@/components/subscription-batch-panel";
import type { Subscription } from "@/lib/api/types";

const mockRefresh = vi.fn();
const mockReplace = vi.fn();
vi.mock("next/navigation", () => ({
	useRouter: () => ({ refresh: mockRefresh, replace: mockReplace }),
}));

const mockBatchUpdate = vi.fn();
const mockDelete = vi.fn();
vi.mock("@/lib/api/client", () => ({
	apiClient: {
		batchUpdateSubscriptionCategory: (...args: unknown[]) => mockBatchUpdate(...args),
		deleteSubscription: (...args: unknown[]) => mockDelete(...args),
	},
}));

vi.mock("@/lib/format", () => ({
	formatDateTime: (v: string) => v,
}));

const MOCK_SUBS: Subscription[] = [
	{
		id: "sub-1",
		source_name: "Tech Channel",
		source_value: "UC123",
		rsshub_route: "/bilibili/user/video/123",
		platform: "bilibili",
		source_type: "user_video",
		adapter_type: "bilibili_uid",
		source_url: null,
		category: "tech",
		tags: ["ai"],
		priority: 80,
		enabled: true,
		created_at: "2026-02-23T00:00:00Z",
		updated_at: "2026-02-23T00:00:00Z",
	},
	{
		id: "sub-2",
		source_name: "Finance Blog",
		source_value: "https://example.com/feed",
		rsshub_route: "",
		platform: "rss",
		source_type: "rss_generic",
		adapter_type: "rss_generic",
		source_url: "https://example.com/feed",
		category: "macro",
		tags: [],
		priority: 50,
		enabled: true,
		created_at: "2026-02-22T00:00:00Z",
		updated_at: "2026-02-22T00:00:00Z",
	},
	{
		id: "sub-3",
		source_name: "",
		source_value: "",
		rsshub_route: "",
		platform: "youtube",
		source_type: "url",
		adapter_type: "rsshub_route",
		source_url: null,
		category: "misc",
		tags: [],
		priority: 10,
		enabled: false,
		created_at: "2026-02-21T00:00:00Z",
		updated_at: "2026-02-21T00:00:00Z",
	},
];

describe("SubscriptionBatchPanel", () => {
	const PANEL_TEST_TIMEOUT_MS = 15000;

	beforeEach(() => {
		vi.clearAllMocks();
	});

	afterEach(() => {
		vi.useRealTimers();
	});

	it(
		"renders empty message when no subscriptions",
		() => {
			render(<SubscriptionBatchPanel subscriptions={[]} />);
			expect(screen.getByText("暂无订阅数据。")).toBeInTheDocument();
		},
		PANEL_TEST_TIMEOUT_MS,
	);

	it(
		"renders all subscriptions rows",
		() => {
			render(<SubscriptionBatchPanel subscriptions={MOCK_SUBS} />);
			expect(screen.getByText("当前订阅列表")).toBeInTheDocument();
			expect(screen.getByRole("columnheader", { name: "来源" })).toHaveAttribute("scope", "col");
			expect(screen.getByText("Tech Channel")).toBeInTheDocument();
			expect(screen.getByText("Finance Blog")).toBeInTheDocument();
			expect(screen.getByText("科技")).toBeInTheDocument();
			expect(screen.getByText("宏观")).toBeInTheDocument();
		},
		PANEL_TEST_TIMEOUT_MS,
	);

		it(
			"renders category badge semantics and shadcn status badges",
		() => {
			render(<SubscriptionBatchPanel subscriptions={MOCK_SUBS} />);

			const techRow = screen.getByText("Tech Channel").closest("tr");
			const disabledRow = screen.getByLabelText("选择 订阅 sub-3").closest("tr");
			expect(techRow).not.toBeNull();
			expect(disabledRow).not.toBeNull();

			const techBadge = within(techRow as HTMLElement).getByText("科技");
			expect(techBadge).toHaveClass("sub-category-badge");
			expect(techBadge).toHaveAttribute("data-category", "tech");
			const enabledBadge = within(techRow as HTMLElement).getByText("启用");
			const disabledBadge = within(disabledRow as HTMLElement).getByText("停用");
			expect(enabledBadge).toHaveAttribute("data-slot", "badge");
			expect(disabledBadge).toHaveAttribute("data-slot", "badge");
			expect(enabledBadge).not.toHaveClass("status-chip");
			expect(disabledBadge).not.toHaveClass("status-chip");
		},
		PANEL_TEST_TIMEOUT_MS,
	);

	it(
		"renders localized category labels in batch select while preserving english enum values",
		() => {
			render(<SubscriptionBatchPanel subscriptions={MOCK_SUBS} />);
			fireEvent.click(screen.getByLabelText(/^全选/));
			const combo = screen.getByRole("combobox", { name: "批量设分类" });
			expect(combo).toBeInTheDocument();
			expect(combo).toHaveTextContent("其他");
			fireEvent.click(combo);
			expect(screen.getByRole("option", { name: "创作者" })).toBeInTheDocument();
		},
		PANEL_TEST_TIMEOUT_MS,
	);

	it(
		"select-all checkbox selects all rows",
		() => {
			render(<SubscriptionBatchPanel subscriptions={MOCK_SUBS} />);
			const allCheckbox = screen.getByLabelText(/^全选/);
			fireEvent.click(allCheckbox);
			const rowCheckboxes = screen.getAllByRole("checkbox").filter((cb) => cb !== allCheckbox);
			rowCheckboxes.forEach((cb) => {
				expect(cb).toBeChecked();
			});
		},
		PANEL_TEST_TIMEOUT_MS,
	);

	it(
		"select-all checkbox clears selection on second toggle",
		() => {
			render(<SubscriptionBatchPanel subscriptions={MOCK_SUBS} />);
			const allCheckbox = screen.getByLabelText(/^全选/);
			fireEvent.click(allCheckbox);
			expect(screen.getByText(/已选/)).toBeInTheDocument();
			fireEvent.click(allCheckbox);
			expect(screen.queryByText(/已选/)).not.toBeInTheDocument();
		},
		PANEL_TEST_TIMEOUT_MS,
	);

	it(
		"shows batch action bar when items are selected",
		() => {
			render(<SubscriptionBatchPanel subscriptions={MOCK_SUBS} />);
			fireEvent.click(screen.getByLabelText(/^全选/));

			expect(screen.getByText(/已选/)).toBeInTheDocument();
			expect(screen.getByRole("button", { name: "应用分类" })).toBeInTheDocument();
		},
		PANEL_TEST_TIMEOUT_MS,
	);

	it(
		"adds pending feedback class, data state and aria-busy while applying category",
		async () => {
			let resolveBatch: ((value: { updated: number }) => void) | undefined;
			mockBatchUpdate.mockReturnValue(
				new Promise<{ updated: number }>((resolve) => {
					resolveBatch = resolve;
				}),
			);
			render(<SubscriptionBatchPanel subscriptions={MOCK_SUBS} />);

			fireEvent.click(screen.getByLabelText(/^全选/));
			fireEvent.click(screen.getByRole("button", { name: "应用分类" }));

			const pendingButton = screen.getByRole("button", { name: "应用分类中…" });
			expect(pendingButton).toHaveAttribute("data-feedback-state", "pending");
			expect(pendingButton).toHaveAttribute("data-feedback-state", "pending");
			expect(pendingButton).toHaveAttribute("aria-busy", "true");
			expect(pendingButton).toBeDisabled();

			resolveBatch?.({ updated: 3 });
			await waitFor(() => {
				expect(screen.queryByRole("button", { name: "应用分类中…" })).not.toBeInTheDocument();
			});
		},
		PANEL_TEST_TIMEOUT_MS,
	);

	it(
		"toggles single row selection on and off",
		() => {
			render(<SubscriptionBatchPanel subscriptions={MOCK_SUBS} />);
			const oneCheckbox = screen.getByLabelText("选择 Tech Channel");
			fireEvent.click(oneCheckbox);
			expect(screen.getByText(/已选/)).toBeInTheDocument();
			expect(screen.getByText("1")).toBeInTheDocument();

			fireEvent.click(oneCheckbox);
			expect(screen.queryByText(/已选/)).not.toBeInTheDocument();
		},
		PANEL_TEST_TIMEOUT_MS,
	);

	it(
		"submits selected ids and category for batch update and shows success",
		async () => {
			mockBatchUpdate.mockResolvedValue({ updated: 2 });
			render(<SubscriptionBatchPanel subscriptions={MOCK_SUBS} />);

			fireEvent.click(screen.getByLabelText(/^全选/));
			fireEvent.click(screen.getByRole("combobox", { name: "批量设分类" }));
			fireEvent.click(screen.getByRole("option", { name: "创作者" }));
			fireEvent.click(screen.getByRole("button", { name: "应用分类" }));

			await waitFor(() => {
				expect(mockBatchUpdate).toHaveBeenCalledTimes(1);
				expect(mockBatchUpdate).toHaveBeenCalledWith({
					ids: expect.arrayContaining(["sub-1", "sub-2"]),
					category: "creator",
				});
			});
			await waitFor(() => {
				expect(screen.getByText("已将 2 条订阅移至分类「创作者」")).toBeInTheDocument();
			});
			expect(mockRefresh).toHaveBeenCalledTimes(1);
		},
		PANEL_TEST_TIMEOUT_MS,
	);

	it(
		"shows explicit error message when batch update fails",
		async () => {
			mockBatchUpdate.mockRejectedValue(new Error("Server error"));
			render(<SubscriptionBatchPanel subscriptions={MOCK_SUBS} />);

			fireEvent.click(screen.getByLabelText(/^全选/));
			fireEvent.click(screen.getByRole("button", { name: "应用分类" }));

			await waitFor(() => {
				expect(mockBatchUpdate).toHaveBeenCalledTimes(1);
			});
			await waitFor(() => {
				expect(screen.getByText("操作失败：请求失败，请稍后重试。")).toBeInTheDocument();
			});
			expect(mockRefresh).not.toHaveBeenCalled();
		},
		PANEL_TEST_TIMEOUT_MS,
	);

	it(
		"retries batch update without session header when local e2e preflight fails",
		async () => {
			mockBatchUpdate
				.mockRejectedValueOnce(new Error("ERR_REQUEST_FAILED"))
				.mockResolvedValueOnce({ updated: 1 });
			render(<SubscriptionBatchPanel subscriptions={MOCK_SUBS} sessionToken="session-token" />);

			fireEvent.click(screen.getByLabelText("选择 Tech Channel"));
			fireEvent.click(screen.getByRole("button", { name: "应用分类" }));

			await waitFor(() => {
				expect(mockBatchUpdate).toHaveBeenCalledTimes(2);
			});
			expect(mockBatchUpdate).toHaveBeenNthCalledWith(
				1,
				{ ids: ["sub-1"], category: "misc" },
				{ webSessionToken: "session-token" },
			);
			expect(mockBatchUpdate).toHaveBeenNthCalledWith(2, {
				ids: ["sub-1"],
				category: "misc",
			});
		},
		PANEL_TEST_TIMEOUT_MS,
	);

	it(
		"does not retry batch update when failure is not the preflight error",
		async () => {
			mockBatchUpdate.mockRejectedValue(new Error("ERR_INVALID_INPUT"));
			render(<SubscriptionBatchPanel subscriptions={MOCK_SUBS} sessionToken="session-token" />);

			fireEvent.click(screen.getByLabelText("选择 Tech Channel"));
			fireEvent.click(screen.getByRole("button", { name: "应用分类" }));

			await waitFor(() => {
				expect(mockBatchUpdate).toHaveBeenCalledTimes(1);
			});
			expect(screen.getByText("操作失败：输入参数不合法，请检查后重试。")).toBeInTheDocument();
		},
		PANEL_TEST_TIMEOUT_MS,
	);

	it(
		"shows undo after batch update and restores previous categories when undone",
		async () => {
			mockBatchUpdate.mockResolvedValueOnce({ updated: 2 });
			mockBatchUpdate.mockResolvedValue({ updated: 1 });
			render(<SubscriptionBatchPanel subscriptions={MOCK_SUBS} />);

			fireEvent.click(screen.getByLabelText("选择 Tech Channel"));
			fireEvent.click(screen.getByLabelText("选择 Finance Blog"));
			fireEvent.click(screen.getByRole("combobox", { name: "批量设分类" }));
			fireEvent.click(screen.getByRole("option", { name: "创作者" }));
			fireEvent.click(screen.getByRole("button", { name: "应用分类" }));

			await waitFor(() => {
				expect(screen.getByRole("button", { name: "撤销" })).toBeInTheDocument();
			});

			const techRow = screen.getByText("Tech Channel").closest("tr");
			const financeRow = screen.getByText("Finance Blog").closest("tr");
			expect(techRow).not.toBeNull();
			expect(financeRow).not.toBeNull();
			expect(within(techRow as HTMLElement).getByText("创作者")).toBeInTheDocument();
			expect(within(financeRow as HTMLElement).getByText("创作者")).toBeInTheDocument();

			fireEvent.click(screen.getByRole("button", { name: "撤销" }));

			await waitFor(() => {
				expect(mockBatchUpdate).toHaveBeenCalledWith({ ids: ["sub-1"], category: "tech" });
				expect(mockBatchUpdate).toHaveBeenCalledWith({ ids: ["sub-2"], category: "macro" });
			});
			await waitFor(() => {
				expect(within(techRow as HTMLElement).getByText("科技")).toBeInTheDocument();
				expect(within(financeRow as HTMLElement).getByText("宏观")).toBeInTheDocument();
			});
			expect(screen.getByText("已撤销分类变更，恢复 2 条订阅至原分类。")).toBeInTheDocument();
			expect(screen.getByText("已恢复 2 条订阅至原分类。")).toBeInTheDocument();
		},
		PANEL_TEST_TIMEOUT_MS,
	);

	it(
		"updates undo countdown and removes undo CTA after expiration while keeping history",
		async () => {
			vi.useFakeTimers();
			mockBatchUpdate.mockResolvedValueOnce({ updated: 2 });
			render(<SubscriptionBatchPanel subscriptions={MOCK_SUBS} />);

			fireEvent.click(screen.getByLabelText("选择 Tech Channel"));
			fireEvent.click(screen.getByLabelText("选择 Finance Blog"));
			fireEvent.click(screen.getByRole("combobox", { name: "批量设分类" }));
			fireEvent.click(screen.getByRole("option", { name: "创作者" }));
			fireEvent.click(screen.getByRole("button", { name: "应用分类" }));

			await act(async () => {
				await Promise.resolve();
			});
			expect(screen.getByRole("button", { name: "撤销" })).toBeInTheDocument();
			expect(screen.getByText(/可在 10 秒内撤销/)).toBeInTheDocument();

			act(() => {
				vi.advanceTimersByTime(1000);
			});
			expect(screen.getByText(/可在 9 秒内撤销/)).toBeInTheDocument();

			act(() => {
				vi.advanceTimersByTime(9000);
			});
			expect(screen.queryByRole("button", { name: "撤销" })).not.toBeInTheDocument();
			expect(screen.getByText("批量分类撤销窗口已结束。")).toBeInTheDocument();
		},
		PANEL_TEST_TIMEOUT_MS,
	);

	it(
		"shows explicit error feedback when undo category operation fails",
		async () => {
			mockBatchUpdate.mockResolvedValueOnce({ updated: 2 });
			mockBatchUpdate.mockRejectedValueOnce(new Error("undo failed"));
			render(<SubscriptionBatchPanel subscriptions={MOCK_SUBS} />);

			fireEvent.click(screen.getByLabelText("选择 Tech Channel"));
			fireEvent.click(screen.getByLabelText("选择 Finance Blog"));
			fireEvent.click(screen.getByRole("combobox", { name: "批量设分类" }));
			fireEvent.click(screen.getByRole("option", { name: "创作者" }));
			fireEvent.click(screen.getByRole("button", { name: "应用分类" }));

			await waitFor(() => {
				expect(screen.getByRole("button", { name: "撤销" })).toBeInTheDocument();
			});
			fireEvent.click(screen.getByRole("button", { name: "撤销" }));

			await waitFor(() => {
				expect(screen.getByText("撤销失败：请求失败，请稍后重试。")).toBeInTheDocument();
			});
			expect(screen.getByText("上次撤销失败，请稍后重试。")).toBeInTheDocument();
			expect(screen.getByRole("button", { name: "撤销" })).toBeInTheDocument();
		},
		PANEL_TEST_TIMEOUT_MS,
	);

	it(
		"cancel selection clears selected state and hides action bar",
		() => {
			render(<SubscriptionBatchPanel subscriptions={MOCK_SUBS} />);
			fireEvent.click(screen.getByLabelText(/^全选/));

			expect(screen.getByRole("button", { name: "取消选择" })).toBeInTheDocument();
			fireEvent.click(screen.getByRole("button", { name: "取消选择" }));
			expect(screen.queryByText(/已选/)).not.toBeInTheDocument();
		},
		PANEL_TEST_TIMEOUT_MS,
	);

	it(
		"requires confirmation before deleting and sends exact id on confirm",
		async () => {
			mockDelete.mockResolvedValue(undefined);
			render(<SubscriptionBatchPanel subscriptions={MOCK_SUBS} />);

			const deleteButtons = screen.getAllByRole("button", { name: "删除" });
			fireEvent.click(deleteButtons[0]);

			expect(mockDelete).not.toHaveBeenCalled();
			fireEvent.click(screen.getByRole("button", { name: "确认删除「Tech Channel」" }));

			await waitFor(() => {
				expect(mockDelete).toHaveBeenCalledTimes(1);
				expect(mockDelete).toHaveBeenCalledWith("sub-1");
			});
			expect(mockReplace).toHaveBeenCalledWith(
				"/subscriptions?status=success&code=SUBSCRIPTION_DELETED",
			);
			expect(mockRefresh).toHaveBeenCalledTimes(1);
		},
		PANEL_TEST_TIMEOUT_MS,
	);

	it(
		"retries delete without session header when local e2e preflight fails",
		async () => {
			mockDelete
				.mockRejectedValueOnce(new Error("ERR_REQUEST_FAILED"))
				.mockResolvedValueOnce(undefined);
			render(<SubscriptionBatchPanel subscriptions={MOCK_SUBS} sessionToken="session-token" />);

			fireEvent.click(screen.getAllByRole("button", { name: "删除" })[0]);
			fireEvent.click(screen.getByRole("button", { name: "确认删除「Tech Channel」" }));

			await waitFor(() => {
				expect(mockDelete).toHaveBeenCalledTimes(2);
			});
			expect(mockDelete).toHaveBeenNthCalledWith(1, "sub-1", { webSessionToken: "session-token" });
			expect(mockDelete).toHaveBeenNthCalledWith(2, "sub-1");
		},
		PANEL_TEST_TIMEOUT_MS,
	);

	it(
		"adds row state markers for selection and delete states",
		async () => {
			let resolveDelete: (() => void) | undefined;
			mockDelete.mockReturnValue(
				new Promise<void>((resolve) => {
					resolveDelete = resolve;
				}),
			);
			render(<SubscriptionBatchPanel subscriptions={MOCK_SUBS} />);

			const firstRowCheckbox = screen.getByLabelText("选择 Tech Channel");
			const firstDeleteButton = screen.getAllByRole("button", { name: "删除" })[0];
			const firstRow = firstRowCheckbox.closest("tr");
			expect(firstRow).not.toBeNull();
			expect(firstRow).not.toHaveClass("row-selected");
			expect(firstRow).not.toHaveAttribute("data-state");

			fireEvent.click(firstRowCheckbox);
			expect(firstRow).toHaveClass("row-selected");
			expect(firstRow).not.toHaveAttribute("data-state");

			fireEvent.click(firstDeleteButton);
			expect(firstRow).toHaveAttribute("data-state", "confirming-delete");

			fireEvent.click(screen.getByRole("button", { name: "确认删除「Tech Channel」" }));
			await waitFor(() => {
				expect(mockDelete).toHaveBeenCalledTimes(1);
			});
			expect(firstRow).toHaveAttribute("data-state", "deleting");

			resolveDelete?.();
			await waitFor(() => {
				expect(screen.queryByText("Tech Channel")).not.toBeInTheDocument();
			});
		},
		PANEL_TEST_TIMEOUT_MS,
	);

	it(
		"allows canceling delete confirmation without calling delete API",
		() => {
			render(<SubscriptionBatchPanel subscriptions={MOCK_SUBS} />);

			const deleteButtons = screen.getAllByRole("button", { name: "删除" });
			fireEvent.click(deleteButtons[0]);
			expect(screen.getByRole("button", { name: "确认删除「Tech Channel」" })).toBeInTheDocument();

			fireEvent.click(screen.getByRole("button", { name: "取消" }));
			expect(mockDelete).not.toHaveBeenCalled();
			expect(screen.queryByRole("button", { name: "确认删除「Tech Channel」" })).not.toBeInTheDocument();
			expect(screen.getAllByRole("button", { name: "删除" })[0]).toHaveFocus();
		},
		PANEL_TEST_TIMEOUT_MS,
	);

	it(
		"shows delete failure message when API rejects",
		async () => {
			mockDelete.mockRejectedValue(new Error("delete denied"));
			render(<SubscriptionBatchPanel subscriptions={MOCK_SUBS} />);

			const deleteButtons = screen.getAllByRole("button", { name: "删除" });
			fireEvent.click(deleteButtons[0]);
			fireEvent.click(screen.getByRole("button", { name: "确认删除「Tech Channel」" }));

			await waitFor(() => {
				expect(mockDelete).toHaveBeenCalledTimes(1);
			});
			await waitFor(() => {
				expect(screen.getByText("删除失败：请求失败，请稍后重试。")).toBeInTheDocument();
			});
			await waitFor(() => {
				expect(screen.getAllByRole("button", { name: "删除" })[0]).toHaveFocus();
			});
		},
		PANEL_TEST_TIMEOUT_MS,
	);

	it(
		"uses non-empty aria-label fallback when source fields are empty",
		() => {
			render(<SubscriptionBatchPanel subscriptions={MOCK_SUBS} />);
			expect(screen.getByLabelText("选择 订阅 sub-3")).toBeInTheDocument();
		},
		PANEL_TEST_TIMEOUT_MS,
	);

	it(
		"announces delete target with stable fallback name",
		() => {
			render(<SubscriptionBatchPanel subscriptions={MOCK_SUBS} />);
			const deleteButtons = screen.getAllByRole("button", { name: "删除" });
			fireEvent.click(deleteButtons[2]);
			expect(screen.getByText("已进入删除确认，目标为 订阅 sub-3。")).toBeInTheDocument();
		},
		PANEL_TEST_TIMEOUT_MS,
	);
});
