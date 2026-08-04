import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { supabase } from "../lib/supabaseClient";
import { useSpeechRecognition } from "./useSpeechRecognition";
import { useSpeechSynthesis } from "./useSpeechSynthesis";

function generateBoardDescription(elements) {
  if (!elements || elements.length === 0) return null;
  const labelOf = {};
  elements.forEach((el) => {
    if (el.type === "text" && el.containerId)
      labelOf[el.containerId] = (labelOf[el.containerId] || "") + el.text?.trim();
  });
  elements.forEach((el) => {
    if (el.type === "text" && !el.containerId && el.text?.trim())
      labelOf[el.id] = el.text.trim();
  });
  const shapeTypes = new Set(["rectangle", "ellipse", "diamond", "triangle", "trapezoid", "parallelogram"]);
  const components = elements
    .filter((el) => shapeTypes.has(el.type))
    .map((el) => labelOf[el.id] || el.type)
    .filter(Boolean);
  const connections = elements
    .filter((el) => el.type === "arrow" && el.startBinding?.elementId && el.endBinding?.elementId)
    .map((el) => {
      const from = labelOf[el.startBinding.elementId] || "node";
      const to   = labelOf[el.endBinding.elementId]   || "node";
      const via  = labelOf[el.id];
      return via ? `${from} --[${via}]--> ${to}` : `${from} → ${to}`;
    });
  if (components.length === 0 && connections.length === 0) return null;
  const parts = ["[Architecture diagram]"];
  if (components.length) parts.push(`Components: ${components.join(", ")}`);
  if (connections.length) parts.push(`Connections: ${connections.join(", ")}`);
  return parts.join("\n");
}

function isDiagramMeaningful(elements) {
  const shapeTypes = new Set(["rectangle", "ellipse", "diamond", "triangle", "trapezoid", "parallelogram"]);
  const shapes = elements.filter((el) => shapeTypes.has(el.type));
  const arrows = elements.filter(
    (el) => el.type === "arrow" && el.startBinding?.elementId && el.endBinding?.elementId
  );
  return shapes.length >= 2 && arrows.length >= 1;
}

/**
 * Manages interview session lifecycle: init, send message, end.
 *
 * @param track         interview track ("behavioral" | "technical" | "system-design")
 * @param boardRef      ref to the SystemDesignBoard, used to read diagram elements
 * @param onQuestionContext  called with (QuestionContext, sessionId) when the problem is first assigned
 */
