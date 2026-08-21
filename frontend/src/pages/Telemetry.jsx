import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import Navbar from "../components/Navbar";
import { api } from "../lib/api";

const TRACK_LABELS = {
  behavioral: "Behavioral",
  technical: "Technical",
  "system-design": "System Design",
};

const TRACK_COLORS = {
  behavioral: "bg-amber",
  technical: "bg-sage",
  "system-design": "bg-coral",
};

const TRACK_TEXT_COLORS = {
  behavioral: "text-amber",
  technical: "text-sage",
  "system-design": "text-coral",
};

const TRACK_RING_COLORS = {
  behavioral: "#E8A33D",
  technical: "#5FA88F",
  "system-design": "#E0735C",
};

const DIFFICULTY_COLORS = { easy: "bg-sage", medium: "bg-amber", hard: "bg-coral" };
const DIFFICULTY_LABELS = { easy: "Easy", medium: "Medium", hard: "Hard" };

const LANG_COLORS = ["bg-amber", "bg-sage", "bg-coral", "bg-blue-400"];

const QUESTION_TRACKS = ["technical", "system-design"];

// Full static class strings (not interpolated) so Tailwind's content scan
// can actually find and generate them — `bg-${accent}/10` would silently
// produce no CSS since the scanner doesn't evaluate template literals.
const KPI_GLOW_CLASSES = {
  amber: "bg-amber/10 group-hover:bg-amber/20",
  sage: "bg-sage/10 group-hover:bg-sage/20",
  coral: "bg-coral/10 group-hover:bg-coral/20",
};

function KpiCard({ label, value, sub, accent = "amber", delay = 0 }) {
  return (
    <div
      className="group relative overflow-hidden rounded-2xl border border-white/10 bg-panel px-6 py-5 opacity-0 animate-rise transition hover:-translate-y-0.5 hover:border-white/20"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div
        className={`pointer-events-none absolute -right-8 -top-8 h-24 w-24 rounded-full blur-2xl transition ${KPI_GLOW_CLASSES[accent]}`}
      />
      <p className="text-xs uppercase tracking-wide text-mute">{label}</p>
      <p className="mt-1 font-display text-3xl text-cream">{value ?? "N/A"}</p>
      {sub && <p className="mt-1 text-xs text-mute">{sub}</p>}
    </div>
  );
}

function ProgressRing({ pct, color, size = 56, stroke = 5 }) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const offset = c - (Math.min(Math.max(pct, 0), 100) / 100) * c;
  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth={stroke} />
        <circle
          cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={stroke}
          strokeDasharray={c} strokeDashoffset={offset} strokeLinecap="round"
          className="transition-all duration-700 ease-out"
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-[11px] font-medium text-cream/80">
        {pct}%
      </span>
    </div>
  );
}

// One card per track combining session volume, avg score, and completion into
// a single glanceable unit — replaces the old pair of near-identical
// horizontal-bar panels (sessions-by-track / avg-score-by-track), which read
// as the same chart twice with different numbers.
function TrackCard({ track, sessions, avgScore, completion, delay = 0 }) {
  return (
    <div
      className="relative overflow-hidden rounded-2xl border border-white/10 bg-panel p-5 opacity-0 animate-rise transition hover:-translate-y-0.5 hover:border-white/20"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className={`absolute inset-x-0 top-0 h-1 ${TRACK_COLORS[track]}`} />
      <div className="flex items-start justify-between">
        <div>
          <span className={`inline-flex items-center gap-1.5 text-sm font-medium ${TRACK_TEXT_COLORS[track]}`}>
            <span className={`h-1.5 w-1.5 rounded-full ${TRACK_COLORS[track]}`} />
            {TRACK_LABELS[track]}
          </span>
          <p className="mt-3 font-display text-3xl text-cream">{sessions}</p>
          <p className="text-xs text-mute">session{sessions === 1 ? "" : "s"}</p>
        </div>
        <ProgressRing pct={completion} color={TRACK_RING_COLORS[track]} />
      </div>
      <div className="mt-4 flex items-center justify-between border-t border-white/5 pt-3 text-xs">
        <span className="text-mute">Avg score</span>
        <span className="text-cream/90 tabular-nums">{avgScore > 0 ? `${avgScore} / 10` : "N/A"}</span>
      </div>
      <div className="mt-1.5 flex items-center justify-between text-xs">
        <span className="text-mute">Completion</span>
        <span className="text-cream/90 tabular-nums">{completion}%</span>
      </div>
    </div>
  );
}

