import { describe, expect, it } from "vitest";

import { VERSION } from "../lib/version";

describe("version", () => {
  it("matches the Python package version", () => {
    expect(VERSION).toBe("0.1.0");
  });
});
