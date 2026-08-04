import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../lib/api", () => ({
  api: {
    getBoilerplate: vi.fn(),
    runTests: vi.fn(),
    trackEvent: vi.fn(),
  },
}));

// Avoids pulling in Monaco/react-markdown (CodeEditor's real dependencies)
// just to get the LANGUAGES table.
vi.mock("../components/CodeEditor", () => ({
  LANGUAGES: [
    { id: "python", label: "Python", monaco: "python", piston: "python", version: "3.10.0" },
    { id: "javascript", label: "JavaScript", monaco: "javascript", piston: "node", version: "18.15.0" },
    { id: "java", label: "Java", monaco: "java", piston: "java", version: "15.0.2" },
    { id: "cpp", label: "C++", monaco: "cpp", piston: "gcc", version: "10.2.0" },
  ],
}));

import { api } from "../lib/api";
import { useCodeRunner, STARTER_CODE } from "../hooks/useCodeRunner";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("useCodeRunner", () => {
  it("starts on python with the python starter code", () => {
    const { result } = renderHook(() => useCodeRunner());
    expect(result.current.language).toBe("python");
    expect(result.current.code).toBe(STARTER_CODE.python);
    expect(result.current.testResults).toBeNull();
    expect(result.current.running).toBe(false);
  });

  it("handleLanguageChange fetches and shows question-specific boilerplate when a session is active", async () => {
    api.getBoilerplate.mockResolvedValue({ boilerplate: "def solve(): ...", supported: true });
    const { result } = renderHook(() => useCodeRunner());

    await act(async () => {
      await result.current.handleLanguageChange("javascript", "sess-1");
    });

    expect(api.getBoilerplate).toHaveBeenCalledWith("sess-1", "node");
    expect(result.current.language).toBe("javascript");
    expect(result.current.code).toBe("def solve(): ...");
  });

  it("handleLanguageChange falls back to starter code when there is no session yet", async () => {
    const { result } = renderHook(() => useCodeRunner());

    await act(async () => {
      await result.current.handleLanguageChange("java", undefined);
    });

    expect(api.getBoilerplate).not.toHaveBeenCalled();
    expect(result.current.language).toBe("java");
    expect(result.current.code).toBe(STARTER_CODE.java);
  });

  it("shows previously-fetched boilerplate immediately on switch-back, instead of flashing generic starter code", async () => {
    api.getBoilerplate.mockResolvedValue({ boilerplate: "js-boilerplate", supported: true });
    const { result } = renderHook(() => useCodeRunner());

    await act(async () => {
      await result.current.handleLanguageChange("javascript", "sess-1");
    });
    await act(async () => {
      await result.current.handleLanguageChange("python", "sess-1");
    });

    // Switching back to javascript re-fetches (to keep it fresh) but the
    // cache means `code` is set to the cached value synchronously, before
    // that fetch resolves — never falling back to STARTER_CODE.javascript.
    let pending;
    act(() => {
      pending = result.current.handleLanguageChange("javascript", "sess-1");
    });
    expect(result.current.code).toBe("js-boilerplate");
    await act(async () => {
      await pending;
    });
  });

  it("handleQuestionAssigned resets to starter code and refetches boilerplate for the new question", async () => {
    api.getBoilerplate.mockResolvedValue({ boilerplate: "new-question-boilerplate", supported: true });
    const { result } = renderHook(() => useCodeRunner());
    const ctx = { id: "q-2", title: "Two Sum", difficulty: "easy", prompt: "p", constraints: [], examples: [], is_stdio: false };

    await act(async () => {
      result.current.handleQuestionAssigned(ctx, "sess-1");
    });
    await waitFor(() => expect(result.current.code).toBe("new-question-boilerplate"));

    expect(result.current.questionContext).toEqual(ctx);
  });

  it("handleResetBoilerplate restores the fetched original after local edits", async () => {
    api.getBoilerplate.mockResolvedValue({ boilerplate: "original-boilerplate", supported: true });
    const { result } = renderHook(() => useCodeRunner());

    await act(async () => {
      await result.current.handleLanguageChange("javascript", "sess-1");
    });
    act(() => {
      result.current.setCode("some edits the candidate made");
    });
    expect(result.current.code).toBe("some edits the candidate made");

    act(() => {
      result.current.handleResetBoilerplate();
    });
    expect(result.current.code).toBe("original-boilerplate");
  });

  it("handleRunCode populates testResults on success", async () => {
    const fakeResult = {
      status: "ok",
      visible_tests: [{ id: 1, label: "case 1", input: "1", expected: "1", passed: true }],
      hidden_tests: [{ id: 2, passed: true }],
      passed: 2,
      total: 2,
    };
    api.runTests.mockResolvedValue(fakeResult);
    const { result } = renderHook(() => useCodeRunner());

    await act(async () => {
      await result.current.handleRunCode("sess-1");
    });

    expect(api.trackEvent).toHaveBeenCalledWith("code_run", { sessionId: "sess-1", properties: { language: "python" } });
    expect(result.current.testResults).toEqual(fakeResult);
    expect(result.current.running).toBe(false);
  });

  it("handleRunCode surfaces a network-failure result (not a fabricated 0-of-N) when the API call rejects", async () => {
    api.runTests.mockRejectedValue(new Error("network down"));
    const { result } = renderHook(() => useCodeRunner());

    await act(async () => {
      await result.current.handleRunCode("sess-1");
    });

    expect(result.current.testResults).toMatchObject({
      status: "compile_error",
      compile_error: "Could not reach the code execution service.",
      passed: 0,
      total: 0,
    });
    expect(result.current.running).toBe(false);
  });

  it("handleRunCode is a no-op without a session id", async () => {
    const { result } = renderHook(() => useCodeRunner());

    await act(async () => {
      await result.current.handleRunCode(undefined);
    });

    expect(api.runTests).not.toHaveBeenCalled();
    expect(result.current.testResults).toBeNull();
  });
});
