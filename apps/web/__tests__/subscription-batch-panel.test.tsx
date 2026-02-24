import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { SubscriptionBatchPanel } from "@/components/subscription-batch-panel";
import type { Subscription } from "@/lib/api/types";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn() }),
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
    updated_at: "2026-02-22T00:00:00Z",
  },
];

describe("SubscriptionBatchPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders 'No subscription data.' when list is empty", () => {
    render(<SubscriptionBatchPanel subscriptions={[]} />);
    expect(screen.getByText("No subscription data.")).toBeInTheDocument();
  });

  it("renders all subscriptions as table rows", () => {
    render(<SubscriptionBatchPanel subscriptions={MOCK_SUBS} />);
    expect(screen.getByText("Tech Channel")).toBeInTheDocument();
    expect(screen.getByText("Finance Blog")).toBeInTheDocument();
  });

  it("select-all checkbox selects all rows", () => {
    render(<SubscriptionBatchPanel subscriptions={MOCK_SUBS} />);
    const allCheckbox = screen.getByLabelText("Select all");
    fireEvent.click(allCheckbox);
    const rowCheckboxes = screen.getAllByRole("checkbox").filter(
      (cb) => cb !== allCheckbox,
    );
    rowCheckboxes.forEach((cb) => expect(cb).toBeChecked());
  });

  it("shows batch action bar when items are selected", () => {
    render(<SubscriptionBatchPanel subscriptions={MOCK_SUBS} />);
    fireEvent.click(screen.getByLabelText("Select all"));
    expect(screen.getByText(/selected/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /apply/i })).toBeInTheDocument();
  });

  it("calls batchUpdateSubscriptionCategory with selected ids and chosen category", async () => {
    mockBatchUpdate.mockResolvedValue({ updated: 2 });
    render(<SubscriptionBatchPanel subscriptions={MOCK_SUBS} />);

    fireEvent.click(screen.getByLabelText("Select all"));
    const select = screen.getByRole("combobox");
    fireEvent.change(select, { target: { value: "creator" } });
    fireEvent.click(screen.getByRole("button", { name: /apply/i }));

    await waitFor(() =>
      expect(mockBatchUpdate).toHaveBeenCalledWith({
        ids: expect.arrayContaining(["sub-1", "sub-2"]),
        category: "creator",
      })
    );
    await waitFor(() =>
      expect(screen.getByText(/Updated 2 subscription/i)).toBeInTheDocument()
    );
  });

  it("shows error message when batchUpdate fails", async () => {
    mockBatchUpdate.mockRejectedValue(new Error("Server error"));
    render(<SubscriptionBatchPanel subscriptions={MOCK_SUBS} />);

    fireEvent.click(screen.getByLabelText("Select all"));
    fireEvent.click(screen.getByRole("button", { name: /apply/i }));

    await waitFor(() =>
      expect(screen.getByText(/Error: Server error/i)).toBeInTheDocument()
    );
  });

  it("cancel button clears selection and hides batch bar", () => {
    render(<SubscriptionBatchPanel subscriptions={MOCK_SUBS} />);
    fireEvent.click(screen.getByLabelText("Select all"));
    expect(screen.getByRole("button", { name: /cancel/i })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(screen.queryByText(/selected/i)).not.toBeInTheDocument();
  });

  it("calls deleteSubscription on delete button click", async () => {
    mockDelete.mockResolvedValue(undefined);
    render(<SubscriptionBatchPanel subscriptions={MOCK_SUBS} />);

    const deleteButtons = screen.getAllByRole("button", { name: /delete/i });
    fireEvent.click(deleteButtons[0]);

    await waitFor(() =>
      expect(mockDelete).toHaveBeenCalledWith("sub-1")
    );
  });
});
