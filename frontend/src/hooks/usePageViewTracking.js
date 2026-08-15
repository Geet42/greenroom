import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import { supabase } from "../lib/supabaseClient";
import { api } from "../lib/api";

// Matches the dynamic segment of App.jsx's "/results/:sessionId" route so the
// backend sees a bounded route template rather than one label per session id.
function normalizePath(pathname) {
  if (pathname.startsWith("/results/")) return "/results/:sessionId";
  return pathname;
}

// Only reports page views for signed-in users — the /analytics/event
// endpoint requires auth, and firing it from the public landing/login/signup
// pages would just be a guaranteed 401 on every anonymous visit.
export default function usePageViewTracking() {
  const location = useLocation();

  useEffect(() => {
    let cancelled = false;
    supabase.auth.getSession().then(({ data }) => {
      if (cancelled || !data?.session) return;
      api.trackEvent("page_view", { properties: { path: normalizePath(location.pathname) } });
    });
    return () => {
      cancelled = true;
    };
  }, [location.pathname]);
}
