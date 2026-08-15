import { useState } from "react";
import Prose from "./Prose";

const DIFFICULTY_STYLES = {
  easy:   { label: "Easy",   className: "text-emerald-400 bg-emerald-400/10" },
  medium: { label: "Medium", className: "text-amber-400 bg-amber-400/10" },
  hard:   { label: "Hard",   className: "text-red-400 bg-red-400/10" },
};

const TABS = [
  { id: "description", label: "Description" },
  { id: "functional", label: "Functional" },
  { id: "non-functional", label: "Non-Functional" },
  { id: "constraints", label: "Constraints" },
  { id: "out-of-scope", label: "Out of Scope" },
];

function BulletList({ items, emptyLabel }) {
  if (!items || items.length === 0) {
    return <p className="text-xs text-mute">{emptyLabel}</p>;
  }
  return (
    <ul className="space-y-1.5">
      {items.map((item, i) => (
        <li key={i} className="flex items-start gap-2">
          <span className="text-sage mt-0.5 shrink-0">•</span>
          <span className="text-sm text-cream/80">
            <Prose>{item}</Prose>
          </span>
        </li>
      ))}
    </ul>
  );
}

export default function SystemDesignProblemPanel({ questionContext }) {
  const [tab, setTab] = useState("description");

  if (!questionContext) {
    return (
      <div className="flex h-full flex-col items-center justify-center px-6 py-10 text-center">
        <div className="mb-3 text-3xl">⌛</div>
        <p className="text-sm font-medium text-cream/70">Waiting for problem</p>
        <p className="mt-1 text-xs text-mute">The interviewer will assign a system-design question shortly</p>
      </div>
    );
  }

  const diff = DIFFICULTY_STYLES[questionContext.difficulty?.toLowerCase()] || DIFFICULTY_STYLES.medium;

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header */}
      <div className="shrink-0 border-b border-white/5 px-5 pb-3 pt-4">
        <div className="flex flex-wrap items-center gap-3">
          <h2 className="font-display text-base font-semibold text-cream">{questionContext.title}</h2>
          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${diff.className}`}>{diff.label}</span>
        </div>

        {(questionContext.scale_metadata || []).length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {questionContext.scale_metadata.map((tag, i) => (
              <span
                key={i}
                className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 font-mono text-xs text-cream/70"
                title={tag.label}
              >
                <span className="text-mute">{tag.label}:</span> {tag.value}
              </span>
            ))}
          </div>
        )}

        {/* Tabs */}
        <div className="mt-3 flex flex-wrap gap-1">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`rounded-md px-3 py-1 text-xs transition ${
                tab === t.id ? "bg-white/10 font-medium text-cream" : "text-mute hover:text-cream"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto px-5 py-4 text-sm text-cream/80">
        {tab === "description" && <Prose>{questionContext.prompt}</Prose>}
        {tab === "functional" && (
          <BulletList items={questionContext.functional_requirements} emptyLabel="No functional requirements listed." />
        )}
        {tab === "non-functional" && (
          <BulletList items={questionContext.non_functional_requirements} emptyLabel="No non-functional requirements listed." />
        )}
        {tab === "constraints" && (
          <BulletList items={questionContext.scaling_constraints} emptyLabel="No scaling constraints listed." />
        )}
        {tab === "out-of-scope" && (
          <BulletList items={questionContext.out_of_scope} emptyLabel="Nothing explicitly out of scope." />
        )}
      </div>
    </div>
  );
}
