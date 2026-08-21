import { describe, it, expect, vi } from "vitest";

// useSpeechSynthesis imports ../lib/api, which imports supabaseClient.ts and
// constructs a real Supabase client at module load time — crashes in any
// environment without real VITE_SUPABASE_* env vars (e.g. CI). Mocked the
// same way every other hook test in this suite mocks ../lib/api, even
// though toSpokenText itself never touches it.
vi.mock("../lib/api", () => ({ api: { speak: vi.fn() } }));

import { toSpokenText } from "../hooks/useSpeechSynthesis";

// Real complaint: text that reads fine on screen ("e.g.") sounds robotic
// spoken aloud verbatim by TTS ("eg") — expanded to how a person says it.
describe("toSpokenText", () => {
  it("expands e.g. to for example", () => {
    expect(toSpokenText("Consider edge cases, e.g. an empty array.")).toBe(
      "Consider edge cases, for example an empty array."
    );
  });

  it("expands i.e. to that is", () => {
    expect(toSpokenText("The base case, i.e. n equals zero.")).toBe(
      "The base case, that is n equals zero."
    );
  });

  it("expands etc. to and so on", () => {
    expect(toSpokenText("Consider arrays, lists, etc. for this problem.")).toBe(
      "Consider arrays, lists, and so on for this problem."
    );
  });

  it("expands vs. to versus", () => {
    expect(toSpokenText("Recursive vs. iterative approach.")).toBe(
      "Recursive versus iterative approach."
    );
  });

  it("leaves normal text untouched", () => {
    const text = "Could you walk me through your approach?";
    expect(toSpokenText(text)).toBe(text);
  });

  it("is case-insensitive", () => {
    expect(toSpokenText("E.g. this case.")).toBe("for example this case.");
  });
});
