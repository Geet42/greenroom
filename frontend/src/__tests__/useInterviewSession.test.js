import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

const {
  mockNavigate, mockSpeak, mockStopSpeech, mockPauseSpeech, mockResumeSpeech, mockStart, mockStop, mockReset,
  MockApiError,
} =
  vi.hoisted(() => {
    class MockApiError extends Error {
      constructor(status, message) {
        super(message);
        this.name = "ApiError";
        this.status = status;
      }
    }
    return {
      mockNavigate: vi.fn(),
      mockSpeak: vi.fn(),
      mockStopSpeech: vi.fn(),
      mockPauseSpeech: vi.fn(),
      mockResumeSpeech: vi.fn(),
      mockStart: vi.fn(),
      mockStop: vi.fn(),
      mockReset: vi.fn(),
      MockApiError,
    };
  });

vi.mock("react-router-dom", () => ({
  useNavigate: () => mockNavigate,
}));

vi.mock("../lib/api", () => ({
  ApiError: MockApiError,
  api: {
    startSession: vi.fn(),
    resumeSession: vi.fn(),
    sendMessage: vi.fn(),
    endSession: vi.fn(),
    saveDiagram: vi.fn(),
    trackEvent: vi.fn(),
  },
}));

vi.mock("../lib/supabaseClient", () => ({
  supabase: { auth: { getSession: vi.fn() } },
}));

vi.mock("../hooks/useSpeechRecognition", () => ({
  useSpeechRecognition: () => ({
    isSupported: true,
    isListening: false,
    transcript: "",
    interimTranscript: "",
    start: mockStart,
    stop: mockStop,
    reset: mockReset,
  }),
}));

vi.mock("../hooks/useSpeechSynthesis", () => ({
  useSpeechSynthesis: () => ({
    isSpeaking: false,
    speak: mockSpeak,
    stop: mockStopSpeech,
    pause: mockPauseSpeech,
    resume: mockResumeSpeech,
  }),
}));

import { api, ApiError } from "../lib/api";
import { supabase } from "../lib/supabaseClient";
import { useInterviewSession } from "../hooks/useInterviewSession";

const AUTHED_SESSION = { data: { session: { access_token: "tok" } } };

beforeEach(() => {
  vi.clearAllMocks();
  supabase.auth.getSession.mockResolvedValue(AUTHED_SESSION);
  sessionStorage.clear();
});

describe("useInterviewSession — init", () => {
  it("redirects to /login when there is no authenticated session", async () => {
    supabase.auth.getSession.mockResolvedValue({ data: { session: null } });
    renderHook(() => useInterviewSession({ track: "behavioral" }));

    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith("/login", { replace: true }));
    expect(api.startSession).not.toHaveBeenCalled();
  });

  it("starts a fresh session, speaks the opening question, and tracks session_start", async () => {
    api.startSession.mockResolvedValue({ session_id: "sess-1", track: "behavioral", question: "Tell me about yourself." });
    const onSessionIdReady = vi.fn();
    const { result } = renderHook(() =>
      useInterviewSession({ track: "behavioral", onSessionIdReady })
    );

    await waitFor(() => expect(result.current.sessionId).toBe("sess-1"));
    expect(result.current.messages).toEqual([{ role: "interviewer", text: "Tell me about yourself." }]);
    expect(mockSpeak).toHaveBeenCalledWith("Tell me about yourself.");
    expect(api.trackEvent).toHaveBeenCalledWith(
      "session_start", { sessionId: "sess-1", properties: { track: "behavioral" } },
    );
    expect(onSessionIdReady).toHaveBeenCalledWith("sess-1");
    expect(result.current.loading).toBe(false);
  });

  it("resumes an existing session instead of starting a new one when resumeSessionId is given", async () => {
    api.resumeSession.mockResolvedValue({
      session_id: "sess-1",
      track: "technical",
      history: [
        { role: "interviewer", content: "Here's a problem." },
        { role: "candidate", content: "Let me think." },
      ],
      question_context: { id: "q-1" },
      diagram_elements: [],
    });
    const onQuestionContext = vi.fn();
    const { result } = renderHook(() =>
      useInterviewSession({ track: "technical", resumeSessionId: "sess-1", onQuestionContext })
    );

    await waitFor(() => expect(result.current.sessionId).toBe("sess-1"));
    expect(result.current.messages).toEqual([
      { role: "interviewer", text: "Here's a problem." },
      { role: "candidate", text: "Let me think." },
    ]);
    expect(onQuestionContext).toHaveBeenCalledWith({ id: "q-1" }, "sess-1");
    expect(api.startSession).not.toHaveBeenCalled();
  });

  it("falls back to starting a fresh session when resume fails", async () => {
    api.resumeSession.mockRejectedValue(new Error("410: expired"));
    api.startSession.mockResolvedValue({ session_id: "sess-2", track: "behavioral", question: "Question one." });
    const { result } = renderHook(() =>
      useInterviewSession({ track: "behavioral", resumeSessionId: "stale-session" })
    );

    await waitFor(() => expect(result.current.sessionId).toBe("sess-2"));
    expect(api.startSession).toHaveBeenCalled();
  });

  it("redirects to /login when starting a session returns 401/403", async () => {
    api.startSession.mockRejectedValue(new ApiError(401, "API error 401: unauthorized"));
    renderHook(() => useInterviewSession({ track: "behavioral" }));

    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith("/login", { replace: true }));
  });

  it("shows a friendly message when starting a session returns 429 (too many active sessions)", async () => {
    api.startSession.mockRejectedValue(new ApiError(429, "API error 429: too many requests"));
    const { result } = renderHook(() => useInterviewSession({ track: "behavioral" }));

    await waitFor(() =>
      expect(result.current.messages[0]?.text).toMatch(/too many active sessions/i)
    );
  });
});

