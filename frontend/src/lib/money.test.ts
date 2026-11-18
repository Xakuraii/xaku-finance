import { describe, it, expect } from "vitest";
import { parseMoneyInput, formatMoney, formatAmountOnly } from "./money";

describe("parseMoneyInput", () => {
  it("rejects more than two decimals", () => {
    expect(parseMoneyInput("1.005", 2)).toEqual({ ok: false, reason: "precision" });
  });

  it("parses valid integer amount", () => {
    expect(parseMoneyInput("500", 2)).toEqual({
      ok: true,
      amountMinor: 50000,
      serialized: "500.00",
    });
  });

  it("parses valid decimal amount", () => {
    expect(parseMoneyInput("1250.50", 2)).toEqual({
      ok: true,
      amountMinor: 125050,
      serialized: "1250.50",
    });
  });

  it("rejects negative amount", () => {
    expect(parseMoneyInput("-10.00", 2)).toEqual({ ok: false, reason: "negative" });
  });

  it("rejects invalid characters", () => {
    expect(parseMoneyInput("abc", 2)).toEqual({ ok: false, reason: "invalid" });
  });
});

describe("formatMoney", () => {
  it("formats with currency code", () => {
    expect(formatMoney(125050, "USD", "en-US")).toBe("1,250.50 USD");
  });

  it("formats KHR amounts", () => {
    expect(formatMoney(5000000, "KHR", "en-US")).toBe("50,000.00 KHR");
  });

  it("formats amount only", () => {
    expect(formatAmountOnly(125050, "en-US")).toBe("1,250.50");
  });
});
