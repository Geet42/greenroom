import ReactMarkdown from "react-markdown";

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
      {children}
    </ReactMarkdown>
  );
}
