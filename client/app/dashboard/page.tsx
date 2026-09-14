"use client";

import { useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { supabase } from "../../lib/supabase";

type Store = { store_id: string; store_name: string };
type Summary = { items_scanned_today: number; items_rescued: number; items_on_flash_sale: number };
type RescueResult = { status: string; store_id: string; agent_output: string };
type VisionResult = { store_id: string; parsed_items: Array<{ name: string; quantity: number; estimated_shelf_life_hours: number }> };
const backendUrl = process.env.NEXT_PUBLIC_EDIFLOW_BACKEND_URL ?? "http://127.0.0.1:8080";

export default function Dashboard() {
  const [session, setSession] = useState<Session | null>(null);
  const [store, setStore] = useState<Store | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [result, setResult] = useState<RescueResult | null>(null);
  const [error, setError] = useState("");
  const [running, setRunning] = useState(false);
  const [photo, setPhoto] = useState<File | null>(null);
  const [visionResult, setVisionResult] = useState<VisionResult | null>(null);
  const [parsingPhoto, setParsingPhoto] = useState(false);

  useEffect(() => {
    if (!supabase) { setError("Supabase login is not configured."); return; }
    void supabase.auth.getSession().then(({ data }) => {
      if (!data.session) { window.location.href = "/login"; return; }
      setSession(data.session); void loadStore(data.session);
    });
  }, []);

  async function loadStore(current: Session) {
    const response = await fetch(`${backendUrl}/api/v1/me`, { headers: { Authorization: `Bearer ${current.access_token}` } });
    if (response.status === 401) { window.location.href = "/login"; return; }
    if (!response.ok) { setError("Your account does not have an active store membership."); return; }
    const currentStore = await response.json() as Store;
    setStore(currentStore);
    const summaryResponse = await fetch(`${backendUrl}/api/v1/stores/${currentStore.store_id}/summary`, { headers: { Authorization: `Bearer ${current.access_token}` } });
    if (summaryResponse.ok) setSummary(await summaryResponse.json() as Summary);
  }

  async function runRescue() {
    if (!session) return;
    setRunning(true); setError("");
    try {
      const response = await fetch("/api/rescue", { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${session.access_token}` }, body: "{}" });
      const payload = await response.json() as RescueResult & { detail?: string | { message?: string } };
      if (!response.ok) throw new Error(typeof payload.detail === "string" ? payload.detail : payload.detail?.message ?? "Rescue request failed");
      setResult(payload);
      if (store) await loadStore(session);
    } catch (rescueError) { setError(rescueError instanceof Error ? rescueError.message : "Unable to run the rescue check."); }
    finally { setRunning(false); }
  }

  async function parsePhoto() {
    if (!photo || !session || !store) return;
    setParsingPhoto(true); setError(""); setVisionResult(null);
    try {
      const imageBase64 = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
          const value = reader.result;
          if (typeof value !== "string") { reject(new Error("Unable to read the selected photo.")); return; }
          resolve(value.split(",")[1] ?? "");
        };
        reader.onerror = () => reject(new Error("Unable to read the selected photo."));
        reader.readAsDataURL(photo);
      });
      const response = await fetch(`${backendUrl}/api/v1/vision/parse`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${session.access_token}` },
        body: JSON.stringify({ image_base64: imageBase64, media_type: photo.type || "image/jpeg" }),
      });
      const payload = await response.json() as VisionResult & { detail?: string | { message?: string } };
      if (!response.ok) throw new Error(typeof payload.detail === "string" ? payload.detail : payload.detail?.message ?? "Photo parsing failed");
      setVisionResult(payload);
    } catch (photoError) {
      setError(photoError instanceof Error ? photoError.message : "Unable to parse the selected photo.");
    } finally { setParsingPhoto(false); }
  }

  return <main><nav className="topbar"><a className="brand" href="/"><span className="brand-mark">e</span><span>EdiFlow</span></a><div className="nav-actions"><a className="dashboard-link" href="/settings">Settings</a><button className="login-button" onClick={() => void supabase?.auth.signOut().then(() => { window.location.href = "/"; })}>Log out</button></div></nav><section className="shell dashboard-header"><p className="eyebrow">STORE WORKSPACE</p><h1>{store?.store_name ?? "Your store dashboard"}</h1><p className="hero-text">Monitor short-dated inventory and let EdiFlow coordinate the next rescue.</p></section>{error && <div className="error-notice shell" role="alert">{error}</div>}<section className="shell store-panel"><div className="store-heading"><div><p className="eyebrow">CONNECTED INVENTORY</p><h2>{store?.store_id ?? "Loading store…"}</h2></div><span className="connected"><span /> IMS connected</span></div><div className="metric-grid"><div className="metric"><span className="metric-icon">↗</span><strong>{summary?.items_scanned_today ?? "—"}</strong><span>items scanned today</span></div><div className="metric"><span className="metric-icon green">♥</span><strong>{summary?.items_rescued ?? "—"}</strong><span>items rescued</span></div><div className="metric"><span className="metric-icon orange">◷</span><strong>{summary?.items_on_flash_sale ?? "—"}</strong><span>on flash sale</span></div></div><div className="store-actions"><div><p className="eyebrow">NEXT ACTION</p><h3>Check today&apos;s short-dated inventory</h3><p className="muted">EdiFlow will route items to a pantry or publish a neighborhood sale.</p></div><button className="primary-button" onClick={() => void runRescue()} disabled={running}>{running ? "Running rescue…" : "Run rescue check →"}</button></div><div className="photo-panel"><div><p className="eyebrow">PHOTO INGESTION</p><h3>Scan unpackaged goods</h3><p className="muted">Upload a shelf or bakery photo and Bedrock will identify candidate items for review.</p></div><div className="photo-controls"><input type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => setPhoto(event.target.files?.[0] ?? null)} /><button className="primary-button" onClick={() => void parsePhoto()} disabled={!photo || parsingPhoto}>{parsingPhoto ? "Parsing photo…" : "Parse photo →"}</button></div>{visionResult && <div className="vision-result"><strong>Detected items</strong>{visionResult.parsed_items.length ? <ul>{visionResult.parsed_items.map((item) => <li key={`${item.name}-${item.quantity}`}>{item.name} — {item.quantity} ({item.estimated_shelf_life_hours}h estimated shelf life)</li>)}</ul> : <p className="muted">No food items were detected.</p>}</div>}</div>{result && <div className="rescue-result"><div className="rescue-result-heading"><div><p className="eyebrow">LATEST RESCUE RESULT</p><h3>Agent actions completed</h3></div><span className="result-status">{result.status}</span></div><pre>{result.agent_output}</pre></div>}</section><footer className="shell footer"><span>© 2026 EdiFlow</span><a href="/settings">Manage store settings →</a></footer></main>;
}
