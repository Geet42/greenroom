import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "../lib/supabaseClient";

export default function AuthCallback() {
  const navigate = useNavigate();

  useEffect(() => {
    // Supabase exchanges the code for a session automatically when flowType is "pkce".
    // We just wait for the session to be ready then redirect to the dashboard.
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        navigate("/dashboard", { replace: true });
      } else {
        navigate("/login", { replace: true });
      }
    });
  }, [navigate]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-stage">
      <p className="text-sm text-mute">Signing you in…</p>
    </div>
  );
}