async function setUpStartedSession() {
  api.startSession.mockResolvedValue({ session_id: "sess-1", track: "behavioral", question: "Q1" });
  const { result } = renderHook(() => useInterviewSession({ track: "behavioral" }));
  await waitFor(() => expect(result.current.sessionId).toBe("sess-1"));
  return result;
}

function twoNodeDiagram(secondLabel = "DB") {
  return [
    { id: "s1", type: "rectangle" },
    { id: "s1-label", type: "text", containerId: "s1", text: "API" },
    { id: "s2", type: "rectangle" },
    { id: "s2-label", type: "text", containerId: "s2", text: secondLabel },
    { id: "a1", type: "arrow", startBinding: { elementId: "s1" }, endBinding: { elementId: "s2" } },
  ];
}

async function setUpStartedSystemDesignSession(getElements) {
  api.startSession.mockResolvedValue({ session_id: "sess-1", track: "system-design", question: "Q1" });
  const boardRef = { current: { getElements } };
  const { result } = renderHook(() => useInterviewSession({ track: "system-design", boardRef }));
  await waitFor(() => expect(result.current.sessionId).toBe("sess-1"));
  return result;
}

describe("useInterviewSession — handleSend diagram de-duplication (system-design)", () => {
  it("attaches the diagram description on the first send", async () => {
    const result = await setUpStartedSystemDesignSession(() => twoNodeDiagram());
    api.sendMessage.mockResolvedValue({ question: "Tell me about this design." });

    act(() => result.current.setAnswerText("Here's my design."));
    await act(async () => {
      await result.current.handleSend();
    });

    const sentMessage = api.sendMessage.mock.calls[0][0].message;
    expect(sentMessage).toContain("[Architecture diagram]");
    expect(sentMessage).toContain("API");
    expect(sentMessage).toContain("DB");
  });

  it("does not re-attach an identical diagram on the next send", async () => {
    const result = await setUpStartedSystemDesignSession(() => twoNodeDiagram());
    api.sendMessage.mockResolvedValue({ question: "Follow-up 1." });
    act(() => result.current.setAnswerText("Here's my design."));
    await act(async () => {
      await result.current.handleSend();
    });

    api.sendMessage.mockResolvedValue({ question: "Follow-up 2." });
    act(() => result.current.setAnswerText("Still thinking about the cache."));
    await act(async () => {
      await result.current.handleSend();
    });

    const secondMessage = api.sendMessage.mock.calls[1][0].message;
    expect(secondMessage).toBe("Still thinking about the cache.");
  });

  it("re-attaches the diagram once it actually changes", async () => {
    let elements = twoNodeDiagram();
    const result = await setUpStartedSystemDesignSession(() => elements);
    api.sendMessage.mockResolvedValue({ question: "Follow-up 1." });
    act(() => result.current.setAnswerText("Here's my design."));
    await act(async () => {
      await result.current.handleSend();
    });

    elements = twoNodeDiagram("Cache"); // candidate relabels the second component
    api.sendMessage.mockResolvedValue({ question: "Follow-up 2." });
    act(() => result.current.setAnswerText("Added a cache layer."));
    await act(async () => {
      await result.current.handleSend();
    });

    const secondMessage = api.sendMessage.mock.calls[1][0].message;
    expect(secondMessage).toContain("[Architecture diagram]");
    expect(secondMessage).toContain("Cache");
  });

  it("re-attaches the diagram after a candidate-requested question switch even if unchanged", async () => {
    const result = await setUpStartedSystemDesignSession(() => twoNodeDiagram());
    const onQuestionContext = vi.fn();
    // Re-render with onQuestionContext wired (the default helper doesn't pass one).
    const boardRef = { current: { getElements: () => twoNodeDiagram() } };
    const { result: result2 } = renderHook(() =>
      useInterviewSession({ track: "system-design", boardRef, onQuestionContext })
    );
    api.startSession.mockResolvedValue({ session_id: "sess-2", track: "system-design", question: "Q1" });
    await waitFor(() => expect(result2.current.sessionId).toBe("sess-2"));

    api.sendMessage.mockResolvedValue({ question: "First reply." });
    act(() => result2.current.setAnswerText("Here's my design."));
    await act(async () => {
      await result2.current.handleSend();
    });

    api.sendMessage.mockResolvedValue({
      question: "Here's your new problem.",
      question_context: { id: "sd-2", title: "New Problem", difficulty: "medium", prompt: "p", constraints: [], examples: [] },
    });
    act(() => result2.current.setAnswerText("Can I get the next question please?"));
    await act(async () => {
      await result2.current.handleSend();
    });
    expect(onQuestionContext).toHaveBeenCalled();

    api.sendMessage.mockResolvedValue({ question: "Follow-up on new problem." });
    act(() => result2.current.setAnswerText("Here's my design for the new problem."));
    await act(async () => {
      await result2.current.handleSend();
    });

    const thirdMessage = api.sendMessage.mock.calls[2][0].message;
    expect(thirdMessage).toContain("[Architecture diagram]");
  });
});

