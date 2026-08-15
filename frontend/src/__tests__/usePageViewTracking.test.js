import { renderHook, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

let mockPathname = "/dashboard";

vi.mock("react-router-dom", () => ({
  useLocation: () => ({ pathname: mockPathname }),
}));

vi.mock("../lib/api", () => ({
  api: { trackEvent: vi.fn() },
}));

vi.mock("../lib/supabaseClient", () => ({
  supabase: { auth: { getSession: vi.fn() } },
}));

import { api } from "../lib/api";
import { supabase } from "../lib/supabaseClient";
import usePageViewTracking from "../hooks/usePageViewTracking";

beforeEach(() => {
  vi.clearAllMocks();
  mockPathname = "/dashboard";
});

describe("usePageViewTracking", () => {
  it("reports the current path when a session exists", async () => {
    supabase.auth.getSession.mockResolvedValue({ data: { session: { access_token: "t" } } });
    renderHook(() => usePageViewTracking());
    await waitFor(() =>
      expect(api.trackEvent).toHaveBeenCalledWith("page_view", { properties: { path: "/dashboard" } })
    );
  });

  it("normalizes /results/:sessionId to a bounded route template", async () => {
    mockPathname = "/results/abc-123";
    supabase.auth.getSession.mockResolvedValue({ data: { session: { access_token: "t" } } });
    renderHook(() => usePageViewTracking());
    await waitFor(() =>
      expect(api.trackEvent).toHaveBeenCalledWith("page_view", { properties: { path: "/results/:sessionId" } })
    );
  });

  it("does not report page views for anonymous visitors", async () => {
    supabase.auth.getSession.mockResolvedValue({ data: { session: null } });
    renderHook(() => usePageViewTracking());
    await waitFor(() => expect(supabase.auth.getSession).toHaveBeenCalled());
    expect(api.trackEvent).not.toHaveBeenCalled();
  });
});
