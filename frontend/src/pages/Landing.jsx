import { Link } from "react-router-dom";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import Waveform from "../components/Waveform";

const TRACKS = [
  {
    name: "Behavioral",
    eyebrow: "STAR method",
    description:
      "Walk through your stories. Greenroom listens for structure, follow-ups on vague impact, and tells you where the story loses the thread.",
    accent: "bg-amber/15 text-amber"
  },
  {
    name: "Technical",
    eyebrow: "Live coding",
    description:
      "Talk through your approach while you code in a real editor. Run your solution, explain trade-offs, and get pushed on the parts you glossed over.",
    accent: "bg-sage/15 text-sage"
  },
  {
    name: "System design",
    eyebrow: "Whiteboard talk",
    description:
      "Reason out loud about scale, trade-offs, and failure modes. Greenroom plays the skeptical interviewer who keeps asking 'why'.",
    accent: "bg-coral/15 text-coral"
  }
];

const STEPS = [
  {
    label: "Pick a track",
    detail: "Choose behavioral, technical, or system design, and set the role you're prepping for."
  },
  {
    label: "Talk it through",
    detail: "Speak naturally. Greenroom asks real follow-ups based on what you actually say."
  },
  {
    label: "Get the breakdown",
    detail: "A structured report on clarity, confidence, and what to tighten before the real interview."
  }
];

