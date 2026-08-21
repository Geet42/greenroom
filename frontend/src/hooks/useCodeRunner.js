import { useRef, useState } from "react";
import { api } from "../lib/api";
import { LANGUAGES } from "../components/CodeEditor";

export const STARTER_CODE = {
  python: `from collections import defaultdict, Counter, deque
import heapq
from typing import List, Optional, Tuple

# Write your solution here
`,
  javascript: `// Write your solution here
`,
  java: `import java.util.*;
import java.util.stream.*;

class Solution {
    // Write your solution here
}
`,
  cpp: `#include <bits/stdc++.h>
using namespace std;

// Write your solution here
`,
};

export function useCodeRunner() {
  const [language, setLanguage] = useState("python");
  const [code, setCode] = useState(STARTER_CODE.python);
  const [testResults, setTestResults] = useState(null);
  const [revealedCount, setRevealedCount] = useState(0);
  const [running, setRunning] = useState(false);
  const [slowHint, setSlowHint] = useState(false);
  const [boilerplateNote, setBoilerplateNote] = useState(null);
  const [questionContext, setQuestionContext] = useState(null);
  const boilerplateRequestRef = useRef(0);
  // Tracks the last-known-original source per language, so the reset button
  // can restore it without refetching (starter code, or fetched harness boilerplate).
  const originalCodeRef = useRef({ python: STARTER_CODE.python });
  // The code actually embedded in the transcript on the last send, per
  // language — a message is only attached with a code block when the
  // candidate's code is both real (not just the untouched starter/boilerplate)
  // and different from what was already sent, so an unedited or unchanged
  // editor doesn't re-embed an identical code block on every single turn.
  const lastSentCodeRef = useRef({});

  // Fetches question-specific boilerplate for `langId` and swaps it in if found.
  // Shared by language switching and by the question-assigned handler below,
  // since Python is the default language and never goes through a "switch".
  const fetchBoilerplate = async (langId, sessionId) => {
    const lang = LANGUAGES.find((l) => l.id === langId);
    if (!sessionId) return;

    const requestId = ++boilerplateRequestRef.current;
    try {
      const res = await api.getBoilerplate(sessionId, lang.piston);
      if (boilerplateRequestRef.current !== requestId) return;
      if (res.boilerplate) {
        setCode(res.boilerplate);
        originalCodeRef.current[langId] = res.boilerplate;
      }
      // If !res.supported, silently keep the default starter code.
      // The test runner will show a specific error if the user tries to run.
    } catch {
      // Generic starter code already showing — silently keep it.
    }
  };

  // sessionId is passed per-call so the hook doesn't need it at construction time
  const handleLanguageChange = async (newLanguage, sessionId) => {
    setLanguage(newLanguage);
    // If we've already fetched question-specific boilerplate for this
    // language before, show it immediately instead of flashing the generic
    // starter — and don't stomp the cache, or switching away and back loses
    // the real boilerplate for good.
    const cached = originalCodeRef.current[newLanguage];
    if (cached !== undefined) {
      setCode(cached);
    } else {
      setCode(STARTER_CODE[newLanguage]);
      originalCodeRef.current[newLanguage] = STARTER_CODE[newLanguage];
    }
    setTestResults(null);
    setRevealedCount(0);
    setBoilerplateNote(null);
    await fetchBoilerplate(newLanguage, sessionId);
  };

  // Called whenever a technical question is (re)assigned — the first
  // question at session start, or a candidate-requested switch to a
  // different one mid-session (see guardrail.candidate_requests_new_problem
  // on the backend). Every previously-cached boilerplate belongs to the OLD
  // question once this fires, so the whole cache (not just the current
  // language) gets invalidated, and the editor/test results reset to a clean
  // slate before fetching the new question's real boilerplate — otherwise a
  // question switch left the old question's code and test results on screen
  // under the new question's title.
  const handleQuestionAssigned = (ctx, sessionId) => {
    setQuestionContext(ctx);
    originalCodeRef.current = { [language]: STARTER_CODE[language] };
    lastSentCodeRef.current = {};
    setCode(STARTER_CODE[language]);
    setTestResults(null);
    setRevealedCount(0);
    setBoilerplateNote(null);
    fetchBoilerplate(language, sessionId);
  };

  const handleResetBoilerplate = () => {
    const original = originalCodeRef.current[language];
    if (original === undefined) return;
    setCode(original);
    setTestResults(null);
    setRevealedCount(0);
  };

  // Returns the code to attach to the next sent message, or undefined if it
  // shouldn't be attached at all: still just the untouched starter/boilerplate
  // (no real candidate work yet), or identical to what was already sent for
  // this language. Call markCodeSent() after a successful send to record it.
  const getCodeForSend = () => {
    const original = originalCodeRef.current[language];
    if (code === original) return undefined; // untouched boilerplate — nothing to show
    if (code === lastSentCodeRef.current[language]) return undefined; // unchanged since last send
    return code;
  };

  const markCodeSent = (sentCode) => {
    lastSentCodeRef.current[language] = sentCode;
  };

  const handleRunCode = async (sessionId) => {
    if (!sessionId) return;
    const lang = LANGUAGES.find((l) => l.id === language);
    api.trackEvent("code_run", { sessionId, properties: { language: lang.id } });
    setRunning(true);
    setTestResults(null);
    setRevealedCount(0);
    setSlowHint(false);

    const slowHintTimer =
      lang.id === "java" || lang.id === "cpp" ? setTimeout(() => setSlowHint(true), 5000) : null;

    try {
      const res = await api.runTests({
        session_id: sessionId,
        language: lang.piston,
        version: lang.version,
        source: code,
      });
      setTestResults(res);
      const visibleLen = res.visible_tests?.length ?? 0;
      const hiddenLen  = res.hidden_tests?.length ?? 0;
      for (let i = 1; i <= visibleLen + (hiddenLen > 0 ? 1 : 0); i++) {
        setTimeout(() => setRevealedCount(i), i * 300);
      }
    } catch {
      // total: 0, not a guessed test count — this is a network failure, not
      // a real result, so "0 / 7 passed" would misleadingly imply 7 tests
      // actually ran and failed.
      setTestResults({
        status: "compile_error",
        compile_error: "Could not reach the code execution service.",
        visible_tests: [],
        hidden_tests: [],
        passed: 0,
        total: 0,
      });
    } finally {
      if (slowHintTimer) clearTimeout(slowHintTimer);
      setSlowHint(false);
      setRunning(false);
    }
  };

  return {
    language,
    code,
    setCode,
    testResults,
    revealedCount,
    running,
    slowHint,
    boilerplateNote,
    questionContext,
    setQuestionContext,
    handleLanguageChange,
    handleQuestionAssigned,
    handleRunCode,
    handleResetBoilerplate,
    getCodeForSend,
    markCodeSent,
  };
}
