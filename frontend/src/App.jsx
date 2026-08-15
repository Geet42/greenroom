import { Routes, Route } from "react-router-dom";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Dashboard from "./pages/Dashboard";
import Interview from "./pages/Interview";
import Results from "./pages/Results";
import AuthCallback from "./pages/AuthCallback";
import Telemetry from "./pages/Telemetry";
import RequireAuth from "./components/RequireAuth";
import usePageViewTracking from "./hooks/usePageViewTracking";

export default function App() {
  usePageViewTracking();
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/auth/callback" element={<AuthCallback />} />
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />
      <Route
        path="/dashboard"
        element={
          <RequireAuth>
            <Dashboard />
          </RequireAuth>
        }
      />
      <Route
        path="/interview"
        element={
          <RequireAuth>
            <Interview />
          </RequireAuth>
        }
      />
      <Route
        path="/results/:sessionId"
        element={
          <RequireAuth>
            <Results />
          </RequireAuth>
        }
      />
      <Route
        path="/telemetry"
        element={
          <RequireAuth>
            <Telemetry />
          </RequireAuth>
        }
      />
    </Routes>
  );
}
