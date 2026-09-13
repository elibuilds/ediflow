"use client";

import { useState } from "react";

type Sale = {
  listing_id: string;
  name: string;
  store: string;
  distance: string;
  quantity_available: number;
  sale_unit_price_usd: number;
  original_unit_price_usd: number;
  discount_percent: number;
  expires_in: string;
};

const demoSales: Sale[] = [
  {
    listing_id: "SALE-BREAD-01",
    name: "Artisanal wheat loaf",
    store: "Corner Market · Main St.",
    distance: "0.8 km away",
    quantity_available: 15,
    sale_unit_price_usd: 1.2,
    original_unit_price_usd: 3,
    discount_percent: 60,
    expires_in: "Today · 6:30 PM"
  },
  {
    listing_id: "SALE-FRUIT-02",
    name: "Seasonal fruit basket",
    store: "Green Basket Foods",
    distance: "1.4 km away",
    quantity_available: 8,
    sale_unit_price_usd: 2.5,
    original_unit_price_usd: 5,
    discount_percent: 50,
    expires_in: "Tomorrow · 10:00 AM"
  },
  {
    listing_id: "SALE-PASTRY-03",
    name: "Fresh pastry box",
    store: "Corner Market · Main St.",
    distance: "0.8 km away",
    quantity_available: 4,
    sale_unit_price_usd: 3.15,
    original_unit_price_usd: 7,
    discount_percent: 55,
    expires_in: "Tomorrow · 8:00 AM"
  }
];

export default function Home() {
  const [activeView, setActiveView] = useState<"resident" | "store">("resident");
  const [sales, setSales] = useState(demoSales);
  const [reserved, setReserved] = useState<string[]>([]);
  const [notice, setNotice] = useState("");

  function reserveSale(sale: Sale) {
    if (reserved.includes(sale.listing_id)) return;
    setReserved((current) => [...current, sale.listing_id]);
    setSales((current) =>
      current.map((item) =>
        item.listing_id === sale.listing_id
          ? { ...item, quantity_available: item.quantity_available - 1 }
          : item
      )
    );
    setNotice(`${sale.name} reserved. We saved one for you at ${sale.store}.`);
  }

  function triggerRescue() {
    setNotice("Rescue request queued for Corner Market. The IMS feed will be checked next.");
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
            <span className="result-count">{sales.length} fresh finds</span>
            <button className="filter active-filter">All food <span>⌄</span></button>
            <button className="filter">Closest first <span>⌄</span></button>
          </div>
          <div className="sale-grid">
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
            <div className="metric"><span className="metric-icon">↗</span><strong>49</strong><span>items scanned today</span></div>
            <div className="metric"><span className="metric-icon green">♥</span><strong>34</strong><span>items rescued</span></div>
            <div className="metric"><span className="metric-icon orange">◷</span><strong>15</strong><span>on flash sale</span></div>
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
