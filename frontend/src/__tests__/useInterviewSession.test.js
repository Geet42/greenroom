import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

const { mockNavigate, mockSpeak, mockStopSpeech, mockPauseSpeech, mockResumeSpeech, mockStart, mockStop, mockReset } =
  vi.hoisted(() => ({
    mockNavigate: vi.fn(),
    mockSpeak: vi.fn(),
    mockStopSpeech: vi.fn(),
    mockPauseSpeech: vi.fn(),
    mockResumeSpeech: vi.fn(),
    mockStart: vi.fn(),
    mockStop: vi.fn(),
    mockReset: vi.fn(),
  }));

vi.mock("react-router-dom", () => ({
  useNavigate: () => mockNavigate,
}));

vi.mock("../lib/api", () => ({
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

import { api } from "../lib/api";
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
    api.startSession.mockRejectedValue(new Error("API error 401: unauthorized"));
    renderHook(() => useInterviewSession({ track: "behavioral" }));

    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith("/login", { replace: true }));
  });

  it("shows a friendly message when starting a session returns 429 (too many active sessions)", async () => {
    api.startSession.mockRejectedValue(new Error("API error 429: too many requests"));
    const { result } = renderHook(() => useInterviewSession({ track: "behavioral" }));

    await waitFor(() =>
      expect(result.current.messages[0]?.text).toMatch(/too many active sessions/i)
    );
  });
});

describe("useInterviewSession — handleSend", () => {
  async function setUpStartedSession() {
    api.startSession.mockResolvedValue({ session_id: "sess-1", track: "behavioral", question: "Q1" });
    const { result } = renderHook(() => useInterviewSession({ track: "behavioral" }));
    await waitFor(() => expect(result.current.sessionId).toBe("sess-1"));
    return result;
  }

  it("sends the candidate's answer and appends the interviewer's reply", async () => {
    const result = await setUpStartedSession();
    api.sendMessage.mockResolvedValue({ question: "Tell me more.", done: false });

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
    api.sendMessage.mockResolvedValue({ question: "Follow-up while muted.", done: false });
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
