import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import { supabase } from "../lib/supabaseClient";

const TRACKS = [
  {
    id: "behavioral",
    name: "Behavioral",
    description: "Practice STAR-method answers to common behavioral questions.",
    accent: "bg-amber/15 text-amber"
  },
  {
    id: "technical",
    name: "Technical",
    description: "Talk through a coding problem with a live editor and execution.",
    accent: "bg-sage/15 text-sage"
  },
  {
    id: "system-design",
    name: "System design",
    description: "Reason out loud about architecture, trade-offs, and scale.",
    accent: "bg-coral/15 text-coral"
  }
];

export default function Dashboard() {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [userEmail, setUserEmail] = useState("");

  useEffect(() => {
    let mounted = true;

    async function load() {
      const { data: userData } = await supabase.auth.getUser();
      if (mounted) setUserEmail(userData?.user?.email ?? "");

      const { data, error } = await supabase
        .from("sessions")
        .select("id, track, role, overall_score, created_at, status")
        .order("created_at", { ascending: false })
        .limit(10);

      if (!error && mounted) setSessions(data ?? []);
      if (mounted) setLoading(false);
    }

    load();
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <main className="flex-1">
        <section className="mx-auto max-w-6xl px-6 py-12">
          <p className="text-sm text-mute">Signed in as {userEmail}</p>
          <h1 className="mt-2 font-display text-4xl tracking-tight">
            Ready for your next session?
          </h1>

          <div className="mt-10 grid gap-6 sm:grid-cols-3">
            {TRACKS.map((track) => (
              <Link
                key={track.id}
                to={`/interview?track=${track.id}`}
                className="rounded-2xl border border-white/10 bg-panel p-6 transition hover:border-amber/40"
              >
                <span className={`inline-flex rounded-full px-3 py-1 text-xs font-medium ${track.accent}`}>
                  {track.name}
                </span>
                <p className="mt-4 text-sm text-mute">{track.description}</p>
                <span className="mt-6 inline-block text-sm text-amber">Start session &rarr;</span>
              </Link>
            ))}
          </div>

          <div className="mt-16">
            <h2 className="font-display text-2xl tracking-tight">Recent sessions</h2>

            {loading ? (
              <p className="mt-4 text-sm text-mute">Loading...</p>
            ) : sessions.length === 0 ? (
              <div className="mt-4 rounded-2xl border border-dashed border-white/10 p-8 text-center text-sm text-mute">
                No sessions yet. Pick a track above to run your first mock interview.
              </div>
            ) : (
              <div className="mt-4 overflow-hidden rounded-2xl border border-white/10">
                <table className="w-full text-left text-sm">
                  <thead className="bg-panel text-mute">
                    <tr>
                      <th className="px-4 py-3 font-medium">Track</th>
                      <th className="px-4 py-3 font-medium">Role</th>
                      <th className="px-4 py-3 font-medium">Score</th>
                      <th className="px-4 py-3 font-medium">Status</th>
                      <th className="px-4 py-3 font-medium">Date</th>
                      <th className="px-4 py-3 font-medium"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {sessions.map((s) => (
                      <tr key={s.id} className="border-t border-white/5">
                        <td className="px-4 py-3 capitalize">{s.track}</td>
                        <td className="px-4 py-3 text-mute">{s.role || "—"}</td>
                        <td className="px-4 py-3">
                          {s.overall_score != null ? `${s.overall_score}/10` : "—"}
                        </td>
                        <td className="px-4 py-3 text-mute capitalize">{s.status}</td>
                        <td className="px-4 py-3 text-mute">
                          {new Date(s.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <Link to={`/results/${s.id}`} className="text-amber hover:underline">
                            View
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
}
