import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "../lib/supabaseClient";

function EyeIcon({ open }) {
  return open ? (
    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
    </svg>
  ) : (
    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
    </svg>
  );
}

function PasswordField({ id, label, value, onChange, placeholder, right }) {
  const [show, setShow] = useState(false);
  return (
    <div>
      <div className="flex items-center justify-between">
        <label htmlFor={id} className="block text-sm text-mute">{label}</label>
        {right}
      </div>
      <div className="relative mt-1">
        <input
          id={id}
          type={show ? "text" : "password"}
          required
          minLength={6}
          value={value}
          onChange={onChange}
          className="w-full rounded-lg border border-white/10 bg-panel px-4 py-2.5 pr-10 text-cream outline-none focus:border-amber/50"
          placeholder={placeholder}
        />
        <button
          type="button"
          onClick={() => setShow((s) => !s)}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-mute transition hover:text-cream"
          tabIndex={-1}
          aria-label={show ? "Hide password" : "Show password"}
        >
          <EyeIcon open={show} />
        </button>
      </div>
    </div>
  );
}

export default function AuthForm({ mode }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [forgotPassword, setForgotPassword] = useState(false);
  const navigate = useNavigate();

  const isSignup = mode === "signup";

  const handleForgotPassword = async (e) => {
    e.preventDefault();
    setError("");
    setMessage("");
    setLoading(true);
    try {
      const { error: resetError } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/login`,
      });
      if (resetError) throw resetError;
      setMessage("Password reset link sent — check your email.");
    } catch (err) {
      setError(err.message || "Something went wrong. Try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setMessage("");

    if (isSignup && password !== confirmPassword) {
      setError("Passwords don't match.");
      return;
    }

    setLoading(true);
    try {
      if (isSignup) {
        const { error: signUpError } = await supabase.auth.signUp({ email, password });
        if (signUpError) throw signUpError;
        setMessage("Check your email to confirm your account, then sign in.");
      } else {
        const { error: signInError } = await supabase.auth.signInWithPassword({ email, password });
        if (signInError) throw signInError;
        navigate("/dashboard");
      }
    } catch (err) {
      setError(err.message || "Something went wrong. Try again.");
    } finally {
      setLoading(false);
    }
  };

  if (forgotPassword) {
    return (
      <div className="mx-auto flex min-h-[70vh] max-w-md flex-col justify-center px-6 py-16">
        <h1 className="font-display text-3xl tracking-tight">Reset your password</h1>
        <p className="mt-2 text-sm text-mute">
          Enter your email and we'll send you a link to set a new password.
        </p>
        <form onSubmit={handleForgotPassword} className="mt-8 space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm text-mute">Email</label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full rounded-lg border border-white/10 bg-panel px-4 py-2.5 text-cream outline-none focus:border-amber/50"
              placeholder="you@example.com"
            />
          </div>
          {error && <p className="text-sm text-coral">{error}</p>}
          {message && <p className="text-sm text-sage">{message}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-full bg-amber px-6 py-3 text-sm font-medium text-ink transition hover:bg-amberDark disabled:opacity-60"
          >
            {loading ? "Sending..." : "Send reset link"}
          </button>
        </form>
        <p className="mt-6 text-center text-sm text-mute">
          <button
            onClick={() => { setForgotPassword(false); setError(""); setMessage(""); }}
            className="text-amber hover:underline"
          >
            Back to sign in
          </button>
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-md flex-col justify-center px-6 py-16">
      <h1 className="font-display text-3xl tracking-tight">
        {isSignup ? "Set up your greenroom" : "Welcome back"}
      </h1>
      <p className="mt-2 text-sm text-mute">
        {isSignup
          ? "Create a free account to save your sessions and track progress over time."
          : "Sign in to pick up where you left off."}
      </p>

      <form onSubmit={handleSubmit} className="mt-8 space-y-4">
        <div>
          <label htmlFor="email" className="block text-sm text-mute">Email</label>
          <input
            id="email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 w-full rounded-lg border border-white/10 bg-panel px-4 py-2.5 text-cream outline-none focus:border-amber/50"
            placeholder="you@example.com"
          />
        </div>

        <PasswordField
          id="password"
          label="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="At least 6 characters"
          right={!isSignup && (
            <button
              type="button"
              onClick={() => { setForgotPassword(true); setError(""); setMessage(""); }}
              className="text-xs text-amber hover:underline"
            >
              Forgot password?
            </button>
          )}
        />

        {isSignup && (
          <PasswordField
            id="confirmPassword"
            label="Confirm password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="Re-enter your password"
          />
        )}

        {error && <p className="text-sm text-coral">{error}</p>}
        {message && <p className="text-sm text-sage">{message}</p>}

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-full bg-amber px-6 py-3 text-sm font-medium text-ink transition hover:bg-amberDark disabled:opacity-60"
        >
          {loading ? "One moment..." : isSignup ? "Create account" : "Sign in"}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-mute">
        {isSignup ? (
          <>Already have an account?{" "}<a href="/login" className="text-amber hover:underline">Sign in</a></>
        ) : (
          <>New here?{" "}<a href="/signup" className="text-amber hover:underline">Create an account</a></>
        )}
      </p>
    </div>
  );
}