function HBar({ label, value, max, color = "bg-amber", suffix = "" }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div className="flex items-center gap-3">
      <span className="w-28 shrink-0 text-right text-xs text-mute truncate">{label}</span>
      <div className="flex-1 h-2 rounded-full bg-white/5 overflow-hidden">
        <div className={`h-full rounded-full ${color} transition-all duration-700`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-10 text-right text-xs text-cream/70 tabular-nums">{value}{suffix}</span>
    </div>
  );
}

function DailyChart({ data }) {
  const entries = Object.entries(data);
  const max = Math.max(...entries.map(([, v]) => v), 1);
  const CHART_H = 80; // matches h-20

  return (
    <div className="flex items-end gap-1 h-20">
      {entries.map(([day, count], idx) => {
        const barH = count > 0 ? Math.max(Math.round((count / max) * CHART_H), 4) : 2;
        const label = new Date(day + "T00:00:00").toLocaleDateString("en-IE", { month: "short", day: "numeric" });
        return (
          <div key={day} className="flex flex-col items-center flex-1 gap-1 group relative">
            <div
              className="w-full rounded-t bg-gradient-to-t from-amber/50 to-amber group-hover:from-amber group-hover:to-amberDark transition-all duration-300"
              style={{ height: barH }}
              title={`${label}: ${count} session${count !== 1 ? "s" : ""}`}
            />
            {idx % 4 === 0 && (
              <span className="text-[9px] text-mute rotate-45 origin-left mt-1">{label}</span>
            )}
          </div>
        );
      })}
    </div>
  );
}

// Distinct from every other chart on the page: a single gradient (red→green)
// so the eye reads "worse ↔ better" left-to-right at a glance, a dashed
// marker at the bucket containing the overall average, and count labels
// baked into each bar instead of relying on a hover tooltip.
function ScoreDistChart({ data, avgScore }) {
  const bucketKeys = Object.keys(data);
  const total = Object.values(data).reduce((a, b) => a + b, 0);
  const max = Math.max(...Object.values(data), 1);
  const gradients = [
    "from-coral to-coral/70",
    "from-coral/80 to-amber/80",
    "from-amber to-amber",
    "from-sage/80 to-sage",
    "from-sage to-sage/70",
  ];
  const avgBucketIdx = avgScore > 0
    ? Math.min(Math.floor(avgScore / 2), bucketKeys.length - 1)
    : -1;

  return (
    <div>
      <div className="flex items-end gap-3 h-28">
        {bucketKeys.map((bucket, i) => {
          const count = data[bucket];
          const pct = Math.round((count / max) * 100);
          const isAvgBucket = i === avgBucketIdx;
          return (
            <div key={bucket} className="relative flex flex-1 flex-col items-center gap-1.5">
              {isAvgBucket && (
                <span className="absolute -top-5 text-[9px] font-medium text-cream/70">avg</span>
              )}
              <span className="text-xs text-cream/70 tabular-nums">{count}</span>
              <div className="flex h-20 w-full items-end">
                <div
                  className={`w-full rounded-t-md bg-gradient-to-t ${gradients[i]} transition-all duration-500 ${
                    isAvgBucket ? "ring-2 ring-cream/40 ring-offset-1 ring-offset-panel" : ""
                  }`}
                  style={{ height: `${Math.max(pct, count > 0 ? 6 : 2)}%` }}
                />
              </div>
              <span className="text-[10px] text-mute">{bucket}</span>
            </div>
          );
        })}
      </div>
      <p className="mt-3 text-[11px] text-mute">
        {total > 0 ? `${total} scored session${total === 1 ? "" : "s"}, lowest → highest` : "No scored sessions yet"}
      </p>
    </div>
  );
}

