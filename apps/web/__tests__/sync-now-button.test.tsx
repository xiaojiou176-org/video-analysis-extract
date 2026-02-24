import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { SyncNowButton } from "@/components/sync-now-button";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn() }),
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

  it("renders with idle label", () => {
    render(<SyncNowButton />);
    expect(screen.getByRole("button", { name: /sync now/i })).toBeInTheDocument();
  });

  it("shows 'Syncing…' while request is in-flight and disables button", async () => {
    let resolve!: () => void;
    mockPollIngest.mockReturnValue(new Promise<void>((r) => { resolve = r; }));

    render(<SyncNowButton />);
    fireEvent.click(screen.getByRole("button"));

    await waitFor(() => expect(screen.getByText("Syncing…")).toBeInTheDocument());
    expect(screen.getByRole("button")).toBeDisabled();

    await act(async () => { resolve(); });
  });

  it("shows 'Done ✓' immediately after successful API call", async () => {
    mockPollIngest.mockResolvedValue(undefined);
    render(<SyncNowButton />);

    await act(async () => { fireEvent.click(screen.getByRole("button")); });

    await waitFor(() => expect(screen.getByText("Done ✓")).toBeInTheDocument());
  });

  it("shows 'Error — retry?' with destructive style after failed API call", async () => {
    mockPollIngest.mockRejectedValue(new Error("Network error"));
    render(<SyncNowButton />);

    await act(async () => { fireEvent.click(screen.getByRole("button")); });

    await waitFor(() => expect(screen.getByText("Error — retry?")).toBeInTheDocument());
    expect(screen.getByRole("button")).toHaveClass("destructive");
  });
});
