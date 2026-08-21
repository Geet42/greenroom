import { lazy, Suspense, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import Navbar from "../components/Navbar";
import Waveform from "../components/Waveform";
import CodeEditor from "../components/CodeEditor";
import SystemDesignProblemPanel from "../components/SystemDesignProblemPanel";
import { useInterviewSession } from "../hooks/useInterviewSession";
import { useCodeRunner } from "../hooks/useCodeRunner";

const SystemDesignBoard = lazy(() => import("../components/SystemDesignBoard"));

const TRACK_LABELS = {
  behavioral: "Behavioral",
  technical: "Technical",
  "system-design": "System design",
};

function formatCountdown(totalSeconds) {
  const clamped = Math.max(0, totalSeconds);
  const minutes = Math.floor(clamped / 60);
  const seconds = clamped % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

function countdownColorClass(totalSeconds) {
  if (totalSeconds <= 120) return "text-coral";
  if (totalSeconds <= 600) return "text-amber";
  return "text-mute";
}

export default function Interview() {
  const [params, setParams] = useSearchParams();
  const track = params.get("track") || "behavioral";
  const resumeSessionId = params.get("session") || undefined;
  const boardRef = useRef(null);
  // System-design's side panel just needs the raw context to render tabs —
  // no boilerplate/language fetch like codeRunner does for technical, so a
  // plain setState is enough. Re-fires (and the panel re-renders) whenever a
  // new question is assigned, including via the "give me the next question"
  // mid-session flow, not just on first assignment.
  const [sdQuestionContext, setSdQuestionContext] = useState(null);

  const codeRunner = useCodeRunner();
  const session = useInterviewSession({
    track,
    boardRef,
    // Only technical/system-design sessions have a side panel that needs
    // this — wiring it unconditionally fired a wasted callback for every
    // behavioral session's first assigned question.
    onQuestionContext:
      track === "technical" ? codeRunner.handleQuestionAssigned :
      track === "system-design" ? setSdQuestionContext :
      undefined,
    resumeSessionId,
    // Stamp the session id into the URL so a page refresh resumes the same
    // interview instead of starting a brand-new one.
    onSessionIdReady: (id) => {
      if (params.get("session") !== id) {
        setParams({ track, session: id }, { replace: true });
      }
    },
  });

  // Technical/system-design want the interview panel to fill the viewport
  // exactly (editor/board + their own internal scroll areas) and STAY that
  // size as the transcript grows, on screens with room for it. That requires
  // a real, bounded height somewhere in the ancestor chain for h-full/1fr to
  // resolve against — min-h-screen alone doesn't provide one: a flex/grid
  // container whose own height comes from min-height (not height) sizes
  // itself to its content instead, so as the conversation column's message
  // list grew, its overflow-y-auto never actually engaged (nothing was
  // bounding it), and the whole row — including the editor/board column,
  // which hadn't grown at all — grew right along with it (verified: this was
  // the actual cause of the editor/canvas visibly growing over a session).
  // lg:h-screen fixes that anchor; lg:min-h-0 on every flex/grid link in the
  // chain down to the two columns stops each one from re-introducing the
  // same "size to my content" default. Each column still owns its own
  // internal overflow (transcript: overflow-y-auto; editor/board: see the
  // side column below) instead of the ancestor ever hard-clipping, so a
  // genuinely short viewport still degrades to a scrollbar, never lost
  // content — that's the lg:overflow-y-auto note by the side column, not
  // overflow-hidden, which silently clipped Excalidraw's bottom toolbar with
  // no way to reach it at all on a common 1366x768 laptop screen (verified)
  // the last time this was tried.
  //
  // All of that is a DESKTOP layout, though: the two columns collapse to
  // grid-cols-1 below lg (stacked), but grid-rows-[minmax(0,1fr)] only ever
  // defines ONE row — on mobile the second stacked section landed in an
  // auto-generated row with no real height, and Monaco/Excalidraw's own
  // height:100% collapsed to near-zero inside it (verified: a barely-visible
  // sliver of editor). Below lg, none of the fixed-height machinery applies;
  // each section gets a real min-height instead and the page just scrolls,
  // same as the "no room" desktop fallback above already does safely.
  const isFixedHeightTrack = track === "technical" || track === "system-design";

  return (
    <div className={`flex flex-col bg-stage ${isFixedHeightTrack ? "min-h-screen lg:h-screen" : "min-h-screen"}`}>
      <Navbar />
      <main className={`flex-1 ${isFixedHeightTrack ? "lg:flex lg:flex-col lg:min-h-0" : ""}`}>
        <div
          className={`mx-auto grid grid-cols-1 gap-6 px-4 py-6 sm:px-6 sm:py-8 ${
            isFixedHeightTrack
              ? "max-w-[1800px] lg:h-full lg:min-h-0 lg:grid-rows-[minmax(0,1fr)] lg:grid-cols-[380px_1fr]"
              : "max-w-6xl lg:grid-cols-[1.1fr_1fr]"
          }`}
        >

          {/* ── Conversation column ── */}
          <section
            className={`flex min-h-0 flex-col rounded-2xl border border-white/10 bg-panel ${isFixedHeightTrack ? "min-h-[70vh] lg:h-full lg:min-h-0" : ""}`}
          >
            <div className="flex items-center justify-between border-b border-white/5 px-5 py-4">
              <div className="flex items-center gap-2 text-sm text-mute">
                <span className="h-2 w-2 rounded-full bg-sage" />
                {TRACK_LABELS[track] || "Interview"} session
              </div>
              <div className="flex items-center gap-2">
                {session.remainingSeconds != null && (
                  <span
                    title="Time remaining in this session"
                    className={`font-mono text-xs tabular-nums ${countdownColorClass(session.remainingSeconds)}`}
                  >
                    ⏱ {formatCountdown(session.remainingSeconds)}
                  </span>
                )}
                <button
                  onClick={session.toggleMute}
                  title={session.isMuted ? "Unmute interviewer" : "Mute interviewer"}
                  className="rounded-full border border-white/10 px-3 py-1.5 text-xs text-mute transition hover:border-white/30 hover:text-cream"
                >
                  {session.isMuted ? "🔇 Muted" : "🔊 Mute"}
                </button>
                <button
                  onClick={session.handleEnd}
                  disabled={session.ending || !session.sessionId}
                  className="rounded-full border border-white/10 px-4 py-1.5 text-xs text-mute transition hover:border-coral/40 hover:text-coral disabled:opacity-50"
                >
                  {session.ending ? "Wrapping up..." : "End session"}
                </button>
              </div>
            </div>

            <div
              className="flex-1 min-h-0 space-y-4 overflow-y-auto px-5 py-5"
              style={isFixedHeightTrack ? undefined : { maxHeight: "55vh" }}
            >
              {session.loading && <p className="text-sm text-mute">Setting up your interviewer...</p>}
              {session.messages.map((m, i) => (
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
              {session.isSpeaking && !session.isMuted && (
                <p className="text-xs text-mute">Interviewer is speaking...</p>
              )}
              <div ref={session.transcriptEndRef} />
            </div>

            <div className="border-t border-white/5 p-5">
              {!session.isSupported && (
                <p className="mb-3 text-xs text-coral">
                  Your browser doesn't support live speech recognition. Try Chrome or Edge, or
                  type your answer below.
                </p>
              )}

              {session.sessionLocked && (
                <div className="mb-3 rounded-lg border border-amber/30 bg-amber/5 px-3 py-2 text-xs text-amber-300">
                  {session.lockMessage || "This session has ended."}
                </div>
              )}

              {session.diagramWarning && (
                <div className="mb-3 flex items-start justify-between gap-2 rounded-lg border border-amber/30 bg-amber/5 px-3 py-2 text-xs text-amber-300/80">
                  <span>{session.diagramWarning}</span>
                  <button
                    onClick={() => session.setDiagramWarning(null)}
                    className="shrink-0 text-white/40 hover:text-white/70"
                  >
                    ✕
                  </button>
                </div>
              )}

              <div className="rounded-xl border border-white/10 bg-panelLight/40 p-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs uppercase tracking-wide text-mute">Your answer</span>
                  {session.isListening && <Waveform active size="sm" />}
                </div>
                <textarea
                  value={session.answerText}
                  onChange={(e) => session.setAnswerText(e.target.value)}
                  readOnly={session.isListening}
                  disabled={session.sessionLocked}
                  placeholder={session.sessionLocked ? "Session ended, your report is on its way" : "Press the mic and speak, or type here"}
                  className="mt-2 w-full resize-none rounded-lg bg-transparent text-sm text-cream outline-none disabled:opacity-50"
                  rows={3}
                />
              </div>

              <div className="mt-4 flex items-center gap-3">
                <button
                  onClick={session.isListening ? session.stop : session.handleStartRecording}
                  disabled={!session.isSupported || session.sessionLocked}
                  className={`rounded-full px-5 py-2.5 text-sm font-medium transition ${
                    session.isListening ? "bg-coral text-ink" : "bg-amber text-ink hover:bg-amberDark"
                  } disabled:opacity-50`}
                >
                  {session.isListening ? "Stop recording" : "Record answer"}
                </button>
                {session.isSupported && !session.isListening && !session.sessionLocked && (
                  <span className="text-xs text-mute">Hold Space to record</span>
                )}
                <button
                  onClick={() => {
                    if (track !== "technical") {
                      session.handleSend({});
                      return;
                    }
                    // Only attach code that's real work and has actually
                    // changed since the last turn — see useCodeRunner's
                    // getCodeForSend for why (avoids re-embedding an
                    // unedited or already-sent code block on every message).
                    const codeToSend = codeRunner.getCodeForSend();
                    if (codeToSend !== undefined) codeRunner.markCodeSent(codeToSend);
                    session.handleSend({ code: codeToSend, language: codeRunner.language });
                  }}
                  disabled={session.sending || !session.answerText.trim() || session.sessionLocked}
                  className="rounded-full border border-white/10 px-5 py-2.5 text-sm text-cream transition hover:border-amber/40 disabled:opacity-50"
                >
                  {session.sending ? "Sending..." : "Send answer"}
                </button>
              </div>
            </div>
          </section>

          {/* ── Side column ── */}
          {/* lg:overflow-y-auto, not overflow-hidden: on a genuinely short
              viewport where the editor/board's own minimum sizing (e.g.
              SystemDesignBoard's 480px canvas floor) doesn't fit the space
              this column is given, this column scrolls to reach the rest of
              it instead of silently clipping content with no way back — the
              exact failure mode overflow-hidden caused here before. */}
          <section
            className={`min-h-0 rounded-2xl border border-white/10 bg-panel ${isFixedHeightTrack ? "min-h-[70vh] lg:h-full lg:min-h-0 lg:overflow-y-auto" : ""}`}
          >
            {track === "technical" ? (
              <CodeEditor
                language={codeRunner.language}
                code={codeRunner.code}
                setCode={codeRunner.setCode}
                running={codeRunner.running}
                slowHint={codeRunner.slowHint}
                testResults={codeRunner.testResults}
                revealedCount={codeRunner.revealedCount}
                boilerplateNote={codeRunner.boilerplateNote}
                questionContext={codeRunner.questionContext}
                onLanguageChange={(lang) => codeRunner.handleLanguageChange(lang, session.sessionId)}
                onRun={() => codeRunner.handleRunCode(session.sessionId)}
                onReset={codeRunner.handleResetBoilerplate}
              />
            ) : track === "system-design" ? (
              // LeetCode-style split, matching the technical layout: a fixed
              // problem panel on the left, the board on the right on screens
              // with room for it. Below lg, side-by-side would squeeze the
              // canvas into a sliver — stack the brief above the board instead.
              <div className="flex h-full flex-col lg:flex-row">
                <div className="max-h-[45vh] shrink-0 overflow-y-auto border-b border-white/5 lg:h-full lg:max-h-none lg:w-[38%] lg:min-w-[320px] lg:max-w-[480px] lg:border-b-0 lg:border-r">
                  <SystemDesignProblemPanel questionContext={sdQuestionContext} />
                </div>
                <div className="min-h-[420px] min-w-0 flex-1">
                  <Suspense fallback={<div className="p-6 text-sm text-mute">Loading board…</div>}>
                    <SystemDesignBoard
                      ref={boardRef}
                      initialElements={session.initialDiagramElements}
                      onSave={session.saveDiagram}
                    />
                  </Suspense>
                </div>
              </div>
            ) : (
  <div className="flex h-full flex-col p-6">
    <h2 className="font-display text-xl">During this session</h2>
    <p className="mt-1 text-xs text-mute">Tips to get the most out of your practice</p>

    <div className="mt-6 space-y-3">
      <div className="rounded-xl border border-white/5 bg-panelLight/40 p-4">
        <p className="text-sm font-medium text-cream">🎙 Speak naturally</p>
        <p className="mt-1 text-xs text-mute">The interviewer responds to what you actually say, no scripted replies.</p>
      </div>
      <div className="rounded-xl border border-white/5 bg-panelLight/40 p-4">
        <p className="text-sm font-medium text-cream">⏸ Pause when you need to</p>
        <p className="mt-1 text-xs text-mute">There's no penalty for taking a breath before answering.</p>
      </div>
      <div className="rounded-xl border border-white/5 bg-panelLight/40 p-4">
        <p className="text-sm font-medium text-cream">⭐ Use the STAR method</p>
        <p className="mt-1 text-xs text-mute">Structure your answers (Situation, Task, Action, Result) for clearer storytelling.</p>
      </div>
      <div className="rounded-xl border border-white/5 bg-panelLight/40 p-4">
        <p className="text-sm font-medium text-cream">🏁 End when you're ready</p>
        <p className="mt-1 text-xs text-mute">Hit "End session" whenever you want your full feedback report.</p>
      </div>
    </div>

    <div className="mt-auto pt-6">
      <div className="rounded-xl border border-amber/20 bg-amber/5 p-4">
        <p className="text-xs font-medium text-amber">Reminder</p>
        <p className="mt-1 text-xs text-mute">Your session is being recorded for feedback. Be as detailed as you would in a real interview.</p>
      </div>
    </div>
  </div>
)}
          </section>

        </div>
      </main>
    </div>
  );
}
