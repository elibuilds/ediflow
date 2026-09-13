"use client";

import { useEffect, useState } from "react";

type Sale = {
  listing_id: string;
  store_id: string;
  name: string;
  store: string;
  distance: string;
  quantity_available: number;
  sale_unit_price_usd: number;
  original_unit_price_usd: number;
  discount_percent: number;
  expires_in: string;
};

type StoreSummary = {
  items_scanned_today: number;
  items_rescued: number;
  items_on_flash_sale: number;
};

const backendUrl =
  process.env.NEXT_PUBLIC_EDIFLOW_BACKEND_URL ?? "http://127.0.0.1:8080";

export default function Home() {
  const [activeView, setActiveView] = useState<"resident" | "store">("resident");
  const [sales, setSales] = useState<Sale[]>([]);
  const [reserved, setReserved] = useState<string[]>([]);
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [summary, setSummary] = useState<StoreSummary | null>(null);

  useEffect(() => {
    void loadSales();
    void loadSummary();
  }, []);

  async function loadSales() {
    try {
      const response = await fetch(`${backendUrl}/api/v1/flash-sales`);
      if (!response.ok) throw new Error("Unable to load flash sales");
      const payload = (await response.json()) as { listings: Sale[] };
      setSales(payload.listings);
      setError("");
    } catch {
      setError("The rescue network is unavailable. Please try again shortly.");
    } finally {
      setLoading(false);
    }
  }

  async function loadSummary() {
    try {
      const response = await fetch(
        `${backendUrl}/api/v1/stores/STORE-ACCRA-01/summary`
      );
      if (!response.ok) throw new Error("Unable to load store summary");
      setSummary((await response.json()) as StoreSummary);
    } catch {
      setError("The store workspace is unavailable. Please try again shortly.");
    }
  }

  async function reserveSale(sale: Sale) {
    if (reserved.includes(sale.listing_id)) return;
    try {
      const response = await fetch(
        `${backendUrl}/api/v1/flash-sales/${sale.listing_id}/reservations`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            quantity: 1,
            resident_reference: "demo-resident-01"
          })
        }
      );
      const payload = (await response.json()) as { detail?: string };
      if (!response.ok) throw new Error(payload.detail ?? "Reservation failed");
      setReserved((current) => [...current, sale.listing_id]);
      await loadSales();
      setNotice(`${sale.name} reserved. We saved one for you at ${sale.store}.`);
    } catch (reservationError) {
      setError(
        reservationError instanceof Error
          ? reservationError.message
          : "Unable to reserve this rescue."
      );
    }
  }

  async function triggerRescue() {
    try {
      const response = await fetch("/api/rescue", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ store_id: "STORE-ACCRA-01" })
      });
      const payload = (await response.json()) as {
        detail?: string | { message?: string };
      };
      if (!response.ok) {
        const detail =
          typeof payload.detail === "string"
            ? payload.detail
            : payload.detail?.message ?? "Rescue request failed";
        throw new Error(detail);
      }
      setNotice("Rescue check completed. Inventory was routed by EdiFlow.");
      await loadSales();
      await loadSummary();
    } catch (rescueError) {
      setError(
        rescueError instanceof Error
          ? rescueError.message
          : "Unable to run the rescue check."
      );
    }
  }

  return (
    <main>
      <nav className="topbar">
        <a className="brand" href="/">
          <span className="brand-mark">e</span>
          <span>EdiFlow</span>
        </a>
        <div className="nav-actions">
          <span className="live-pill"><span /> Network live</span>
          <button className="avatar" aria-label="Open profile">PE</button>
        </div>
      </nav>

      <section className="hero shell">
        <div className="hero-copy">
          <p className="eyebrow">GOOD NEIGHBOR NETWORK</p>
          <h1>Good food,<br /><em>better neighbors.</em></h1>
          <p className="hero-text">
            EdiFlow helps local stores rescue short-dated food before it becomes waste —
            moving it to food banks or into the hands of nearby neighbors.
          </p>
          <div className="switcher" role="tablist" aria-label="Choose workspace">
            <button className={activeView === "resident" ? "active" : ""} onClick={() => setActiveView("resident")}>
              I&apos;m a neighbor
            </button>
            <button className={activeView === "store" ? "active" : ""} onClick={() => setActiveView("store")}>
              I run a store
            </button>
          </div>
        </div>
        <div className="hero-note">
          <span className="leaf">✦</span>
          <p>Every rescue starts<br />with one good choice.</p>
        </div>
      </section>

      {notice && <div className="notice shell" role="status">{notice}<button onClick={() => setNotice("")}>Dismiss</button></div>}
      {error && <div className="error-notice shell" role="alert">{error}<button onClick={() => setError("")}>Dismiss</button></div>}

      {activeView === "resident" ? (
        <section className="shell content">
          <div className="section-heading">
            <div>
              <p className="eyebrow">NEAR YOU</p>
              <h2>Rescued today</h2>
            </div>
            <button className="text-button">⌖ Accra, Ghana <span>⌄</span></button>
          </div>
          <div className="filter-row">
            <span className="result-count">{loading ? "Loading fresh finds…" : `${sales.length} fresh finds`}</span>
            <button className="filter active-filter">All food <span>⌄</span></button>
            <button className="filter">Closest first <span>⌄</span></button>
          </div>
          <div className="sale-grid">
            {!loading && sales.length === 0 && <p className="muted">No rescues are available right now.</p>}
            {sales.map((sale) => {
              const isReserved = reserved.includes(sale.listing_id);
              return (
                <article className="sale-card" key={sale.listing_id}>
                  <div className={`food-image image-${sale.listing_id.split("-")[1].toLowerCase()}`}>
                    <span className="discount">{sale.discount_percent}% off</span>
                    <span className="food-symbol">{sale.name.includes("fruit") ? "◌" : sale.name.includes("pastry") ? "✺" : "◒"}</span>
                  </div>
                  <div className="sale-body">
                    <div className="sale-title"><h3>{sale.name}</h3><span className="heart">♡</span></div>
                    <p className="muted">{sale.store}</p>
                    <p className="muted small">{sale.distance} <span className="dot">·</span> Pick up by {sale.expires_in}</p>
                    <div className="price-row">
                      <strong>${sale.sale_unit_price_usd.toFixed(2)}</strong>
                      <del>${sale.original_unit_price_usd.toFixed(2)}</del>
                      <span>{sale.quantity_available} left</span>
                    </div>
                    <button className={`reserve-button ${isReserved ? "reserved" : ""}`} onClick={() => reserveSale(sale)} disabled={isReserved || sale.quantity_available === 0}>
                      {isReserved ? "Reserved ✓" : sale.quantity_available === 0 ? "Sold out" : "Reserve a rescue"}
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      ) : (
        <section className="shell store-panel">
          <div className="store-heading">
            <div><p className="eyebrow">STORE WORKSPACE</p><h2>Corner Market <span>· Main St.</span></h2></div>
            <span className="connected"><span /> IMS connected</span>
          </div>
          <div className="metric-grid">
            <div className="metric"><span className="metric-icon">↗</span><strong>{summary?.items_scanned_today ?? "—"}</strong><span>items scanned today</span></div>
            <div className="metric"><span className="metric-icon green">♥</span><strong>{summary?.items_rescued ?? "—"}</strong><span>items rescued</span></div>
            <div className="metric"><span className="metric-icon orange">◷</span><strong>{summary?.items_on_flash_sale ?? "—"}</strong><span>on flash sale</span></div>
          </div>
          <div className="store-actions">
            <div><p className="eyebrow">NEXT ACTION</p><h3>Check today&apos;s short-dated inventory</h3><p className="muted">EdiFlow will route items to a pantry or publish a neighborhood sale.</p></div>
            <button className="primary-button" onClick={triggerRescue}>Run rescue check <span>→</span></button>
          </div>
          <div className="activity"><div><p className="eyebrow">RECENT ACTIVITY</p><p><span className="activity-dot green-dot" /> 24 milk units matched to Hope Community Pantry <small>12 min ago</small></p><p><span className="activity-dot orange-dot" /> 15 wheat loaves published for neighbors <small>18 min ago</small></p></div><button className="text-button">View all activity →</button></div>
        </section>
      )}

      <footer className="shell footer"><span>© 2026 EdiFlow</span><span>Built for the Good Neighbor track · <a href="https://agentsforhumans.devpost.com/rules">Agents for Humans</a></span></footer>
    </main>
  );
}
