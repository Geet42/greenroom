import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import Editor from "@monaco-editor/react";
import Navbar from "../components/Navbar";
import Waveform from "../components/Waveform";
import { api } from "../lib/api";
import { supabase } from "../lib/supabaseClient";
import { useSpeechRecognition } from "../hooks/useSpeechRecognition";
import { useSpeechSynthesis } from "../hooks/useSpeechSynthesis";

const TRACK_LABELS = {
  behavioral: "Behavioral",
  technical: "Technical",
  "system-design": "System design"
};

const LANGUAGES = [
  { id: "python", label: "Python", monaco: "python", piston: "python", version: "3.10.0" },
  { id: "javascript", label: "JavaScript", monaco: "javascript", piston: "javascript", version: "18.15.0" },
  { id: "java", label: "Java", monaco: "java", piston: "java", version: "15.0.2" },
  { id: "cpp", label: "C++", monaco: "cpp", piston: "cpp", version: "10.2.0" }
];

const STARTER_CODE = {
  python: "def solution():\n    pass\n",
  javascript: "function solution() {\n\n}\n",
  java: "class Solution {\n    public static void main(String[] args) {\n\n    }\n}\n",
  cpp: "#include <iostream>\nusing namespace std;\n\nint main() {\n\n    return 0;\n}\n"
};

