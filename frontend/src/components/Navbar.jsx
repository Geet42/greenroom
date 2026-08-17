import { Link, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { supabase } from "../lib/supabaseClient";

export default function Navbar() {
  const [session, setSession] = useState(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => setSession(data.session));
    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
    });
    return () => listener.subscription.unsubscribe();
  }, []);

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    navigate("/");
  };

  return (
    <header className="sticky top-0 z-50 border-b border-white/5 bg-stage/80 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-6">
        <Link to="/" className="flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-full bg-amber text-ink">
            <span className="block h-2.5 w-2.5 rounded-full bg-ink" />
          </span>
          <span className="font-display text-lg tracking-tight">Greenroom</span>
        </Link>

        <nav className="hidden items-center gap-8 text-sm text-mute md:flex">
          <a href="/#how-it-works" className="hover:text-cream">How it works</a>
          <a href="/#tracks" className="hover:text-cream">Tracks</a>
          <a href="/#pricing" className="hover:text-cream">Pricing</a>
        </nav>

        <div className="hidden items-center gap-3 md:flex">
          {session ? (
            <>
              <Link
                to="/dashboard"
                className="rounded-full px-4 py-2 text-sm text-cream transition hover:bg-panel"
              >
                Your Interviews
              </Link>
              <Link
                to="/telemetry"
                className="rounded-full px-4 py-2 text-sm text-mute transition hover:bg-panel hover:text-cream"
              >
                Dashboard
              </Link>
              <button
                onClick={handleSignOut}
                className="rounded-full border border-white/10 px-4 py-2 text-sm text-mute transition hover:border-white/20 hover:text-cream"
              >
                Sign out
              </button>
            </>
          ) : (
            <>
              <Link
                to="/login"
                className="rounded-full px-4 py-2 text-sm text-cream transition hover:bg-panel"
              >
                Sign in
              </Link>
              <Link
                to="/signup"
                className="rounded-full bg-amber px-4 py-2 text-sm font-medium text-ink transition hover:bg-amberDark"
              >
                Start free
              </Link>
            </>
          )}
        </div>

        {/* Mobile menu toggle — 44px tap target, standard touch-target minimum */}
        <button
          type="button"
          onClick={() => setMenuOpen((v) => !v)}
          aria-label={menuOpen ? "Close menu" : "Open menu"}
          aria-expanded={menuOpen}
          className="flex h-11 w-11 items-center justify-center rounded-full text-cream transition hover:bg-panel md:hidden"
        >
          {menuOpen ? (
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
              <path d="M4 4l12 12M16 4L4 16" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
            </svg>
          ) : (
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
              <path d="M2.5 5h15M2.5 10h15M2.5 15h15" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
            </svg>
          )}
        </button>
      </div>

      {menuOpen && (
        <div className="border-t border-white/5 bg-stage px-4 py-4 md:hidden">
          <nav className="flex flex-col gap-1 text-sm text-mute">
            <a href="/#how-it-works" className="rounded-lg px-3 py-2.5 hover:bg-panel hover:text-cream">How it works</a>
            <a href="/#tracks" className="rounded-lg px-3 py-2.5 hover:bg-panel hover:text-cream">Tracks</a>
            <a href="/#pricing" className="rounded-lg px-3 py-2.5 hover:bg-panel hover:text-cream">Pricing</a>
          </nav>
          <div className="mt-3 flex flex-col gap-2 border-t border-white/5 pt-3">
            {session ? (
              <>
                <Link to="/dashboard" className="rounded-lg px-3 py-2.5 text-sm text-cream hover:bg-panel">
                  Your Interviews
                </Link>
                <Link to="/telemetry" className="rounded-lg px-3 py-2.5 text-sm text-mute hover:bg-panel hover:text-cream">
                  Dashboard
                </Link>
                <button
                  onClick={handleSignOut}
                  className="rounded-lg border border-white/10 px-3 py-2.5 text-left text-sm text-mute hover:border-white/20 hover:text-cream"
                >
                  Sign out
                </button>
              </>
            ) : (
              <>
                <Link to="/login" className="rounded-lg px-3 py-2.5 text-sm text-cream hover:bg-panel">
                  Sign in
                </Link>
                <Link
                  to="/signup"
                  className="rounded-full bg-amber px-4 py-2.5 text-center text-sm font-medium text-ink hover:bg-amberDark"
                >
                  Start free
                </Link>
              </>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