// A single bar per track, segmented easy/medium/hard, so the difficulty mix
// of what's actually been assigned reads as one shape instead of three
// separate numbers.
function DifficultyStackedBar({ counts }) {
  const total = counts.easy + counts.medium + counts.hard;
  if (total === 0) return <p className="text-xs text-mute">No questions assigned yet.</p>;
  return (
    <div className="flex h-3 w-full overflow-hidden rounded-full bg-white/5">
      {["easy", "medium", "hard"].map((d) => {
        const pct = (counts[d] / total) * 100;
        if (pct === 0) return null;
        return (
          <div
            key={d}
            className={`${DIFFICULTY_COLORS[d]} transition-all duration-700 first:rounded-l-full last:rounded-r-full`}
            style={{ width: `${pct}%` }}
            title={`${DIFFICULTY_LABELS[d]}: ${counts[d]}`}
          />
        );
      })}
    </div>
  );
}

function TopicRow({ row, max }) {
  const pct = max > 0 ? Math.round((row.total / max) * 100) : 0;
  return (
    <div className="flex items-center gap-3">
      <span className="w-32 shrink-0 truncate text-xs text-mute capitalize">{row.topic}</span>
      <div className="flex h-1.5 flex-1 overflow-hidden rounded-full bg-white/5">
        {["easy", "medium", "hard"].map((d) => {
          const segPct = row.total > 0 ? (row[d] / row.total) * pct : 0;
          if (segPct === 0) return null;
          return <div key={d} className={DIFFICULTY_COLORS[d]} style={{ width: `${segPct}%` }} />;
        })}
      </div>
      <span className="w-6 text-right text-xs tabular-nums text-cream/70">{row.total}</span>
    </div>
  );
}

