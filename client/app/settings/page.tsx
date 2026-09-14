"use client";

import { useEffect, useState } from "react";
import { supabase } from "../../lib/supabase";

type StoredSettings = {
  provider?: string;
  endpoint?: string;
  location?: string;
  autoSync?: boolean;
  approvalBeforePantry?: boolean;
  approvalBeforeFlashSale?: boolean;
  syncFrequency?: string;
  minimumUnits?: string;
};

export default function Settings() {
  const [checking, setChecking] = useState(true);
  const [provider, setProvider] = useState("Demo IMS");
  const [endpoint, setEndpoint] = useState("");
  const [location, setLocation] = useState("Main St., Accra");
  const [autoSync, setAutoSync] = useState(true);
  const [approvalBeforePantry, setApprovalBeforePantry] = useState(false);
  const [approvalBeforeFlashSale, setApprovalBeforeFlashSale] = useState(true);
  const [syncFrequency, setSyncFrequency] = useState("15");
  const [minimumUnits, setMinimumUnits] = useState("2");
  const [saved, setSaved] = useState(false);

  const backendUrl =
    process.env.NEXT_PUBLIC_EDIFLOW_BACKEND_URL ?? "http://127.0.0.1:8080";
  const demoImsUrl =
    `${backendUrl}/api/v1/demo-ims/inventory` +
    "?store_id=STORE-ACCRA-01&days_threshold=10";

  useEffect(() => {
    const stored = localStorage.getItem("ediflow-store-settings");

    if (stored) {
      try {
        const settings = JSON.parse(stored) as StoredSettings;

        if (settings.provider) setProvider(settings.provider);
        if (settings.endpoint) setEndpoint(settings.endpoint);
        if (settings.location) setLocation(settings.location);
        if (settings.autoSync !== undefined) setAutoSync(settings.autoSync);
        if (settings.approvalBeforePantry !== undefined) {
          setApprovalBeforePantry(settings.approvalBeforePantry);
        }
        if (settings.approvalBeforeFlashSale !== undefined) {
          setApprovalBeforeFlashSale(settings.approvalBeforeFlashSale);
        }
        if (settings.syncFrequency) setSyncFrequency(settings.syncFrequency);
        if (settings.minimumUnits) setMinimumUnits(settings.minimumUnits);
      } catch {
        localStorage.removeItem("ediflow-store-settings");
      }
    }

    if (!supabase) {
      window.location.href = "/login";
      return;
    }

    void supabase.auth.getSession().then(({ data }) => {
      if (!data.session) {
        window.location.href = "/login";
        return;
      }

      setChecking(false);
    });
  }, []);

  function saveSettings(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    localStorage.setItem(
      "ediflow-store-settings",
      JSON.stringify({
        provider,
        endpoint,
        location,
        autoSync,
        approvalBeforePantry,
        approvalBeforeFlashSale,
        syncFrequency,
        minimumUnits,
      })
    );
    setSaved(true);
  }

  async function logOut() {
    await supabase?.auth.signOut();
    window.location.href = "/";
  }

  if (checking) {
    return (
      <main>
        <div className="auth-page-content">
          <p className="muted">Loading settings…</p>
        </div>
      </main>
    );
  }

  return (
    <main>
      <nav className="topbar">
        <a className="brand" href="/">
          <span className="brand-mark">e</span>
          <span>EdiFlow</span>
        </a>
        <div className="nav-actions">
          <a className="dashboard-link" href="/dashboard">
            Dashboard
          </a>
          <button className="login-button" onClick={() => void logOut()}>
            Log out
          </button>
        </div>
      </nav>

      <section className="shell dashboard-header">
        <p className="eyebrow">STORE SETTINGS</p>
        <h1>Connect your store.</h1>
        <p className="hero-text">
          Configure where EdiFlow reads inventory and how your store appears to
          neighbors.
        </p>
      </section>

      <section className="shell settings-grid">
        <form className="settings-card" onSubmit={saveSettings}>
          <p className="eyebrow">IMS INTEGRATION</p>
          <h2>Inventory source</h2>
          <p className="muted">
            Choose the system that provides short-dated inventory. Credentials
            should be entered only in the secured deployment environment.
          </p>

          <label>
            Provider
            <select
              value={provider}
              onChange={(event) => setProvider(event.target.value)}
            >
              <option>Demo IMS</option>
              <option>Shopify</option>
              <option>Square</option>
              <option>Odoo</option>
            </select>
          </label>

          <label>
            Inventory endpoint
            <input
              value={endpoint}
              onChange={(event) => setEndpoint(event.target.value)}
              placeholder="https://your-ims.example.com"
            />
          </label>

          {provider === "Demo IMS" && (
            <div className="demo-feed">
              <small>Demo inventory feed</small>
              <a href={demoImsUrl} target="_blank" rel="noreferrer">
                {demoImsUrl}
              </a>
              <p className="muted">
                 this read-only JSON URL allows you demo an IMS connection.
              </p>
            </div>
          )}

          <button className="primary-button" type="submit">
            Save integration settings
          </button>

          {saved && (
            <p className="auth-message" role="status">
              Settings saved for this browser. Vendor credentials are not
              stored here yet.
            </p>
          )}
        </form>

        <div className="settings-card">
          <p className="eyebrow">AUTOMATION &amp; APPROVALS</p>
          <h2>Rescue controls</h2>
          <p className="muted">
            Choose how EdiFlow should monitor inventory and request approval
            for public actions.
          </p>

          <label className="setting-toggle">
            <input
              type="checkbox"
              checked={autoSync}
              onChange={(event) => setAutoSync(event.target.checked)}
            />
            <span>
              <strong>Automatically sync inventory</strong>
              <small>Check the connected IMS on a schedule.</small>
            </span>
          </label>

          <label>
            Sync frequency
            <select
              value={syncFrequency}
              onChange={(event) => setSyncFrequency(event.target.value)}
              disabled={!autoSync}
            >
              <option value="5">Every 5 minutes</option>
              <option value="15">Every 15 minutes</option>
              <option value="60">Every hour</option>
            </select>
          </label>

          <label className="setting-toggle">
            <input
              type="checkbox"
              checked={approvalBeforePantry}
              onChange={(event) =>
                setApprovalBeforePantry(event.target.checked)
              }
            />
            <span>
              <strong>Approve pantry dispatches</strong>
              <small>
                Pause pantry volunteer dispatch until a manager approves it.
              </small>
            </span>
          </label>

          <label className="setting-toggle">
            <input
              type="checkbox"
              checked={approvalBeforeFlashSale}
              onChange={(event) =>
                setApprovalBeforeFlashSale(event.target.checked)
              }
            />
            <span>
              <strong>Approve flash-sale publishing</strong>
              <small>
                Review pricing and quantities before neighbors can reserve.
              </small>
            </span>
          </label>

          <label>
            Minimum units to publish
            <input
              type="number"
              min="0"
              value={minimumUnits}
              onChange={(event) => setMinimumUnits(event.target.value)}
            />
            <small className="field-help">
              Items below this quantity stay out of flash sales.
            </small>
          </label>
        </div>

        <div className="settings-card">
          <p className="eyebrow">STORE PROFILE</p>
          <h2>Local details</h2>

          <label>
            Pickup location
            <input
              value={location}
              onChange={(event) => setLocation(event.target.value)}
            />
          </label>

          <label>
            Public contact email
            <input type="email" placeholder="store@example.com" />
          </label>

          <div className="settings-status">
            <span className="connected">
              <span /> {provider} ready
            </span>
            <p className="muted">
              Pantry routing, flash-sale publishing, and volunteer dispatch use
              this store&apos;s inventory.
            </p>
          </div>
        </div>
      </section>

      <footer className="shell footer">
        <a href="/dashboard">← Back to dashboard</a>
        <span>Store configuration</span>
      </footer>
    </main>
  );
}
