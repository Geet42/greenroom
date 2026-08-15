const STATUS_META = {
  accepted: { label: "Accepted", icon: "✓", className: "text-sage bg-sage/10 border-sage/30", iconBg: "bg-sage/20" },
  wrong_answer: { label: "Wrong Answer", icon: "✗", className: "text-coral bg-coral/10 border-coral/30", iconBg: "bg-coral/20" },
  runtime_error: { label: "Runtime Error", icon: "!", className: "text-coral bg-coral/10 border-coral/30", iconBg: "bg-coral/20" },
  compile_error: { label: "Compilation Error", icon: "!", className: "text-coral bg-coral/10 border-coral/30", iconBg: "bg-coral/20" },
};

// A labeled monospace block for one field of a test case (input/expected/
// got) — LeetCode's console renders each as its own boxed row rather than
// inline text, which is far easier to scan when values are long.
function CodeField({ label, value, tone = "cream" }) {
  const toneClass = { cream: "text-cream", sage: "text-sage", coral: "text-coral" }[tone];
  return (
    <div>
      <p className="text-[11px] font-medium uppercase tracking-wide text-mute">{label}</p>
      <pre className={`mt-1 overflow-x-auto rounded-lg border border-white/5 bg-black/30 px-3 py-2 font-mono text-xs ${toneClass}`}>
        {value}
      </pre>
    </div>
  );
}

export default function TestResultsPanel({ testResults, revealedCount }) {
  if (!testResults) return null;

  const meta = STATUS_META[testResults.status] ?? { label: testResults.status, icon: "•", className: "text-mute bg-white/5 border-white/10", iconBg: "bg-white/10" };
  const isAccepted = testResults.status === "accepted";
  const passRate = testResults.total > 0 ? Math.round((testResults.passed / testResults.total) * 100) : 0;

  return (
    <div className="overflow-hidden rounded-xl border border-white/10 bg-ink shadow-lg">
      {/* Summary bar */}
      <div className={`flex items-center justify-between border-b px-4 py-3 ${meta.className}`}>
        <span className="flex items-center gap-2 text-sm font-semibold">
          <span className={`flex h-5 w-5 items-center justify-center rounded-full text-xs ${meta.iconBg}`}>{meta.icon}</span>
          {meta.label}
        </span>
        <div className="flex items-center gap-2">
          <div className="h-1.5 w-20 overflow-hidden rounded-full bg-white/10">
            <div
              className={`h-full rounded-full ${isAccepted ? "bg-sage" : "bg-coral"} transition-all duration-500`}
              style={{ width: `${passRate}%` }}
            />
          </div>
          <span className="text-xs font-medium text-mute tabular-nums">{testResults.passed} / {testResults.total}</span>
        </div>
      </div>

      {/* Compile / runtime error body */}
      {testResults.compile_error && (
        <pre className="max-h-40 overflow-auto bg-coral/5 p-4 font-mono text-xs text-coral whitespace-pre-wrap">
          {testResults.compile_error}
        </pre>
      )}

      {/* Visible test cases — reveal one by one */}
      <div className="divide-y divide-white/5">
        {testResults.visible_tests?.slice(0, revealedCount).map((tc, i) => (
          <div
            key={tc.id}
            className={`p-4 transition-all duration-300 ${tc.passed ? "" : "bg-coral/[0.03]"}`}
          >
            <div className={`flex items-center gap-2 text-xs font-semibold ${tc.passed ? "text-sage" : "text-coral"}`}>
              <span className={`flex h-4 w-4 items-center justify-center rounded-full text-[10px] ${tc.passed ? "bg-sage/20" : "bg-coral/20"}`}>
                {tc.passed ? "✓" : "✗"}
              </span>
              Case {i + 1}
              <span className="font-normal text-mute">— {tc.label}</span>
            </div>
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              {tc.input && <CodeField label="Input" value={tc.input} />}
              <CodeField label="Expected" value={tc.expected} />
              {tc.passed ? (
                <CodeField label="Output" value={tc.output ?? tc.expected} tone="sage" />
              ) : (
                <CodeField label="Output" value={tc.error ?? tc.output ?? "no output"} tone="coral" />
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Hidden test cases revealed after visible ones */}
      {revealedCount > (testResults.visible_tests?.length ?? 0) && testResults.hidden_tests?.length > 0 && (
        <div className="border-t border-white/5 p-4">
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

      <p className="border-t border-white/5 px-4 py-2.5 text-xs text-white/30">
        Your code is shared with the interviewer whether or not you run tests.
      </p>
    </div>
  );
}
