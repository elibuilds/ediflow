"use client";

import { useEffect, useState } from "react";
import { supabase } from "../../lib/supabase";

export default function Settings() {
  const [checking, setChecking] = useState(true);
  const [provider, setProvider] = useState("Demo IMS");
  const [endpoint, setEndpoint] = useState("");
  const [location, setLocation] = useState("Main St., Accra");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    void supabase?.auth.getSession().then(({ data }) => {
      if (!data.session) window.location.href = "/login";
      setChecking(false);
    });
  }, []);

  function saveSettings(event: React.FormEvent) {
    event.preventDefault();
    localStorage.setItem("ediflow-store-settings", JSON.stringify({ provider, endpoint, location }));
    setSaved(true);
  }

  if (checking) return <main><div className="auth-page-content"><p className="muted">Loading settings…</p></div></main>;
  return <main><nav className="topbar"><a className="brand" href="/"><span className="brand-mark">e</span><span>EdiFlow</span></a><div className="nav-actions"><a className="dashboard-link" href="/dashboard">Dashboard</a><button className="login-button" onClick={() => void supabase?.auth.signOut().then(() => { window.location.href = "/"; })}>Log out</button></div></nav><section className="shell dashboard-header"><p className="eyebrow">STORE SETTINGS</p><h1>Connect your store.</h1><p className="hero-text">Configure where EdiFlow reads inventory and how your store appears to neighbors.</p></section><section className="shell settings-grid"><form className="settings-card" onSubmit={saveSettings}><p className="eyebrow">IMS INTEGRATION</p><h2>Inventory source</h2><p className="muted">Choose the system that provides short-dated inventory. Credentials should be entered only in the secured deployment environment.</p><label>Provider<select value={provider} onChange={(event) => setProvider(event.target.value)}><option>Demo IMS</option><option>Shopify</option><option>Square</option><option>Odoo</option></select></label><label>Inventory endpoint<input value={endpoint} onChange={(event) => setEndpoint(event.target.value)} placeholder="https://your-ims.example.com" /></label><button className="primary-button" type="submit">Save integration settings</button>{saved && <p className="auth-message" role="status">Settings saved for this browser. Vendor credentials are not stored here yet.</p>}</form><div className="settings-card"><p className="eyebrow">STORE PROFILE</p><h2>Local details</h2><label>Pickup location<input value={location} onChange={(event) => setLocation(event.target.value)} /></label><label>Public contact email<input type="email" placeholder="store@example.com" /></label><div className="settings-status"><span className="connected"><span /> {provider} ready</span><p className="muted">Pantry routing, flash-sale publishing, and volunteer dispatch use this store&apos;s inventory.</p></div></div></section><footer className="shell footer"><a href="/dashboard">← Back to dashboard</a><span>Store configuration</span></footer></main>;
}
