import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { usePathnameMock } = vi.hoisted(() => ({
  usePathnameMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  usePathname: usePathnameMock,
}));

vi.mock("next/link", () => ({
  default: ({ href, className, children, ...rest }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) => (
    <a href={href} className={className} {...rest}>
      {children}
    </a>
  ),
}));

import { AppNav } from "@/components/nav";

describe("AppNav", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("marks root nav as active on homepage", () => {
    usePathnameMock.mockReturnValue("/");
    render(<AppNav />);

    expect(screen.getByRole("link", { name: "首页" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "任务" })).not.toHaveAttribute("aria-current");
  });

  it("marks nested route as active by prefix", () => {
    usePathnameMock.mockReturnValue("/jobs/job-123");
    render(<AppNav />);

    expect(screen.getByRole("link", { name: "任务" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "首页" })).not.toHaveAttribute("aria-current");
  });
});
