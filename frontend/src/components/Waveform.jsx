const HEIGHTS = [18, 34, 48, 30, 60, 22, 44, 56, 26, 38, 50, 20, 42, 32, 58, 24];

export default function Waveform({ active = true, size = "md" }) {
  const barWidth = size === "lg" ? "w-1.5" : "w-1";
  const gap = size === "lg" ? "gap-1.5" : "gap-1";
  const maxHeight = size === "lg" ? 64 : 36;

  return (
    <div className={`flex items-center ${gap}`} aria-hidden="true">
      {HEIGHTS.map((h, i) => (
        <span
          key={i}
          className={`${barWidth} rounded-full bg-amber/80 ${active ? "animate-pulseBar" : ""}`}
          style={{
            height: `${(h / 60) * maxHeight}px`,
            animationDelay: `${i * 0.06}s`,
            opacity: active ? 1 : 0.35
          }}
        />
      ))}
    </div>
  );
}
