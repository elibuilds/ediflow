"use client";

import { useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { supabase } from "../lib/supabase";

type Sale = {
  listing_id: string; name: string; store: string; distance: string;
  quantity_available: number; sale_unit_price_usd: number;
  original_unit_price_usd: number; discount_percent: number; expires_in: string;
};
type StoreSummary = { items_scanned_today: number; items_rescued: number; items_on_flash_sale: number };
type RescueResult = { status: string; store_id: string; agent_output: string };
const backendUrl = process.env.NEXT_PUBLIC_EDIFLOW_BACKEND_URL ?? "http://127.0.0.1:8080";

export default function Home() {
  const [sales, setSales] = useState<Sale[]>([]);
  const [reserved, setReserved] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [session, setSession] = useState<Session | null>(null);
  const [storeId, setStoreId] = useState("");
  const [storeName, setStoreName] = useState("");
  const [summary, setSummary] = useState<StoreSummary | null>(null);
  const [rescueResult, setRescueResult] = useState<RescueResult | null>(null);
  const [showLogin, setShowLogin] = useState(false);
  const [authMode, setAuthMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  useEffect(() => {
    void loadSales();
    if (!supabase) return;
    void supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      if (data.session) void loadStore(data.session);
    });
    const { data: listener } = supabase.auth.onAuthStateChange((_event, next) => {
      setSession(next);
      if (next) void loadStore(next);
      else { setStoreId(""); setStoreName(""); setSummary(null); }
    });
    return () => listener.subscription.unsubscribe();
  }, []);

  async function loadSales() {
    try {
      const response = await fetch(`${backendUrl}/api/v1/flash-sales`);
      if (!response.ok) throw new Error();
      setSales((await response.json() as { listings: Sale[] }).listings);
    } catch { setError("The rescue network is unavailable. Please try again shortly."); }
    finally { setLoading(false); }
  }

  async function loadStore(currentSession: Session) {
    try {
      const response = await fetch(`${backendUrl}/api/v1/me`, {
        headers: { Authorization: `Bearer ${currentSession.access_token}` }
      });
      if (!response.ok) throw new Error("Your account does not have an active store membership.");
      const store = await response.json() as { store_id: string; store_name: string };
      setStoreId(store.store_id);
      setStoreName(store.store_name);
      await loadSummary(currentSession, store.store_id);
    } catch (membershipError) {
      setError(membershipError instanceof Error ? membershipError.message : "Unable to load your store workspace.");
    }
  }

  async function loadSummary(currentSession: Session, currentStoreId: string) {
    const response = await fetch(`${backendUrl}/api/v1/stores/${currentStoreId}/summary`, {
      headers: { Authorization: `Bearer ${currentSession.access_token}` }
    });
    if (!response.ok) throw new Error("Unable to load store summary");
    setSummary(await response.json() as StoreSummary);
  }

  async function reserveSale(sale: Sale) {
    if (reserved.includes(sale.listing_id)) return;
    try {
      const response = await fetch(`${backendUrl}/api/v1/flash-sales/${sale.listing_id}/reservations`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ quantity: 1, resident_reference: "demo-resident-01" })
      });
      const payload = await response.json() as { detail?: string };
      if (!response.ok) throw new Error(payload.detail ?? "Reservation failed");
      setReserved((current) => [...current, sale.listing_id]);
      await loadSales();
      setNotice(`${sale.name} reserved. We saved one for you at ${sale.store}.`);
    } catch (reservationError) {
      setError(reservationError instanceof Error ? reservationError.message : "Unable to reserve this rescue.");
    }
  }

  async function triggerRescue() {
    if (!session) { setShowLogin(true); return; }
    try {
      const response = await fetch("/api/rescue", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${session.access_token}` },
        body: "{}"
      });
      const payload = await response.json() as RescueResult & { detail?: string | { message?: string } };
      if (!response.ok) {
        const detail = typeof payload.detail === "string" ? payload.detail : payload.detail?.message ?? "Rescue request failed";
        throw new Error(detail);
      }
      setRescueResult(payload);
      setNotice("Rescue check completed. Inventory was routed by EdiFlow.");
      await loadSales();
      await loadSummary(session, storeId);
    } catch (rescueError) {
      setError(rescueError instanceof Error ? rescueError.message : "Unable to run the rescue check.");
    }
  }

  async function submitAuth(event: React.FormEvent) {
    event.preventDefault();
    if (!supabase) { setError("Supabase login is not configured."); return; }
    const result = authMode === "login"
      ? await supabase.auth.signInWithPassword({ email, password })
      : await supabase.auth.signUp({ email, password });
    if (result.error) { setError(result.error.message); return; }
    setShowLogin(false);
    setNotice(authMode === "login" ? "Welcome back. Your store workspace is ready." : "Account created. An administrator must assign your store membership.");
  }

  return <main>
    <nav className="topbar">
      <a className="brand" href="/"><span className="brand-mark">e</span><span>EdiFlow</span></a>
      <div className="nav-actions"><span className="live-pill"><span /> Network live</span>
        {session ? <button className="login-button" onClick={() => void supabase?.auth.signOut()}>Log out</button>
          : <a className="login-button" href="/login">Log in</a>}
      </div>
    </nav>
    <section className="hero shell"><div className="hero-copy">
      <p className="eyebrow">GOOD NEIGHBOR NETWORK</p><h1>Good food,<br /><em>better neighbors.</em></h1>
      <p className="hero-text">EdiFlow helps local stores rescue short-dated food before it becomes waste — moving it to food banks or into the hands of nearby neighbors.</p>
    </div><div className="hero-note"><span className="leaf">✦</span><p>Every rescue starts<br />with one good choice.</p></div></section>
    {notice && <div className="notice shell" role="status">{notice}<button onClick={() => setNotice("")}>Dismiss</button></div>}
    {error && <div className="error-notice shell" role="alert">{error}<button onClick={() => setError("")}>Dismiss</button></div>}
    <section className="shell content"><div className="section-heading"><div><p className="eyebrow">NEAR YOU</p><h2>Rescued today</h2></div><button className="text-button">⌖ Accra, Ghana <span>⌄</span></button></div>
      <div className="filter-row"><span className="result-count">{loading ? "Loading fresh finds…" : `${sales.length} fresh finds`}</span><button className="filter active-filter">All food <span>⌄</span></button><button className="filter">Closest first <span>⌄</span></button></div>
      <div className="sale-grid">{!loading && sales.length === 0 && <p className="muted">No rescues are available right now.</p>}
        {sales.map((sale) => { const isReserved = reserved.includes(sale.listing_id); return <article className="sale-card" key={sale.listing_id}>
          <div className={`food-image image-${sale.name.toLowerCase().includes("bread") ? "bread" : sale.name.toLowerCase().includes("apple") ? "fruit" : "pastry"}`}><span className="discount">{sale.discount_percent}% off</span><span className="food-symbol">◒</span></div>
          <div className="sale-body"><div className="sale-title"><h3>{sale.name}</h3><span className="heart">♡</span></div><p className="muted">{sale.store}</p><p className="muted small">{sale.distance} <span className="dot">·</span> Pick up by {sale.expires_in}</p><div className="price-row"><strong>${sale.sale_unit_price_usd.toFixed(2)}</strong><del>${sale.original_unit_price_usd.toFixed(2)}</del><span>{sale.quantity_available} left</span></div><button className={`reserve-button ${isReserved ? "reserved" : ""}`} onClick={() => void reserveSale(sale)} disabled={isReserved || sale.quantity_available === 0}>{isReserved ? "Reserved ✓" : sale.quantity_available === 0 ? "Sold out" : "Reserve a rescue"}</button></div>
        </article>; })}
      </div>
    </section>
    {showLogin && <section className="shell auth-panel"><form onSubmit={submitAuth}><p className="eyebrow">STORE ACCESS</p><h2>{authMode === "login" ? "Welcome back" : "Create a store account"}</h2><p className="muted">Sign in to manage inventory and run rescues for your assigned store.</p><label>Email<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label><label>Password<input type="password" minLength={6} value={password} onChange={(event) => setPassword(event.target.value)} required /></label><button className="primary-button" type="submit">{authMode === "login" ? "Log in" : "Create account"}</button><button className="text-button auth-switch" type="button" onClick={() => setAuthMode(authMode === "login" ? "signup" : "login")}>{authMode === "login" ? "Need an account? Sign up" : "Already have an account? Log in"}</button></form></section>}
    {session && storeId && <section className="shell store-panel"><div className="store-heading"><div><p className="eyebrow">STORE WORKSPACE</p><h2>{storeName || storeId}</h2></div><span className="connected"><span /> IMS connected</span></div><div className="metric-grid"><div className="metric"><span className="metric-icon">↗</span><strong>{summary?.items_scanned_today ?? "—"}</strong><span>items scanned today</span></div><div className="metric"><span className="metric-icon green">♥</span><strong>{summary?.items_rescued ?? "—"}</strong><span>items rescued</span></div><div className="metric"><span className="metric-icon orange">◷</span><strong>{summary?.items_on_flash_sale ?? "—"}</strong><span>on flash sale</span></div></div><div className="store-actions"><div><p className="eyebrow">NEXT ACTION</p><h3>Check today&apos;s short-dated inventory</h3><p className="muted">EdiFlow will route items to a pantry or publish a neighborhood sale.</p></div><button className="primary-button" onClick={() => void triggerRescue()}>Run rescue check <span>→</span></button></div>{rescueResult && <div className="rescue-result" role="status"><div className="rescue-result-heading"><div><p className="eyebrow">LATEST RESCUE RESULT</p><h3>Agent actions completed</h3></div><span className="result-status">{rescueResult.status}</span></div><pre>{rescueResult.agent_output}</pre></div>}</section>}
    <footer className="shell footer"><span>© 2026 EdiFlow</span><span>Built for the Good Neighbor track</span></footer>
  </main>;
}