export default function Landing() {
  return (
    <div className="min-h-screen">
      <Navbar />

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div
          className="pointer-events-none absolute -top-40 left-1/2 h-[520px] w-[900px] -translate-x-1/2 animate-sweep rounded-full bg-amber/20 blur-3xl"
          aria-hidden="true"
        />
        <div className="relative mx-auto max-w-6xl px-6 pb-20 pt-16 sm:pt-24">
          <div className="animate-rise">
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-sage">
              Free to start &middot; voice-based &middot; honest feedback
            </p>
            <h1 className="mt-6 max-w-3xl font-display text-5xl font-medium leading-[1.1] tracking-tight sm:text-6xl">
              Walk into the room
              <span className="text-amber"> ready.</span>
            </h1>
            <p className="mt-6 max-w-xl text-lg text-mute">
              Greenroom is where you rehearse before it counts. Speak your answers out loud to
              an AI interviewer that listens, follows up, and tells you exactly where your
              story or your code falls apart.
            </p>
            <div className="mt-10 flex flex-wrap items-center gap-4">
              <Link
                to="/signup"
                className="rounded-full bg-amber px-7 py-3 text-sm font-medium text-ink transition hover:bg-amberDark"
              >
                Start a free mock interview
              </Link>
              <a
                href="#how-it-works"
                className="rounded-full border border-white/10 px-7 py-3 text-sm text-cream transition hover:border-white/25"
              >
                See how it works
              </a>
            </div>
          </div>

          {/* Signature visual: the "stage" panel */}
          <div className="mt-16 animate-rise" style={{ animationDelay: "0.15s" }}>
            <div className="relative mx-auto max-w-2xl rounded-2xl border border-white/10 bg-panel p-6 shadow-glow sm:p-8">
              <div className="flex items-center justify-between text-xs text-mute">
                <span className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-sage" />
                  Live session &middot; Behavioral track
                </span>
                <span>00:42</span>
              </div>

              <div className="mt-6 space-y-4">
                <div className="rounded-xl bg-panelLight/60 p-4 text-sm text-mute">
                  <p className="font-display text-cream">Interviewer</p>
                  <p className="mt-1">
                    Tell me about a time you had to push back on a decision you disagreed with.
                  </p>
                </div>
                <div className="rounded-xl border border-amber/20 bg-amber/5 p-4 text-sm">
                  <p className="font-display text-amber">You</p>
                  <p className="mt-1 text-cream/90">
                    "On my last team, we were about to ship a feature without testing edge
                    cases for..."
                  </p>
                  <div className="mt-4">
                    <Waveform active />
                  </div>
                </div>
              </div>

              <div className="mt-6 flex items-center justify-between border-t border-white/5 pt-4 text-xs text-mute">
                <span>Clarity: building</span>
                <span>Structure: needs a clearer result</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="border-t border-white/5 py-20">
        <div className="mx-auto max-w-6xl px-6">
          <h2 className="font-display text-3xl tracking-tight sm:text-4xl">
            Three steps. No scheduling, no judgment.
          </h2>
          <div className="mt-12 grid gap-10 sm:grid-cols-3">
            {STEPS.map((step, i) => (
              <div key={step.label}>
                <p className="font-display text-4xl text-amber">{i + 1}</p>
                <h3 className="mt-3 text-lg font-medium">{step.label}</h3>
                <p className="mt-2 text-sm text-mute">{step.detail}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Tracks */}
      <section id="tracks" className="border-t border-white/5 py-20">
        <div className="mx-auto max-w-6xl px-6">
          <h2 className="font-display text-3xl tracking-tight sm:text-4xl">
            Practice the interview you're actually facing.
          </h2>
          <p className="mt-3 max-w-2xl text-mute">
            Every session adapts to the track you choose, with follow-up questions shaped by
            how you answer, not a fixed script.
          </p>
          <div className="mt-12 grid gap-6 sm:grid-cols-3">
            {TRACKS.map((track) => (
              <div
                key={track.name}
                className="rounded-2xl border border-white/10 bg-panel p-6 transition hover:border-white/20"
              >
                <span className={`inline-flex rounded-full px-3 py-1 text-xs font-medium ${track.accent}`}>
                  {track.eyebrow}
                </span>
                <h3 className="mt-4 font-display text-2xl">{track.name}</h3>
                <p className="mt-3 text-sm text-mute">{track.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="border-t border-white/5 py-20">
        <div className="mx-auto max-w-6xl px-6">
          <h2 className="font-display text-3xl tracking-tight sm:text-4xl">
            Start free. Stay free, if that's what works.
          </h2>
          <div className="mt-12 grid gap-6 sm:grid-cols-2">
            <div className="rounded-2xl border border-white/10 bg-panel p-8">
              <h3 className="font-display text-2xl">Free</h3>
              <p className="mt-2 text-sm text-mute">Everything you need to prep consistently.</p>
              <p className="mt-6 font-display text-4xl">$0</p>
              <ul className="mt-6 space-y-3 text-sm text-mute">
                <li>Unlimited behavioral and technical sessions</li>
                <li>Live coding with instant execution</li>
                <li>Structured feedback after every session</li>
                <li>Session history and progress tracking</li>
              </ul>
              <Link
                to="/signup"
                className="mt-8 inline-flex rounded-full bg-amber px-6 py-3 text-sm font-medium text-ink transition hover:bg-amberDark"
              >
                Create your account
              </Link>
            </div>
            <div className="rounded-2xl border border-white/10 bg-panel p-8 opacity-80">
              <h3 className="font-display text-2xl">Pro</h3>
              <p className="mt-2 text-sm text-mute">For focused, high-volume prep. Coming soon.</p>
              <p className="mt-6 font-display text-4xl">&mdash;</p>
              <ul className="mt-6 space-y-3 text-sm text-mute">
                <li>Role-tailored question banks from your resume</li>
                <li>Higher-accuracy speech transcription</li>
                <li>Downloadable interview reports</li>
                <li>Priority access to new interview tracks</li>
              </ul>
              <span className="mt-8 inline-flex rounded-full border border-white/10 px-6 py-3 text-sm text-mute">
                Notify me at launch
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="border-t border-white/5 py-20">
        <div className="mx-auto max-w-6xl px-6 text-center">
          <h2 className="font-display text-3xl tracking-tight sm:text-4xl">
            The room is waiting. Get comfortable in it first.
          </h2>
          <Link
            to="/signup"
            className="mt-8 inline-flex rounded-full bg-amber px-8 py-3 text-sm font-medium text-ink transition hover:bg-amberDark"
          >
            Start your first session
          </Link>
        </div>
      </section>

      <Footer />
    </div>
  );
}
