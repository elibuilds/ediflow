"use client";

import { useEffect, useState } from "react";

type Sale = {
  listing_id: string; name: string; store: string; distance: string;
  quantity_available: number; sale_unit_price_usd: number;
  original_unit_price_usd: number; discount_percent: number; expires_in: string;
};
const backendUrl = process.env.NEXT_PUBLIC_EDIFLOW_BACKEND_URL ?? "http://127.0.0.1:8080";

export default function Home() {
  const [sales, setSales] = useState<Sale[]>([]);
  const [reserved, setReserved] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => { void loadSales(); }, []);

  async function loadSales() {
    try {
      const response = await fetch(`${backendUrl}/api/v1/flash-sales`);
      if (!response.ok) throw new Error();
      setSales((await response.json() as { listings: Sale[] }).listings);
    } catch { setError("The rescue network is unavailable. Please try again shortly."); }
    finally { setLoading(false); }
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

  return <main>
    <nav className="topbar"><a className="brand" href="/"><span className="brand-mark">e</span><span>EdiFlow</span></a><div className="nav-actions"><span className="live-pill"><span /> Network live</span><a className="login-button" href="/login">Store login</a></div></nav>
    <section className="hero shell"><div className="hero-copy"><p className="eyebrow">GOOD NEIGHBOR NETWORK</p><h1>Good food,<br /><em>better neighbors.</em></h1><p className="hero-text">EdiFlow helps local stores rescue short-dated food before it becomes waste — moving it to food banks or into the hands of nearby neighbors.</p></div><div className="hero-note"><span className="leaf">✦</span><p>Every rescue starts<br />with one good choice.</p></div></section>
    {notice && <div className="notice shell" role="status">{notice}<button onClick={() => setNotice("")}>Dismiss</button></div>}
    {error && <div className="error-notice shell" role="alert">{error}<button onClick={() => setError("")}>Dismiss</button></div>}
    <section className="shell content"><div className="section-heading"><div><p className="eyebrow">NEAR YOU</p><h2>Rescued today</h2></div><button className="text-button">⌖ Accra, Ghana <span>⌄</span></button></div><div className="filter-row"><span className="result-count">{loading ? "Loading fresh finds…" : `${sales.length} fresh finds`}</span><button className="filter active-filter">All food <span>⌄</span></button><button className="filter">Closest first <span>⌄</span></button></div><div className="sale-grid">{!loading && sales.length === 0 && <p className="muted">No rescues are available right now.</p>}{sales.map((sale) => { const isReserved = reserved.includes(sale.listing_id); return <article className="sale-card" key={sale.listing_id}><div className={`food-image image-${sale.name.toLowerCase().includes("bread") ? "bread" : sale.name.toLowerCase().includes("apple") ? "fruit" : "pastry"}`}><span className="discount">{sale.discount_percent}% off</span><span className="food-symbol">◒</span></div><div className="sale-body"><div className="sale-title"><h3>{sale.name}</h3><span className="heart">♡</span></div><p className="muted">{sale.store}</p><p className="muted small">{sale.distance} <span className="dot">·</span> Pick up by {sale.expires_in}</p><div className="price-row"><strong>${sale.sale_unit_price_usd.toFixed(2)}</strong><del>${sale.original_unit_price_usd.toFixed(2)}</del><span>{sale.quantity_available} left</span></div><button className={`reserve-button ${isReserved ? "reserved" : ""}`} onClick={() => void reserveSale(sale)} disabled={isReserved || sale.quantity_available === 0}>{isReserved ? "Reserved ✓" : sale.quantity_available === 0 ? "Sold out" : "Reserve a rescue"}</button></div></article>; })}</div></section>
    <footer className="shell footer"><span>© 2026 EdiFlow</span><span>Built for the Good Neighbor track</span></footer>
  </main>;
}
