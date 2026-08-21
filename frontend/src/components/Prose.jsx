import ReactMarkdown from "react-markdown";

// Question prompts/constraints come from public source datasets (LeetCode,
// system-design-primer, etc.), not this app's own copy, so an em/en dash can
// show up in the raw text regardless of anything the app itself writes. This
// is the one place all of that text renders (CodeEditor's ProblemPanel and
// SystemDesignProblemPanel both go through here), so sanitizing here
// guarantees no dash reaches the screen no matter which source it came from,
// without needing a data migration. Mirrors the backend's
// _strip_typographic_dashes (services/llm.py) — same reasoning, same rule.
const DASH_CHARS = /[–—]/;
export function stripTypographicDashes(text) {
  if (typeof text !== "string" || !text) return text;
  return text
    .replace(/(?<=\d)[–—](?=\d)/g, "-")
    .replace(new RegExp(`\\s*${DASH_CHARS.source}\\s*`, "g"), ", ");
}

// Renders LLM-authored problem text (which may contain markdown like `code`,
// **bold**, or bullet lists) instead of showing it as raw escaped text.
// Shared between CodeEditor's ProblemPanel and SystemDesignProblemPanel.
export default function Prose({ children }) {
  return (
    <ReactMarkdown
      components={{
        p: ({ children }) => <p className="leading-relaxed">{children}</p>,
        code: ({ children }) => (
          <code className="rounded bg-white/10 px-1 py-0.5 font-mono text-xs text-cream">{children}</code>
        ),
        ul: ({ children }) => <ul className="list-disc space-y-1 pl-5">{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal space-y-1 pl-5">{children}</ol>,
        strong: ({ children }) => <strong className="font-semibold text-cream">{children}</strong>,
      }}
    >
      {stripTypographicDashes(children)}
    </ReactMarkdown>
  );
}
