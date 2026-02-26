import { describe, expect, it } from "vitest";

import { resolveSearchParams } from "@/lib/search-params";

describe("resolveSearchParams", () => {
  it("returns empty strings when params are missing", async () => {
    await expect(resolveSearchParams(undefined, ["q", "cursor"] as const)).resolves.toEqual({
      q: "",
      cursor: "",
    });
  });

  it("normalizes strings and array values", async () => {
    const input = Promise.resolve({
      q: "  hello  ",
      category: [" ", "tech", "ops"],
      page: " 2 ",
    });

    await expect(resolveSearchParams(input, ["q", "category", "page"] as const)).resolves.toEqual({
      q: "hello",
      category: "",
      page: "2",
    });
  });

  it("drops non-string params and picks first string in array", async () => {
    const mixed = {
      id: ["", "abc", "def"],
      mode: ["full", "text_only"],
      raw: undefined,
    };

    await expect(resolveSearchParams(mixed, ["id", "mode", "raw"] as const)).resolves.toEqual({
      id: "",
      mode: "full",
      raw: "",
    });
  });
});
