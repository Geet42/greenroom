import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { supabase } from "../lib/supabaseClient";

export default function RequireAuth({ children }) {
  const [status, setStatus] = useState("loading");

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setStatus(data.session ? "authed" : "anon");
    });
    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
      setStatus(session ? "authed" : "anon");
    });
    return () => listener.subscription.unsubscribe();
  }, []);

  if (status === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center text-mute">
        Loading...
      </div>
    );
  }

  if (status === "anon") {
    return <Navigate to="/login" replace />;
  }

  return children;
}
