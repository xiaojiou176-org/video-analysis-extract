import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SyncNowButton } from "@/components/sync-now-button";

const mockRefresh = vi.fn();
vi.mock("next/navigation", () => ({
	useRouter: () => ({ refresh: mockRefresh }),
}));

const mockPollIngest = vi.fn();
vi.mock("@/lib/api/client", () => ({
	apiClient: { pollIngest: (...args: unknown[]) => mockPollIngest(...args) },
}));

describe("SyncNowButton", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	afterEach(() => {
		vi.restoreAllMocks();
	});

	it("renders idle label", () => {
		render(<SyncNowButton />);
		expect(screen.getByRole("button", { name: "立即同步" })).toBeInTheDocument();
	});

	it("shows loading state and prevents duplicate requests while in flight", async () => {
		let resolve!: () => void;
		mockPollIngest.mockReturnValue(
			new Promise<void>((r) => {
				resolve = r;
			}),
		);

		render(<SyncNowButton />);
		const button = screen.getByRole("button", { name: "立即同步" });

		fireEvent.click(button);
		fireEvent.click(button);

		await waitFor(() =>
			expect(screen.getByRole("button", { name: "同步中…" })).toBeInTheDocument(),
		);
		expect(screen.getByRole("button", { name: "同步中…" })).toBeDisabled();
		expect(mockPollIngest).toHaveBeenCalledTimes(1);
		expect(mockPollIngest).toHaveBeenCalledWith({});

		await act(async () => {
			resolve();
		});
	});

	it("shows success state then returns to idle and refreshes router", async () => {
		mockPollIngest.mockResolvedValue(undefined);
		render(<SyncNowButton />);

		await act(async () => {
			fireEvent.click(screen.getByRole("button", { name: "立即同步" }));
		});

		await waitFor(() => expect(screen.getByRole("button", { name: "完成 ✓" })).toBeInTheDocument());
		expect(mockPollIngest).toHaveBeenCalledTimes(1);

		await waitFor(
			() => {
				expect(screen.getByRole("button", { name: "立即同步" })).toBeInTheDocument();
				expect(mockRefresh).toHaveBeenCalled();
			},
			{
				timeout: 2500,
			},
		);
	});

	it("shows error state, uses destructive style, then recovers to idle", async () => {
		mockPollIngest.mockRejectedValue(new Error("Network error"));
		render(<SyncNowButton />);

		await act(async () => {
			fireEvent.click(screen.getByRole("button", { name: "立即同步" }));
		});

		await waitFor(() =>
			expect(screen.getByRole("button", { name: "出错，重试？" })).toBeInTheDocument(),
		);
		expect(screen.getByRole("button", { name: "出错，重试？" })).toHaveClass("destructive");
		expect(mockPollIngest).toHaveBeenCalledTimes(1);

		await waitFor(
			() => {
				expect(screen.getByRole("button", { name: "立即同步" })).toBeInTheDocument();
			},
			{
				timeout: 3500,
			},
		);
		expect(mockRefresh).not.toHaveBeenCalled();
	});
});