function QuestionMixCard({ track, difficulty, topics, delay = 0 }) {
  const maxTopic = Math.max(...topics.map((t) => t.total), 1);
  const total = difficulty.easy + difficulty.medium + difficulty.hard;
  return (
    <div
      className="rounded-2xl border border-white/10 bg-panel px-6 py-5 opacity-0 animate-rise"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="flex items-center justify-between">
        <h3 className={`flex items-center gap-1.5 text-sm font-medium ${TRACK_TEXT_COLORS[track]}`}>
          <span className={`h-1.5 w-1.5 rounded-full ${TRACK_COLORS[track]}`} />
          {TRACK_LABELS[track]}
        </h3>
        <span className="text-xs text-mute">{total} assigned</span>
      </div>

      <div className="mt-4">
        <DifficultyStackedBar counts={difficulty} />
        <div className="mt-2 flex items-center gap-4 text-[11px] text-mute">
          {["easy", "medium", "hard"].map((d) => (
            <span key={d} className="flex items-center gap-1.5">
              <span className={`h-2 w-2 rounded-full ${DIFFICULTY_COLORS[d]}`} />
              {DIFFICULTY_LABELS[d]} ({difficulty[d]})
            </span>
          ))}
        </div>
      </div>

      {topics.length > 0 && (
        <div className="mt-5 space-y-2 border-t border-white/5 pt-4">
          <p className="text-[11px] uppercase tracking-wide text-mute">Top topics</p>
          {topics.map((row) => (
            <TopicRow key={row.topic} row={row} max={maxTopic} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function Telemetry() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    api.getStats()
      .then(setStats)
      .catch((err) => {
        if (err.message?.includes("401") || err.message?.includes("403")) {
          navigate("/login", { replace: true });
        } else {
          setError(err.message || "Failed to load telemetry data.");
        }
      })
      .finally(() => setLoading(false));
  }, [navigate]);

  const trackKeys = ["behavioral", "technical", "system-design"];
  const langEntries = stats
    ? Object.entries(stats.language_usage).sort(([, a], [, b]) => b - a)
    : [];
  const maxLang = langEntries.length ? langEntries[0][1] : 1;
  const completionRate = stats && stats.total_sessions > 0
    ? Math.round((stats.completed_sessions / stats.total_sessions) * 100)
    : 0;

  return (
    <div className="min-h-screen bg-stage">
      <Navbar />
      <main className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-8">
          <h1 className="font-display text-2xl text-cream">Dashboard</h1>
          <p className="mt-1 text-sm text-mute">Your interview performance at a glance</p>
        </div>

        {loading && (
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="h-24 animate-pulse rounded-2xl bg-panel" />
            ))}
          </div>
        )}

        {error && (
          <p className="rounded-xl border border-coral/30 bg-coral/5 px-5 py-4 text-sm text-coral">{error}</p>
        )}

        {stats && (
          <div className="space-y-6">
            {/* KPI row */}
            <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
              <KpiCard label="Total sessions" value={stats.total_sessions} accent="amber" delay={0} />
              <KpiCard label="Completed" value={stats.completed_sessions} sub={`${completionRate}% completion rate`} accent="sage" delay={60} />
              <KpiCard label="Avg score" value={stats.avg_score > 0 ? `${stats.avg_score} / 10` : "N/A"} sub="across completed sessions" accent="coral" delay={120} />
              <KpiCard label="Avg duration" value={stats.avg_duration_minutes > 0 ? `${stats.avg_duration_minutes} min` : "N/A"} sub="per completed session" accent="amber" delay={180} />
            </div>

            {/* Track breakdown — sessions, score, and completion in one glanceable card per track */}
            <div>
              <h2 className="mb-3 text-sm font-medium text-cream">Track breakdown</h2>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                {trackKeys.map((t, i) => (
                  <TrackCard
                    key={t}
                    track={t}
                    sessions={stats.sessions_by_track[t] || 0}
                    avgScore={stats.avg_score_by_track[t] || 0}
                    completion={stats.completion_rate_by_track[t] || 0}
                    delay={i * 60}
                  />
                ))}
              </div>
            </div>

            {/* Charts grid */}
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
              <div className="rounded-2xl border border-white/10 bg-panel px-6 py-5">
                <h2 className="mb-4 text-sm font-medium text-cream">Sessions, last 14 days</h2>
                <DailyChart data={stats.sessions_last_14_days} />
              </div>

              <div className="rounded-2xl border border-white/10 bg-panel px-6 py-5">
                <h2 className="mb-4 text-sm font-medium text-cream">Score distribution</h2>
                {Object.values(stats.score_distribution).every((v) => v === 0) ? (
                  <p className="text-xs text-mute">No completed sessions with scores yet.</p>
                ) : (
                  <ScoreDistChart data={stats.score_distribution} avgScore={stats.avg_score} />
                )}
              </div>
            </div>

            {/* Question difficulty/topic mix — technical + system-design */}
            <div>
              <h2 className="mb-3 text-sm font-medium text-cream">Questions assigned, by topic &amp; difficulty</h2>
              <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
                {QUESTION_TRACKS.map((t) => (
                  <QuestionMixCard
                    key={t}
                    track={t}
                    difficulty={stats.difficulty_by_track?.[t] || { easy: 0, medium: 0, hard: 0 }}
                    topics={stats.topic_breakdown?.[t] || []}
                  />
                ))}
              </div>
            </div>

            {/* Coding language usage */}
            {langEntries.length > 0 && (
              <div className="rounded-2xl border border-white/10 bg-panel px-6 py-5">
                <h2 className="mb-4 text-sm font-medium text-cream">Coding language usage</h2>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  {langEntries.map(([lang, count], i) => (
                    <HBar
                      key={lang}
                      label={lang.charAt(0).toUpperCase() + lang.slice(1)}
                      value={count}
                      max={maxLang}
                      color={LANG_COLORS[i % LANG_COLORS.length]}
                      suffix=" runs"
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