describe("useInterviewSession — handleSend", () => {
  it("sends the candidate's answer and appends the interviewer's reply", async () => {
    const result = await setUpStartedSession();
    api.sendMessage.mockResolvedValue({ question: "Tell me more." });

    act(() => result.current.setAnswerText("I led a project."));
    await act(async () => {
      await result.current.handleSend();
    });

    expect(api.sendMessage).toHaveBeenCalledWith({
      session_id: "sess-1", message: "I led a project.", code: undefined, language: undefined,
    });
    expect(result.current.messages.at(-2)).toEqual({ role: "candidate", text: "I led a project." });
    expect(result.current.messages.at(-1)).toEqual({ role: "interviewer", text: "Tell me more." });
    expect(mockSpeak).toHaveBeenCalledWith("Tell me more.");
    expect(result.current.answerText).toBe("");
  });

  it("is a no-op when the answer is blank", async () => {
    const result = await setUpStartedSession();
    act(() => result.current.setAnswerText("   "));
    await act(async () => {
      await result.current.handleSend();
    });
    expect(api.sendMessage).not.toHaveBeenCalled();
  });

  it("shows a recoverable error message when sendMessage fails", async () => {
    const result = await setUpStartedSession();
    api.sendMessage.mockRejectedValue(new Error("network down"));
    act(() => result.current.setAnswerText("An answer."));

    await act(async () => {
      await result.current.handleSend();
    });

    expect(result.current.messages.at(-1).text).toMatch(/lost connection/i);
  });
});

describe("useInterviewSession — session expiry / countdown", () => {
  it("computes remainingSeconds from the server-provided expires_at on start", async () => {
    const expiresAt = new Date(Date.now() + 120_000).toISOString();
    api.startSession.mockResolvedValue({
      session_id: "sess-1", track: "behavioral", question: "Q1", expires_at: expiresAt,
    });
    const { result } = renderHook(() => useInterviewSession({ track: "behavioral" }));

    await waitFor(() => expect(result.current.sessionId).toBe("sess-1"));
    await waitFor(() => expect(result.current.remainingSeconds).not.toBeNull());
    // Allow a little slack for time elapsed while the test itself ran.
    expect(result.current.remainingSeconds).toBeGreaterThan(110);
    expect(result.current.remainingSeconds).toBeLessThanOrEqual(120);
  });

  it("locks the session and auto-fetches the report once expires_at has passed", async () => {
    const expiresAt = new Date(Date.now() - 1000).toISOString();
    api.startSession.mockResolvedValue({
      session_id: "sess-1", track: "behavioral", question: "Q1", expires_at: expiresAt,
    });
    api.endSession.mockResolvedValue({});
    const { result } = renderHook(() => useInterviewSession({ track: "behavioral" }));

    await waitFor(() => expect(result.current.sessionLocked).toBe(true));
    expect(result.current.lockMessage).toMatch(/time is up/i);
    await waitFor(() => expect(api.endSession).toHaveBeenCalledWith({ session_id: "sess-1" }));
    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith("/results/sess-1"));
  });

  it("locks the session and fetches the report when sendMessage returns 410 (expired mid-session)", async () => {
    const result = await setUpStartedSession();
    api.sendMessage.mockRejectedValue(new ApiError(410, "API error 410: session expired"));
    api.endSession.mockResolvedValue({});
    act(() => result.current.setAnswerText("one more answer"));

    await act(async () => {
      await result.current.handleSend();
    });

    expect(result.current.sessionLocked).toBe(true);
    await waitFor(() => expect(api.endSession).toHaveBeenCalledWith({ session_id: "sess-1" }));
  });

  it("immediately locks and ends a resumed session whose deadline already passed", async () => {
    api.resumeSession.mockResolvedValue({
      session_id: "sess-1",
      track: "behavioral",
      history: [{ role: "interviewer", content: "Hi." }],
      diagram_elements: [],
      expires_at: new Date(Date.now() - 1000).toISOString(),
    });
    api.endSession.mockResolvedValue({});
    renderHook(() => useInterviewSession({ track: "behavioral", resumeSessionId: "sess-1" }));

    await waitFor(() => expect(api.endSession).toHaveBeenCalledWith({ session_id: "sess-1" }));
    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith("/results/sess-1"));
  });

  it("blocks sending once the session is locked", async () => {
    const expiresAt = new Date(Date.now() - 1000).toISOString();
    api.startSession.mockResolvedValue({
      session_id: "sess-1", track: "behavioral", question: "Q1", expires_at: expiresAt,
    });
    api.endSession.mockResolvedValue({});
    const { result } = renderHook(() => useInterviewSession({ track: "behavioral" }));

    await waitFor(() => expect(result.current.sessionLocked).toBe(true));
    act(() => result.current.setAnswerText("too late"));
    await act(async () => {
      await result.current.handleSend();
    });
    expect(api.sendMessage).not.toHaveBeenCalled();
  });
});

