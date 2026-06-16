import { Link, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { supabase } from "../lib/supabaseClient";

export default function Navbar() {
  const [session, setSession] = useState(null);
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
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
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

        <div className="flex items-center gap-3">
          {session ? (
            <>
              <Link
                to="/dashboard"
                className="rounded-full px-4 py-2 text-sm text-cream transition hover:bg-panel"
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
      </div>
    </header>
  );
}