export function useInterviewSession({ track, boardRef, onQuestionContext, resumeSessionId, onSessionIdReady }) {
  const navigate = useNavigate();

  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [ending, setEnding] = useState(false);
  const [answerText, setAnswerText] = useState("");
  const [diagramWarning, setDiagramWarning] = useState(null);
  const [sessionFull, setSessionFull] = useState(false);
  const [initialDiagramElements, setInitialDiagramElements] = useState(null);

  const transcriptEndRef = useRef(null);
  const initDoneRef = useRef(false);
  const newMessageWhileMutedRef = useRef(false);
  const recordingBaseTextRef = useRef("");
  const spaceRecordingRef = useRef(false);

  const { isSupported, isListening, transcript, interimTranscript, start, stop, reset } =
    useSpeechRecognition();
  const { isSpeaking, speak, stop: stopSpeech, pause: pauseSpeech, resume: resumeSpeech } = useSpeechSynthesis();
  const [isMuted, setIsMuted] = useState(false);
  const isMutedRef = useRef(false);
  const lastInterviewerTextRef = useRef(null);

  useEffect(() => () => stopSpeech(), [stopSpeech]);

  const speakIfUnmuted = useCallback((text) => {
    lastInterviewerTextRef.current = text;
    if (isMutedRef.current) {
      stopSpeech(); // discard old paused audio — new content supersedes it
      newMessageWhileMutedRef.current = true;
    } else {
      newMessageWhileMutedRef.current = false;
      speak(text);
    }
  }, [speak, stopSpeech]);

  useEffect(() => {
    if (isListening) {
      const base = recordingBaseTextRef.current;
      const dictated = `${transcript} ${interimTranscript}`.trim();
      setAnswerText(dictated ? `${base} ${dictated}`.trim() : base);
    }
  }, [isListening, transcript, interimTranscript]);

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (initDoneRef.current) return;
    initDoneRef.current = true;
    async function init() {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (!session) { navigate("/login", { replace: true }); return; }

        if (resumeSessionId) {
          try {
            const resumed = await api.resumeSession(resumeSessionId);
            setSessionId(resumed.session_id);
            setMessages(resumed.history.map((m) => ({
              role: m.role === "candidate" ? "candidate" : "interviewer",
              text: m.content,
            })));
            const lastInterviewer = [...resumed.history].reverse().find((m) => m.role === "interviewer");
            if (lastInterviewer) lastInterviewerTextRef.current = lastInterviewer.content;
            if (resumed.question_context && onQuestionContext) {
              onQuestionContext(resumed.question_context, resumed.session_id);
            }
            if (resumed.diagram_elements?.length) {
              setInitialDiagramElements(resumed.diagram_elements);
            }
            onSessionIdReady?.(resumed.session_id);
            return;
          } catch {
            // Resume failed (session gone/completed/backend restarted) — fall
            // through to starting a fresh session below.
          }
        }

        const jd = sessionStorage.getItem("interview_jd") || undefined;
        sessionStorage.removeItem("interview_jd");
        const res = await api.startSession({ track, role: "Software Engineer", job_description: jd });
        setSessionId(res.session_id);
        setMessages([{ role: "interviewer", text: res.question }]);
        speakIfUnmuted(res.question);
        api.trackEvent("session_start", { sessionId: res.session_id, properties: { track } });
        onSessionIdReady?.(res.session_id);
      } catch (err) {
        if (err.message?.includes("401") || err.message?.includes("403")) {
          navigate("/login", { replace: true }); return;
        }
        if (err.message?.includes("429")) {
          setMessages([{ role: "interviewer", text: "You have too many active sessions. Please end an existing session from your dashboard and try again." }]);
          return;
        }
        setMessages([{ role: "interviewer", text: "I couldn't reach the interview backend. Make sure the API server is running and try again." }]);
      } finally {
        setLoading(false);
      }
    }
    init();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Preserves any manually typed text as a base and appends dictation after
  // it, instead of wiping the textarea when recording starts.
  const handleStartRecording = useCallback(() => {
    recordingBaseTextRef.current = answerText.trim();
    reset();
    start();
  }, [answerText, reset, start]);

  const handleStopRecording = useCallback(() => {
    stop();
  }, [stop]);

  // Spacebar push-to-talk: hold to record, release to stop.
  // Once we've started recording via the spacebar, keyup always stops it —
  // regardless of what element has focus by the time the key is released —
  // so a focus change mid-hold (e.g. the code editor grabbing focus) can't
  // strand recording on forever.
  useEffect(() => {
    const onKeyDown = (e) => {
      if (e.code !== "Space" || e.repeat) return;
      const active = document.activeElement;
      const tag = active?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      // Monaco's actual contenteditable/textarea target doesn't always match
      // activeElement's tag (it can sit on the outer .monaco-editor container,
      // e.g. right after mount) — check by ancestry instead of exact tag.
      if (active?.closest?.(".monaco-editor")) return;
      e.preventDefault();
      if (!isListening && isSupported) {
        spaceRecordingRef.current = true;
        handleStartRecording();
      }
    };
    const onKeyUp = (e) => {
      if (e.code !== "Space") return;
      if (spaceRecordingRef.current) {
        spaceRecordingRef.current = false;
        handleStopRecording();
      }
    };
    // Safety net: if the window loses focus while Space is held (alt-tab,
    // a permission prompt, devtools), the keyup event can be lost entirely.
    const onBlur = () => {
      if (spaceRecordingRef.current) {
        spaceRecordingRef.current = false;
        handleStopRecording();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);
    window.addEventListener("blur", onBlur);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
      window.removeEventListener("blur", onBlur);
    };
  }, [isListening, isSupported, handleStartRecording, handleStopRecording]);

  /**
   * Send a candidate message.
   * @param {{ code?: string, language?: string }} extras  pass code/language for technical track
   */
  const handleSend = async (extras = {}) => {
    const answer = answerText.trim();
    if (!answer || !sessionId) return;
    if (isListening) stop();

    let messageToSend = answer;
    if (track === "system-design" && boardRef?.current) {
      const elements = boardRef.current.getElements();
      if (elements.length > 0 && !isDiagramMeaningful(elements)) {
        setDiagramWarning(
          "Your diagram has fewer than 2 connected components. Add more structure, or dismiss this warning to send anyway."
        );
        return;
      }
      setDiagramWarning(null);
      const desc = generateBoardDescription(elements);
      if (desc) messageToSend = `${answer}\n\n${desc}`;
    }

    setMessages((prev) => [...prev, { role: "candidate", text: answer }]);
    setAnswerText("");
    recordingBaseTextRef.current = "";
    reset();
    setSending(true);

    try {
      const res = await api.sendMessage({
        session_id: sessionId,
        message: messageToSend,
        code: extras.code,
        language: extras.language,
      });
      setMessages((prev) => [...prev, { role: "interviewer", text: res.question }]);
      speakIfUnmuted(res.question);
      if (res.question_context && onQuestionContext) onQuestionContext(res.question_context, sessionId);
      if (res.done) setSessionFull(true);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "interviewer", text: "Hmm, I lost connection there. Could you say that again?" },
      ]);
    } finally {
      setSending(false);
    }
  };

  // Debounced-by-caller autosave for the system-design board — best-effort,
  // never surfaced to the candidate if it fails (a missed autosave isn't
  // worth interrupting the interview over).
  const saveDiagram = useCallback((elements) => {
    if (!sessionId) return;
    api.saveDiagram({ session_id: sessionId, elements }).catch(() => {});
  }, [sessionId]);

  const handleEnd = async () => {
    if (!sessionId || ending) return;
    setEnding(true);
    stopSpeech();
    stop();
    try {
      await api.endSession({ session_id: sessionId });
      api.trackEvent("session_end", { sessionId, properties: { track } });
      navigate(`/results/${sessionId}`);
    } catch (err) {
      console.error("End session failed:", err);
      setEnding(false);
      setMessages((prev) => [
        ...prev,
        { role: "interviewer", text: "I had trouble generating your report. Please try ending the session again." },
      ]);
    }
  };

  const toggleMute = () => {
    const nowMuted = !isMuted;
    isMutedRef.current = nowMuted;
    setIsMuted(nowMuted);
    if (nowMuted) {
      pauseSpeech();
    } else {
      if (newMessageWhileMutedRef.current && lastInterviewerTextRef.current) {
        // new response arrived while muted — speak it fresh
        newMessageWhileMutedRef.current = false;
        speak(lastInterviewerTextRef.current);
      } else {
        // no new message — resume from where we paused
        resumeSpeech();
      }
    }
  };

  return {
    sessionId,
    messages,
    loading,
    sending,
    ending,
    answerText,
    setAnswerText,
    transcriptEndRef,
    isSupported,
    isListening,
    isSpeaking,
    isMuted,
    diagramWarning,
    setDiagramWarning,
    sessionFull,
    initialDiagramElements,
    saveDiagram,
    handleStartRecording,
    handleSend,
    handleEnd,
    toggleMute,
    stop,
  };
}