describe("useInterviewSession — handleEnd", () => {
  it("ends the session, tracks session_end, and navigates to the results page", async () => {
    api.startSession.mockResolvedValue({ session_id: "sess-1", track: "behavioral", question: "Q1" });
    api.endSession.mockResolvedValue({});
    const { result } = renderHook(() => useInterviewSession({ track: "behavioral" }));
    await waitFor(() => expect(result.current.sessionId).toBe("sess-1"));

    await act(async () => {
      await result.current.handleEnd();
    });

    expect(api.endSession).toHaveBeenCalledWith({ session_id: "sess-1" });
    expect(api.trackEvent).toHaveBeenCalledWith(
      "session_end", { sessionId: "sess-1", properties: { track: "behavioral" } },
    );
    expect(mockNavigate).toHaveBeenCalledWith("/results/sess-1");
  });

  it("keeps the candidate on the page and shows an error when ending fails", async () => {
    api.startSession.mockResolvedValue({ session_id: "sess-1", track: "behavioral", question: "Q1" });
    api.endSession.mockRejectedValue(new Error("boom"));
    const { result } = renderHook(() => useInterviewSession({ track: "behavioral" }));
    await waitFor(() => expect(result.current.sessionId).toBe("sess-1"));

    await act(async () => {
      await result.current.handleEnd();
    });

    expect(mockNavigate).not.toHaveBeenCalledWith(expect.stringContaining("/results/"));
    expect(result.current.ending).toBe(false);
    expect(result.current.messages.at(-1).text).toMatch(/trouble generating your report/i);
  });
});

describe("useInterviewSession — toggleMute", () => {
  it("pauses speech on mute and resumes it on unmute when no new message arrived", async () => {
    api.startSession.mockResolvedValue({ session_id: "sess-1", track: "behavioral", question: "Q1" });
    const { result } = renderHook(() => useInterviewSession({ track: "behavioral" }));
    await waitFor(() => expect(result.current.sessionId).toBe("sess-1"));

    act(() => result.current.toggleMute());
    expect(result.current.isMuted).toBe(true);
    expect(mockPauseSpeech).toHaveBeenCalled();

    act(() => result.current.toggleMute());
    expect(result.current.isMuted).toBe(false);
    expect(mockResumeSpeech).toHaveBeenCalled();
  });

  it("speaks the latest response fresh (instead of resuming) if a new message arrived while muted", async () => {
    api.startSession.mockResolvedValue({ session_id: "sess-1", track: "behavioral", question: "Opening question." });
    api.sendMessage.mockResolvedValue({ question: "Follow-up while muted." });
    const { result } = renderHook(() => useInterviewSession({ track: "behavioral" }));
    await waitFor(() => expect(result.current.sessionId).toBe("sess-1"));

    act(() => result.current.toggleMute()); // mute
    act(() => result.current.setAnswerText("answer"));
    await act(async () => {
      await result.current.handleSend();
    });
    mockSpeak.mockClear();

    act(() => result.current.toggleMute()); // unmute
    expect(mockSpeak).toHaveBeenCalledWith("Follow-up while muted.");
    expect(mockResumeSpeech).not.toHaveBeenCalled();
  });
});
