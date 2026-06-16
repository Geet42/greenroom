import { Routes, Route } from "react-router-dom";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Dashboard from "./pages/Dashboard";
import Interview from "./pages/Interview";
import Results from "./pages/Results";
import RequireAuth from "./components/RequireAuth";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
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
    </Routes>
  );
}
