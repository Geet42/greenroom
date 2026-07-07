export default function TestResultsPanel({ testResults, revealedCount }) {
  if (!testResults) return null;

  const statusLabel = {
    accepted: "Accepted",
    wrong_answer: "Wrong Answer",
    runtime_error: "Runtime Error",
    compile_error: "Compilation Error",
  }[testResults.status] ?? testResults.status;

  const isAccepted = testResults.status === "accepted";

  return (
    <div className="mt-3 overflow-hidden rounded-lg border border-white/10 bg-ink">
      {/* Summary bar */}
      <div className={`flex items-center justify-between px-4 py-2 text-xs font-medium ${
        isAccepted ? "bg-sage/15 text-sage" : "bg-coral/15 text-coral"
      }`}>
        <span>{statusLabel}</span>
        <span className="text-mute">{testResults.passed} / {testResults.total} passed</span>
      </div>

      {/* Compile / runtime error body */}
      {testResults.compile_error && (
        <pre className="max-h-32 overflow-auto p-3 text-xs text-coral whitespace-pre-wrap">
          {testResults.compile_error}
        </pre>
      )}

      {/* Visible test cases — reveal one by one */}
      {testResults.visible_tests?.slice(0, revealedCount).map((tc) => (
        <div
          key={tc.id}
          className={`border-t border-white/5 p-3 transition-all duration-300 ${tc.passed ? "" : "bg-coral/5"}`}
        >
          <div className={`flex items-center gap-2 text-xs font-medium ${tc.passed ? "text-sage" : "text-coral"}`}>
            <span>{tc.passed ? "✓" : "✗"}</span>
            <span>{tc.label}</span>
          </div>
          <div className="mt-2 space-y-1 text-xs">
            {tc.input && (
              <p className="text-mute">
                Input: <span className="font-mono text-cream">{tc.input}</span>
              </p>
            )}
            <p className="text-mute">
              Expected: <span className="font-mono text-cream">{tc.expected}</span>
            </p>
            {tc.passed ? (
              <p className="text-mute">
                Got: <span className="font-mono text-sage">{tc.output ?? tc.expected}</span>
              </p>
            ) : (
              <p className="text-mute">
                Got: <span className="font-mono text-coral">{tc.error ?? tc.output ?? "no output"}</span>
              </p>
            )}
          </div>
        </div>
      ))}

      {/* Hidden test cases revealed after visible ones */}
      {revealedCount > (testResults.visible_tests?.length ?? 0) && testResults.hidden_tests?.length > 0 && (
        <div className="border-t border-white/5 p-3">
          <p className="mb-2 text-xs text-mute">Hidden test cases</p>
          <div className="flex flex-wrap gap-2">
            {testResults.hidden_tests.map((tc) => (
              <span
                key={tc.id}
                className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs ${
                  tc.passed ? "bg-sage/15 text-sage" : "bg-coral/15 text-coral"
                }`}
              >
                🔒 {tc.passed ? "✓" : "✗"}
              </span>
            ))}
          </div>
        </div>
      )}

      <p className="border-t border-white/5 px-3 py-2 text-xs text-white/30">
        Your code is shared with the interviewer whether or not you run tests.
      </p>
    </div>
  );
}
