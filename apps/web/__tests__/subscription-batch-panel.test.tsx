import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

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
];

describe("SubscriptionBatchPanel", () => {
	const PANEL_TEST_TIMEOUT_MS = 15000;

	beforeEach(() => {
		vi.clearAllMocks();
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
		},
		PANEL_TEST_TIMEOUT_MS,
	);

	it(
		"select-all checkbox selects all rows",
		() => {
			render(<SubscriptionBatchPanel subscriptions={MOCK_SUBS} />);
			const allCheckbox = screen.getByLabelText("全选");
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
			const allCheckbox = screen.getByLabelText("全选");
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
			fireEvent.click(screen.getByLabelText("全选"));

			expect(screen.getByText(/已选/)).toBeInTheDocument();
			expect(screen.getByRole("button", { name: "应用" })).toBeInTheDocument();
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

			fireEvent.click(screen.getByLabelText("全选"));
			fireEvent.change(screen.getByRole("combobox"), { target: { value: "creator" } });
			fireEvent.click(screen.getByRole("button", { name: "应用" }));

			await waitFor(() => {
				expect(mockBatchUpdate).toHaveBeenCalledTimes(1);
				expect(mockBatchUpdate).toHaveBeenCalledWith({
					ids: expect.arrayContaining(["sub-1", "sub-2"]),
					category: "creator",
				});
			});
			await waitFor(() => {
				expect(screen.getByText("已将 2 条订阅移至分类「creator」")).toBeInTheDocument();
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

			fireEvent.click(screen.getByLabelText("全选"));
			fireEvent.click(screen.getByRole("button", { name: "应用" }));

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
		"cancel selection clears selected state and hides action bar",
		() => {
			render(<SubscriptionBatchPanel subscriptions={MOCK_SUBS} />);
			fireEvent.click(screen.getByLabelText("全选"));

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
			fireEvent.click(screen.getByRole("button", { name: "确认删除" }));

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
		"allows canceling delete confirmation without calling delete API",
		() => {
			render(<SubscriptionBatchPanel subscriptions={MOCK_SUBS} />);

			const deleteButtons = screen.getAllByRole("button", { name: "删除" });
			fireEvent.click(deleteButtons[0]);
			expect(screen.getByRole("button", { name: "确认删除" })).toBeInTheDocument();

			fireEvent.click(screen.getByRole("button", { name: "取消" }));
			expect(mockDelete).not.toHaveBeenCalled();
			expect(screen.queryByRole("button", { name: "确认删除" })).not.toBeInTheDocument();
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
			fireEvent.click(screen.getByRole("button", { name: "确认删除" }));

			await waitFor(() => {
				expect(mockDelete).toHaveBeenCalledTimes(1);
			});
			await waitFor(() => {
				expect(screen.getByText("删除失败：请求失败，请稍后重试。")).toBeInTheDocument();
			});
		},
		PANEL_TEST_TIMEOUT_MS,
	);
});