export default function Interview() {
  const [params] = useSearchParams();
  const track = params.get("track") || "behavioral";
  const navigate = useNavigate();

  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [ending, setEnding] = useState(false);

  const [language, setLanguage] = useState("python");
  const [code, setCode] = useState(STARTER_CODE.python);
  const [codeOutput, setCodeOutput] = useState(null);
  const [running, setRunning] = useState(false);

  const { isSupported, isListening, transcript, interimTranscript, start, stop, reset } =
    useSpeechRecognition();
  const { isSpeaking, speak } = useSpeechSynthesis();

  const [answerText, setAnswerText] = useState("");
  const transcriptEndRef = useRef(null);

  useEffect(() => {
    if (isListening) {
      setAnswerText(`${transcript} ${interimTranscript}`.trim());
    }
  }, [isListening, transcript, interimTranscript]);

  const handleStartRecording = () => {
    setAnswerText("");
    reset();
    start();
  };

  useEffect(() => {
    async function init() {
      try {
        const { data: userData } = await supabase.auth.getUser();
        const res = await api.startSession({
          track,
          role: "Software Engineer",
          user_id: userData?.user?.id
        });
        setSessionId(res.session_id);
        setMessages([{ role: "interviewer", text: res.question }]);
        speak(res.question);
      } catch (err) {
        setMessages([
          {
            role: "interviewer",
            text:
              "I couldn't reach the interview backend. Make sure the API server is running and try again."
          }
        ]);
      } finally {
        setLoading(false);
      }
    }
    init();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    const answer = answerText.trim();
    if (!answer || !sessionId) return;

    setMessages((prev) => [...prev, { role: "candidate", text: answer }]);
    setAnswerText("");
    reset();
    setSending(true);

    try {
      const res = await api.sendMessage({
        session_id: sessionId,
        message: answer,
        code: track === "technical" ? code : undefined,
        language: track === "technical" ? language : undefined
      });

      setMessages((prev) => [...prev, { role: "interviewer", text: res.question }]);
      speak(res.question);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "interviewer", text: "Hmm, I lost connection there. Could you say that again?" }
      ]);
    } finally {
      setSending(false);
    }
  };

  const handleRunCode = async () => {
    setRunning(true);
    setCodeOutput(null);
    const lang = LANGUAGES.find((l) => l.id === language);
    try {
      const res = await api.runCode({
        language: lang.piston,
        version: lang.version,
        source: code
      });
      setCodeOutput(res);
    } catch {
      setCodeOutput({ run: { stdout: "", stderr: "Could not reach the code execution service." } });
    } finally {
      setRunning(false);
    }
  };

  const handleEnd = async () => {
    if (!sessionId) return;
    setEnding(true);
    try {
      await api.endSession({ session_id: sessionId });
    } catch {
      // still navigate, results page will show what it can
    }
    navigate(`/results/${sessionId}`);
  };

  return (
    <div className="flex min-h-screen flex-col bg-stage">
      <Navbar />
      <main className="flex-1">
        <div className="mx-auto grid max-w-6xl grid-cols-1 gap-6 px-6 py-8 lg:grid-cols-[1.1fr_1fr]">
          {/* Conversation column */}
          <section className="flex flex-col rounded-2xl border border-white/10 bg-panel">
            <div className="flex items-center justify-between border-b border-white/5 px-5 py-4">
              <div className="flex items-center gap-2 text-sm text-mute">
                <span className="h-2 w-2 rounded-full bg-sage" />
                {TRACK_LABELS[track] || "Interview"} session
              </div>
              <button
                onClick={handleEnd}
                disabled={ending || !sessionId}
                className="rounded-full border border-white/10 px-4 py-1.5 text-xs text-mute transition hover:border-coral/40 hover:text-coral disabled:opacity-50"
              >
                {ending ? "Wrapping up..." : "End session"}
              </button>
            </div>

            <div className="flex-1 space-y-4 overflow-y-auto px-5 py-5" style={{ maxHeight: "55vh" }}>
              {loading && <p className="text-sm text-mute">Setting up your interviewer...</p>}
              {messages.map((m, i) => (
                <div
                  key={i}
                  className={
                    m.role === "interviewer"
                      ? "rounded-xl bg-panelLight/60 p-4 text-sm"
                      : "rounded-xl border border-amber/20 bg-amber/5 p-4 text-sm"
                  }
                >
                  <p className={`font-display ${m.role === "interviewer" ? "text-cream" : "text-amber"}`}>
                    {m.role === "interviewer" ? "Interviewer" : "You"}
                  </p>
                  <p className="mt-1 text-cream/90">{m.text}</p>
                </div>
              ))}
              {isSpeaking && (
                <p className="text-xs text-mute">Interviewer is speaking...</p>
              )}
              <div ref={transcriptEndRef} />
            </div>

            <div className="border-t border-white/5 p-5">
              {!isSupported && (
                <p className="mb-3 text-xs text-coral">
                  Your browser doesn't support live speech recognition. Try Chrome or Edge, or
                  type your answer below.
                </p>
              )}

              <div className="rounded-xl border border-white/10 bg-panelLight/40 p-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs uppercase tracking-wide text-mute">Your answer</span>
                  {isListening && <Waveform active size="sm" />}
                </div>
                <textarea
                  value={answerText}
                  onChange={(e) => setAnswerText(e.target.value)}
                  readOnly={isListening}
                  placeholder="Press the mic and speak, or type here"
                  className="mt-2 w-full resize-none rounded-lg bg-transparent text-sm text-cream outline-none"
                  rows={3}
                />
              </div>

              <div className="mt-4 flex items-center gap-3">
                <button
                  onClick={isListening ? stop : handleStartRecording}
                  disabled={!isSupported}
                  className={`rounded-full px-5 py-2.5 text-sm font-medium transition ${
                    isListening
                      ? "bg-coral text-ink"
                      : "bg-amber text-ink hover:bg-amberDark"
                  } disabled:opacity-50`}
                >
                  {isListening ? "Stop recording" : "Record answer"}
                </button>
                <button
                  onClick={handleSend}
                  disabled={sending || !answerText.trim()}
                  className="rounded-full border border-white/10 px-5 py-2.5 text-sm text-cream transition hover:border-amber/40 disabled:opacity-50"
                >
                  {sending ? "Sending..." : "Send answer"}
                </button>
              </div>
            </div>
          </section>

          {/* Side column: code editor for technical, or prep notes */}
          <section className="rounded-2xl border border-white/10 bg-panel">
            {track === "technical" ? (
              <div className="flex h-full flex-col">
                <div className="flex items-center justify-between border-b border-white/5 px-5 py-4">
                  <span className="text-sm text-mute">Code editor</span>
                  <select
                    value={language}
                    onChange={(e) => {
                      setLanguage(e.target.value);
                      setCode(STARTER_CODE[e.target.value]);
                      setCodeOutput(null);
                    }}
                    className="rounded-lg border border-white/10 bg-panelLight px-3 py-1.5 text-xs text-cream"
                  >
                    {LANGUAGES.map((l) => (
                      <option key={l.id} value={l.id}>
                        {l.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="flex-1">
                  <Editor
                    height="320px"
                    theme="vs-dark"
                    language={LANGUAGES.find((l) => l.id === language).monaco}
                    value={code}
                    onChange={(value) => setCode(value ?? "")}
                    options={{ fontSize: 13, minimap: { enabled: false } }}
                  />
                </div>
                <div className="border-t border-white/5 p-4">
                  <button
                    onClick={handleRunCode}
                    disabled={running}
                    className="rounded-full bg-sage px-5 py-2 text-sm font-medium text-ink transition hover:opacity-90 disabled:opacity-50"
                  >
                    {running ? "Running..." : "Run code"}
                  </button>
                  {codeOutput && (
                    <pre className="mt-3 max-h-40 overflow-auto rounded-lg bg-ink p-3 text-xs text-mute">
{codeOutput.run?.stdout || ""}
{codeOutput.run?.stderr ? `\n${codeOutput.run.stderr}` : ""}
                    </pre>
                  )}
                </div>
              </div>
            ) : (
              <div className="p-6">
                <h2 className="font-display text-xl">During this session</h2>
                <ul className="mt-4 space-y-3 text-sm text-mute">
                  <li>Speak naturally. The interviewer responds to what you actually say.</li>
                  <li>Take a breath before answering. There's no penalty for a pause.</li>
                  <li>End the session whenever you're ready for your feedback report.</li>
                </ul>
              </div>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}
