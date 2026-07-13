import Editor from "@monaco-editor/react";
import TestResultsPanel from "./TestResultsPanel";

const LANGUAGES = [
  { id: "python",     label: "Python",     monaco: "python",     piston: "python", version: "3.10.0"  },
  { id: "javascript", label: "JavaScript", monaco: "javascript", piston: "node",   version: "18.15.0" },
  { id: "java",       label: "Java",       monaco: "java",       piston: "java",   version: "15.0.2"  },
  { id: "cpp",        label: "C++",        monaco: "cpp",        piston: "gcc",    version: "10.2.0"  },
];

export { LANGUAGES };

export default function CodeEditor({
  language,
  code,
  setCode,
  running,
  slowHint,
  testResults,
  revealedCount,
  boilerplateNote,
  questionContext,
  onLanguageChange,
  onRun,
  onReset,
}) {
  const lang = LANGUAGES.find((l) => l.id === language);

  return (
    <div className="flex h-full flex-col">
      {/* Header: label + language selector */}
      <div className="flex items-center justify-between border-b border-white/5 px-5 py-4">
        <span className="text-sm text-mute">Code editor</span>
        <div className="flex items-center gap-2">
          <button
            onClick={onReset}
            disabled={running}
            title="Reset to original boilerplate"
            className="rounded-lg border border-white/10 px-3 py-1.5 text-xs text-mute transition hover:border-white/30 hover:text-cream disabled:opacity-50"
          >
            ↺ Reset
          </button>
          <select
            value={language}
            onChange={(e) => onLanguageChange(e.target.value)}
            className="rounded-lg border border-white/10 bg-panelLight px-3 py-1.5 text-xs text-cream"
          >
            {LANGUAGES.map((l) => (
              <option key={l.id} value={l.id}>{l.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Constraints (shown once question is assigned) */}
      {questionContext?.constraints?.length > 0 && (
        <div className="border-b border-white/5 px-5 py-3">
          <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-mute">Constraints</p>
          <ul className="space-y-0.5">
            {questionContext.constraints.map((c, i) => (
              <li key={i} className="font-mono text-xs text-cream/70">{c}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Language not supported note */}
      {boilerplateNote && (
        <p className="border-b border-white/5 px-5 py-2 text-xs text-amber-300/80">{boilerplateNote}</p>
      )}

      {/* Monaco editor */}
      <div className="flex-1">
        <Editor
          height="320px"
          theme="vs-dark"
          language={lang.monaco}
          value={code}
          onChange={(value) => setCode(value ?? "")}
          options={{
            fontSize: 13,
            minimap: { enabled: false },
            quickSuggestions: true,
            suggestOnTriggerCharacters: true,
            wordBasedSuggestions: "currentDocument",
            tabCompletion: "on",
          }}
        />
      </div>

      {/* Run button + results */}
      <div className="border-t border-white/5 p-4">
        <button
          onClick={onRun}
          disabled={running}
          className="rounded-full bg-sage px-5 py-2 text-sm font-medium text-ink transition hover:opacity-90 disabled:opacity-50"
        >
          {running ? (
            <span className="flex items-center gap-2">
              <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-ink border-t-transparent" />
              Running…
            </span>
          ) : "Run code"}
        </button>

        {running && slowHint && (
          <p className="mt-3 text-xs text-white/50">
            Preparing a verified test environment for this language — first run on a
            new problem can take up to a minute. Future runs will be instant.
          </p>
        )}

        {running && (
          <div className="mt-3 space-y-2">
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-8 animate-pulse rounded-lg bg-white/5" />
            ))}
          </div>
        )}

        {!running && <TestResultsPanel testResults={testResults} revealedCount={revealedCount} />}
      </div>
    </div>
  );
}
