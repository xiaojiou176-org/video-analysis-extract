import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen } from "@testing-library/react";

import { AppNav } from "@/components/nav";
import { RelativeTime } from "@/components/relative-time";
import { FormValidationController } from "@/components/form-validation-controller";

let mockedPathname = "/";

vi.mock("next/navigation", () => ({
  usePathname: () => mockedPathname,
}));

vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: React.ReactNode }) => (
    <a href={href} {...rest}>{children}</a>
  ),
}));

describe("AppNav", () => {
  it("marks root nav item active for homepage", () => {
    mockedPathname = "/";
    render(<AppNav />);

    expect(screen.getByRole("link", { name: "首页" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "任务" })).not.toHaveAttribute("aria-current");
  });

  it("marks nested route active when pathname starts with section", () => {
    mockedPathname = "/jobs/job-123";
    render(<AppNav />);

    expect(screen.getByRole("link", { name: "任务" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "首页" })).not.toHaveAttribute("aria-current");
  });
});

describe("RelativeTime", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-02-26T00:10:00Z"));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders relative text and keeps datetime/title attributes", () => {
    render(<RelativeTime dateTime="2026-02-26T00:09:30Z" />);

    const time = screen.getByText("刚刚");
    expect(time.tagName.toLowerCase()).toBe("time");
    expect(time).toHaveAttribute("datetime", "2026-02-26T00:09:30Z");
    expect(time).toHaveAttribute("title");
  });

  it("updates rendered text on interval tick", () => {
    render(<RelativeTime dateTime="2026-02-25T23:00:00Z" />);

    expect(screen.getByText("1 小时前")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(60_000);
    });

    expect(screen.getByText("1 小时前")).toBeInTheDocument();

    act(() => {
      vi.setSystemTime(new Date("2026-02-26T02:10:00Z"));
      vi.advanceTimersByTime(60_000);
    });

    expect(screen.getByText("3 小时前")).toBeInTheDocument();
  });

  it("falls back to raw input when date is invalid", () => {
    render(<RelativeTime dateTime="invalid-date" />);

    expect(screen.getByText("invalid-date")).toBeInTheDocument();
  });
});

describe("FormValidationController", () => {
  beforeEach(() => {
    mockedPathname = "/";
    document.body.innerHTML = "";
  });

  it("disables submit while required field is blank then enables after valid input", () => {
    render(
      <>
        <form data-auto-disable-required="true">
          <input name="url" type="url" required />
          <button type="submit">提交</button>
        </form>
        <FormValidationController />
      </>,
    );

    const submit = screen.getByRole("button", { name: "提交" });
    expect(submit).toBeDisabled();
    expect(submit).toHaveAttribute("aria-disabled", "true");

    const input = screen.getByRole("textbox");
    fireEvent.input(input, { target: { value: "https://example.com" } });

    expect(submit).not.toBeDisabled();
    expect(submit).toHaveAttribute("aria-disabled", "false");
  });

  it("enforces require-one and require-one-exclusive rules", () => {
    render(
      <>
        <form data-require-one="job_id,video_url" data-require-one-exclusive="true">
          <input name="job_id" />
          <input name="video_url" />
          <button type="submit">加载</button>
        </form>
        <FormValidationController />
      </>,
    );

    const submit = screen.getByRole("button", { name: "加载" });
    const [jobId, videoUrl] = screen.getAllByRole("textbox");

    expect(submit).toBeDisabled();

    fireEvent.input(jobId, { target: { value: "job-1" } });
    expect(submit).not.toBeDisabled();

    fireEvent.input(videoUrl, { target: { value: "https://example.com/v" } });
    expect(submit).toBeDisabled();

    fireEvent.input(videoUrl, { target: { value: "" } });
    expect(submit).not.toBeDisabled();
  });

  it("toggles dependent field based on checkbox state", () => {
    render(
      <>
        <form>
          <label>
            <input name="daily_digest_enabled" type="checkbox" />
            开启
          </label>
          <input name="daily_digest_hour_utc" data-disabled-unless-checked="daily_digest_enabled" />
          <button type="submit">保存</button>
        </form>
        <FormValidationController />
      </>,
    );

    const checkbox = screen.getByRole("checkbox");
    const input = screen.getByRole("textbox");

    expect(input).toBeDisabled();
    expect(input).toHaveAttribute("aria-disabled", "true");

    fireEvent.click(checkbox);

    expect(input).not.toBeDisabled();
    expect(input).toHaveAttribute("aria-disabled", "false");
  });
});
