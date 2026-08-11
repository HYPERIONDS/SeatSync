import { describe, expect, it } from "vitest";
import { errorMessage, money } from "./utils";

describe("UI value formatting", () => {
  it("formats integer minor units without floating-point storage", () => {
    expect(money(125050, "INR")).toContain("1,250.50");
  });
  it("shows API detail messages", () => {
    expect(errorMessage({ response: { data: { detail: "Seat is already held" } } })).toBe("Seat is already held");
  });
  it("formats FastAPI validation errors without passing objects to React", () => {
    expect(errorMessage({
      response: {
        data: {
          detail: [
            { type: "value_error", loc: ["body", "email"], msg: "Enter a valid email address" },
            { type: "missing", loc: ["body", "password"], msg: "Field required" },
          ],
        },
      },
    })).toBe("Enter a valid email address Field required");
  });
});
