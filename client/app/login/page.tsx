"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "../../lib/supabase";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setMessage("");
    if (!supabase) {
      setError("Supabase login is not configured. Add the public Supabase URL and anon key.");
      return;
    }
    setSubmitting(true);
    const result = mode === "login"
      ? await supabase.auth.signInWithPassword({ email, password })
      : await supabase.auth.signUp({ email, password });
    setSubmitting(false);
    if (result.error) {
      setError(result.error.message);
      return;
    }
    if (mode === "signup" && !result.data.session) {
      setMessage("Account created. Check your email to confirm it, then log in.");
      return;
    }
    router.push("/");
  }

  return (
    <main className="auth-page">
      <nav className="topbar">
        <a className="brand" href="/">
          <span className="brand-mark">e</span>
          <span>EdiFlow</span>
        </a>
        <a className="login-button" href="/">Back to listings</a>
      </nav>
      <section className="auth-page-content">
        <div className="auth-panel auth-panel-page">
          <p className="eyebrow">STORE ACCESS</p>
          <h1>{mode === "login" ? "Welcome back." : "Join EdiFlow."}</h1>
          <p className="hero-text">
            Sign in to manage inventory and run rescues for your assigned store.
          </p>
          <form onSubmit={submit}>
            <label>
              Email
              <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
            </label>
            <label>
              Password
              <input type="password" minLength={6} value={password} onChange={(event) => setPassword(event.target.value)} required />
            </label>
            {error && <p className="auth-error" role="alert">{error}</p>}
            {message && <p className="auth-message" role="status">{message}</p>}
            <button className="primary-button" type="submit" disabled={submitting}>
              {submitting ? "Please wait…" : mode === "login" ? "Log in" : "Create account"}
            </button>
          </form>
          <button className="text-button auth-switch" type="button" onClick={() => setMode(mode === "login" ? "signup" : "login")}>
            {mode === "login" ? "Need an account? Sign up" : "Already have an account? Log in"}
          </button>
        </div>
      </section>
    </main>
  );
}
