import { useState } from "react";
import qbData from "./data/qb_data.json";

// ─── Badge Glossary ───
const BADGE_GLOSSARY = {
  "Dual Threat": { desc: "Elite rushing production (600+ rush yards). Creates explosive plays with both arm and legs.", color: "#10b981" },
  "Mobile": { desc: "Meaningful rushing contributions (300+ rush yards). Extends plays and adds a run dimension.", color: "#34d399" },
  "Gunslinger": { desc: "Top 20% in average air yards. Pushes the ball downfield aggressively.", color: "#f59e0b" },
  "Aggressive": { desc: "Top 35% in average air yards. Willing to attack intermediate and deep zones.", color: "#fbbf24" },
  "Accurate": { desc: "Top 25% in completion percentage over expected (CPOE). Consistently beats accuracy expectations.", color: "#3b82f6" },
  "Clutch": { desc: "Top 20% in high-leverage EPA. Elevates performance when the game is on the line (win probability 20-80%).", color: "#8b5cf6" },
  "Composed": { desc: "Top 25% in pressure resilience. Maintains production when the pocket collapses.", color: "#06b6d4" },
  "Efficient": { desc: "Top 20% in throw EPA. Maximizes expected points on every pass attempt.", color: "#22c55e" },
  "Dynamic Runner": { desc: "Top 15% in rushing EPA per game. Rushing ability is a true weapon, not just a scramble threat.", color: "#14b8a6" },
  "Consistent": { desc: "Top 20% in positive play rate. High floor — produces positive outcomes on most throws.", color: "#60a5fa" },
  "Pocket Passer": { desc: "Under 200 rush yards. Wins from the pocket with arm talent and processing.", color: "#94a3b8" },
  "Volume": { desc: "7,000+ passing yards across the sample. Workhorse who shoulders a heavy passing load.", color: "#a78bfa" },
  "Big Play": { desc: "Top 20% in yards per attempt. Creates chunk plays and explosive passing production.", color: "#fb923c" },
  "Winner": { desc: "Top 20% in win percentage. Consistently leads teams to victories.", color: "#4ade80" },
  "Inaccurate": { desc: "Bottom 20% in CPOE. Consistently misses throws that the average QB completes.", color: "#ef4444" },
  "Turnover Prone": { desc: "Top 25% in interception rate. Puts the ball in danger too frequently.", color: "#dc2626" },
  "Holds Ball": { desc: "Top 20% in sack rate. Doesn't get the ball out quickly enough or escape pressure.", color: "#f87171" },
  "Conservative": { desc: "Bottom 20% in air yards and deep ball rate. Relies on short, safe throws that limit upside.", color: "#fb923c" },
  "Struggling": { desc: "Bottom 20% in throw EPA. Producing well below league average on pass attempts.", color: "#ef4444" },
  "Losing Record": { desc: "Bottom 20% in win percentage. Team results have been consistently poor.", color: "#b91c1c" },
  "Inconsistent": { desc: "Top 25% in negative play rate. Too many plays that actively hurt the offense.", color: "#f97316" },
  "Steady": { desc: "No standout traits in either direction. Adequate but unremarkable.", color: "#94a3b8" },
  "Developing": { desc: "Young or limited sample. Still finding footing at the NFL level.", color: "#64748b" },
};

const TEAM_COLORS = {
  ARI:"#97233F",ATL:"#A71930",BAL:"#241773",BUF:"#00338D",CAR:"#0085CA",CHI:"#0B162A",
  CIN:"#FB4F14",CLE:"#311D00",DAL:"#003594",DEN:"#FB4F14",DET:"#0076B6",GB:"#203731",
  HOU:"#03202F",IND:"#002C5F",JAX:"#006778",KC:"#E31837",LAC:"#0080C6",LAR:"#003594",
  LV:"#000000",MIA:"#008E97",MIN:"#4F2683",NE:"#002244",NO:"#D3BC8D",NYG:"#0B2265",
  NYJ:"#125740",PHI:"#004C54",PIT:"#FFB612",SEA:"#002244",SF:"#AA0000",TB:"#D50A0A",
  TEN:"#0C2340",WAS:"#5A1414",
};

const TIER_COLORS = { "Elite": "#f59e0b", "Blue Chip": "#3b82f6", "Quality Starter": "#22c55e", "Bridge / Backup": "#6b7280" };
const TIER_ORDER = ["Elite", "Blue Chip", "Quality Starter", "Bridge / Backup"];

const fmtEpa = (v) => (v > 0 ? "+" : "") + v.toFixed(3);
const fmtPct = (v) => v.toFixed(1) + "%";
const fmtCpoe = (v) => (v > 0 ? "+" : "") + v.toFixed(1);

function Badge({ name, onClick }) {
  const info = BADGE_GLOSSARY[name] || { color: "#64748b" };
  return (
    <span onClick={onClick} style={{
      display: "inline-block", padding: "3px 10px", borderRadius: 12, fontSize: 11, fontWeight: 600,
      fontFamily: "'JetBrains Mono', monospace", background: info.color + "22", color: info.color,
      border: `1px solid ${info.color}44`, cursor: "pointer", transition: "all 0.2s", letterSpacing: "0.3px",
    }} title={info.desc}>{name}</span>
  );
}

function RatingCircle({ rating, size = 52 }) {
  const pct = (rating - 40) / 59;
  const color = pct > 0.8 ? "#f59e0b" : pct > 0.6 ? "#3b82f6" : pct > 0.35 ? "#22c55e" : "#6b7280";
  const circ = 2 * Math.PI * (size / 2 - 4);
  return (
    <div style={{ position: "relative", width: size, height: size, flexShrink: 0 }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
        <circle cx={size/2} cy={size/2} r={size/2-4} fill="none" stroke="#1e293b" strokeWidth={3} />
        <circle cx={size/2} cy={size/2} r={size/2-4} fill="none" stroke={color} strokeWidth={3}
          strokeDasharray={circ} strokeDashoffset={circ * (1 - pct)} strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 0.8s ease" }} />
      </svg>
      <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center",
        fontFamily: "'JetBrains Mono', monospace", fontWeight: 700, fontSize: size * 0.36, color }}>{rating}</div>
    </div>
  );
}

function StatBar({ label, value, format = "epa", min = -0.3, max = 0.3 }) {
  const formatted = format === "pct" ? fmtPct(value) : format === "cpoe" ? fmtCpoe(value) : fmtEpa(value);
  const pct = Math.max(0, Math.min(1, (value - min) / (max - min)));
  const color = pct > 0.65 ? "#22c55e" : pct > 0.4 ? "#f59e0b" : "#ef4444";
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "#94a3b8", marginBottom: 3 }}>
        <span>{label}</span>
        <span style={{ fontFamily: "'JetBrains Mono', monospace", color }}>{formatted}</span>
      </div>
      <div style={{ height: 4, background: "#1e293b", borderRadius: 2 }}>
        <div style={{ height: "100%", width: `${pct * 100}%`, background: color, borderRadius: 2, transition: "width 0.5s ease" }} />
      </div>
    </div>
  );
}

function QBProfile({ qb }) {
  return (
    <div style={{ padding: "20px 24px", background: "#0d1321", borderTop: "1px solid #1e293b", animation: "slideDown 0.3s ease" }}>
      <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8, minWidth: 120 }}>
          {qb.headshotUrl ? (
            <img src={qb.headshotUrl} alt={qb.name} style={{
              width: 120, height: 87, objectFit: "cover", borderRadius: 8,
              border: `2px solid ${TEAM_COLORS[qb.team] || "#333"}`, background: "#0a0e14",
            }} onError={(e) => { e.target.style.display = "none"; }} />
          ) : (
            <div style={{ width: 120, height: 87, borderRadius: 8, background: "#1e293b",
              display: "flex", alignItems: "center", justifyContent: "center", fontSize: 32, color: "#475569" }}>🏈</div>
          )}
          <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 13, color: "#94a3b8" }}>
            {qb.wins}-{qb.losses} ({fmtPct(qb.winPct)})
          </div>
          <div style={{ fontSize: 11, color: "#64748b" }}>{qb.seasons}</div>
        </div>

        <div style={{ flex: 1, minWidth: 250 }}>
          <p style={{ color: "#cbd5e1", fontSize: 13, lineHeight: 1.7, margin: "0 0 16px 0", fontFamily: "'Outfit', sans-serif" }}>
            {qb.description}
          </p>
        </div>

        <div style={{ minWidth: 220, flex: "0 0 220px" }}>
          <StatBar label="Throw EPA" value={qb.throwEpa} min={-0.1} max={0.35} />
          <StatBar label="Pressure Resilience" value={qb.pressureResilience} min={-0.75} max={-0.1} />
          <StatBar label="High-Leverage EPA" value={qb.highLeverageEpa} min={-0.15} max={0.3} />
          <StatBar label="Rush EPA/Game" value={qb.rushEpaPerGame} min={-1.0} max={1.5} />
          <StatBar label="CPOE" value={qb.cpoe} format="cpoe" min={-5} max={8} />
          <StatBar label="YPA" value={qb.ypa} format="cpoe" min={5} max={9} />
        </div>

        <div style={{ minWidth: 160 }}>
          <div style={{ fontSize: 11, color: "#64748b", marginBottom: 8, textTransform: "uppercase", letterSpacing: 1 }}>Totals</div>
          {[["Pass Yards", qb.passYds.toLocaleString()], ["Pass TD", qb.passTd], ["INT", qb.int],
            ["Rush Yards", qb.rushYds.toLocaleString()], ["Rush TD", qb.rushTd],
            ["Sack Rate", fmtPct(qb.sackRate)], ["Comp %", fmtPct(qb.compPct)], ["GWD", qb.gwd],
          ].map(([label, val]) => (
            <div key={label} style={{ display: "flex", justifyContent: "space-between", padding: "4px 0",
              borderBottom: "1px solid #1e293b15", fontSize: 12 }}>
              <span style={{ color: "#64748b" }}>{label}</span>
              <span style={{ color: "#e2e8f0", fontFamily: "'JetBrains Mono', monospace" }}>{val}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function QBCard({ qb, isExpanded, onToggle, onBadgeClick }) {
  const teamColor = TEAM_COLORS[qb.team] || "#333";
  return (
    <div style={{ background: "#111827", borderRadius: 10, overflow: "hidden",
      borderLeft: `3px solid ${teamColor}`, transition: "all 0.2s", marginBottom: 2 }}>
      <div onClick={onToggle} style={{ display: "flex", alignItems: "center", gap: 16,
        padding: "14px 20px", cursor: "pointer", transition: "background 0.15s" }}
        onMouseEnter={(e) => e.currentTarget.style.background = "#1e293b44"}
        onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}>
        <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 14, fontWeight: 700,
          color: "#64748b", width: 28, textAlign: "right", flexShrink: 0 }}>{qb.rank}</div>
        {qb.headshotUrl ? (
          <img src={qb.headshotUrl} alt="" style={{ width: 36, height: 36, borderRadius: "50%",
            objectFit: "cover", border: `2px solid ${teamColor}`, flexShrink: 0, background: "#0a0e14" }}
            onError={(e) => { e.target.style.display = "none"; }} />
        ) : (
          <div style={{ width: 36, height: 36, borderRadius: "50%", background: teamColor + "33",
            display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14,
            flexShrink: 0, color: teamColor, fontWeight: 700 }}>{qb.team}</div>
        )}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontFamily: "'Outfit', sans-serif", fontWeight: 700, fontSize: 15, color: "#f1f5f9",
            overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {qb.name}
            <span style={{ marginLeft: 8, fontSize: 11, fontWeight: 500, color: teamColor, opacity: 0.8 }}>{qb.team}</span>
          </div>
          <div style={{ display: "flex", gap: 6, marginTop: 4, flexWrap: "wrap" }}>
            {qb.badges.map((b) => <Badge key={b} name={b} onClick={(e) => { e.stopPropagation(); onBadgeClick(b); }} />)}
          </div>
        </div>
        <div style={{ textAlign: "right", marginRight: 8, fontFamily: "'JetBrains Mono', monospace", fontSize: 12 }}>
          <div style={{ color: qb.throwEpa > 0.2 ? "#22c55e" : qb.throwEpa > 0.1 ? "#f59e0b" : "#ef4444" }}>
            {fmtEpa(qb.throwEpa)} EPA
          </div>
          <div style={{ color: "#64748b", fontSize: 11 }}>{qb.wins}-{qb.losses}</div>
        </div>
        <RatingCircle rating={qb.rating} size={48} />
        <div style={{ color: "#475569", fontSize: 18, transition: "transform 0.2s",
          transform: isExpanded ? "rotate(180deg)" : "rotate(0deg)" }}>▾</div>
      </div>
      {isExpanded && <QBProfile qb={qb} />}
    </div>
  );
}

function GlossaryModal({ badge, onClose }) {
  if (!badge) return null;
  const info = BADGE_GLOSSARY[badge];
  if (!info) return null;
  return (
    <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)",
      backdropFilter: "blur(4px)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
      <div onClick={(e) => e.stopPropagation()} style={{ background: "#111827", borderRadius: 12,
        padding: 28, maxWidth: 420, width: "90%", border: `1px solid ${info.color}44`,
        boxShadow: `0 0 40px ${info.color}22` }}>
        <span style={{ padding: "4px 14px", borderRadius: 16, fontSize: 14, fontWeight: 700,
          background: info.color + "22", color: info.color, border: `1px solid ${info.color}44`,
          fontFamily: "'JetBrains Mono', monospace" }}>{badge}</span>
        <p style={{ color: "#cbd5e1", fontSize: 14, lineHeight: 1.7, margin: "16px 0 0",
          fontFamily: "'Outfit', sans-serif" }}>{info.desc}</p>
        <button onClick={onClose} style={{ marginTop: 20, padding: "8px 20px", background: "#1e293b",
          border: "1px solid #334155", borderRadius: 8, color: "#94a3b8", fontSize: 13,
          cursor: "pointer", fontFamily: "'Outfit', sans-serif" }}>Got it</button>
      </div>
    </div>
  );
}

function FullGlossary({ onBadgeClick }) {
  const neg = ["Inaccurate","Turnover Prone","Holds Ball","Conservative","Struggling","Losing Record","Inconsistent"];
  const positive = Object.entries(BADGE_GLOSSARY).filter(([k]) => !neg.includes(k));
  const negative = Object.entries(BADGE_GLOSSARY).filter(([k]) => neg.includes(k));
  const Section = ({ title, items }) => (
    <div style={{ marginBottom: 24 }}>
      <h3 style={{ fontFamily: "'Outfit', sans-serif", fontSize: 14, color: "#94a3b8",
        textTransform: "uppercase", letterSpacing: 1.5, marginBottom: 12 }}>{title}</h3>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 8 }}>
        {items.map(([name, info]) => (
          <div key={name} onClick={() => onBadgeClick(name)} style={{
            padding: "10px 14px", background: "#111827", borderRadius: 8,
            border: `1px solid ${info.color}22`, cursor: "pointer", transition: "border-color 0.2s" }}
            onMouseEnter={(e) => e.currentTarget.style.borderColor = info.color + "66"}
            onMouseLeave={(e) => e.currentTarget.style.borderColor = info.color + "22"}>
            <span style={{ padding: "2px 8px", borderRadius: 10, fontSize: 11, fontWeight: 600,
              background: info.color + "22", color: info.color, fontFamily: "'JetBrains Mono', monospace" }}>{name}</span>
            <div style={{ fontSize: 12, color: "#94a3b8", lineHeight: 1.5, marginTop: 6,
              fontFamily: "'Outfit', sans-serif" }}>{info.desc}</div>
          </div>
        ))}
      </div>
    </div>
  );
  return <div><Section title="Positive Archetypes" items={positive} /><Section title="Negative Flags" items={negative} /></div>;
}

export default function App() {
  const [expandedQb, setExpandedQb] = useState(null);
  const [selectedBadge, setSelectedBadge] = useState(null);
  const [view, setView] = useState("rankings");
  const [tierFilter, setTierFilter] = useState("All");

  const filtered = tierFilter === "All" ? qbData : qbData.filter((q) => q.tier === tierFilter);
  const grouped = {};
  for (const tier of TIER_ORDER) {
    const tqbs = filtered.filter((q) => q.tier === tier);
    if (tqbs.length > 0) grouped[tier] = tqbs;
  }

  return (
    <div style={{ minHeight: "100vh", background: "#0a0e14", color: "#e2e8f0", fontFamily: "'Outfit', sans-serif" }}>
      <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet" />
      <style>{`
        @keyframes slideDown { from { opacity: 0; max-height: 0; } to { opacity: 1; max-height: 600px; } }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: #0a0e14; }
        ::selection { background: #f59e0b44; }
      `}</style>

      <header style={{ padding: "32px 40px 24px", borderBottom: "1px solid #1e293b",
        background: "linear-gradient(180deg, #111827 0%, #0a0e14 100%)" }}>
        <div style={{ maxWidth: 1000, margin: "0 auto" }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 12, marginBottom: 4 }}>
            <h1 style={{ fontSize: 28, fontWeight: 900, letterSpacing: "-0.5px",
              background: "linear-gradient(135deg, #f59e0b, #ef4444)",
              WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>QB Intelligence</h1>
            <span style={{ color: "#475569", fontSize: 13, fontFamily: "'JetBrains Mono', monospace" }}>
              v2.0 — Two-Pillar Rating</span>
          </div>
          <p style={{ color: "#64748b", fontSize: 13, marginBottom: 20 }}>
            2024–2025 blended · {qbData.length} quarterbacks · Click any QB to expand their profile</p>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            {["rankings", "glossary"].map((v) => (
              <button key={v} onClick={() => setView(v)} style={{
                padding: "6px 16px", borderRadius: 8, fontSize: 13, fontWeight: 600,
                background: view === v ? "#f59e0b22" : "transparent",
                color: view === v ? "#f59e0b" : "#64748b",
                border: view === v ? "1px solid #f59e0b44" : "1px solid transparent",
                cursor: "pointer", textTransform: "capitalize", fontFamily: "'Outfit', sans-serif",
              }}>{v === "glossary" ? "Badge Glossary" : v}</button>
            ))}
            {view === "rankings" && (
              <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
                {["All", ...TIER_ORDER].map((t) => (
                  <button key={t} onClick={() => setTierFilter(t)} style={{
                    padding: "4px 12px", borderRadius: 6, fontSize: 11, fontWeight: 600,
                    background: tierFilter === t ? (TIER_COLORS[t] || "#475569") + "22" : "transparent",
                    color: tierFilter === t ? (TIER_COLORS[t] || "#94a3b8") : "#475569",
                    border: `1px solid ${tierFilter === t ? (TIER_COLORS[t] || "#475569") + "44" : "transparent"}`,
                    cursor: "pointer", fontFamily: "'JetBrains Mono', monospace",
                  }}>{t}</button>
                ))}
              </div>
            )}
          </div>
        </div>
      </header>

      <main style={{ maxWidth: 1000, margin: "0 auto", padding: "24px 40px 60px" }}>
        {view === "rankings" ? (
          Object.entries(grouped).map(([tier, qbs]) => (
            <div key={tier} style={{ marginBottom: 32 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12,
                padding: "0 0 8px 0", borderBottom: `2px solid ${TIER_COLORS[tier]}33` }}>
                <span style={{ fontSize: 12, fontWeight: 700, color: TIER_COLORS[tier],
                  fontFamily: "'JetBrains Mono', monospace", textTransform: "uppercase",
                  letterSpacing: 1.5 }}>{tier}</span>
                <span style={{ fontSize: 11, color: "#475569" }}>{qbs.length} QB{qbs.length > 1 ? "s" : ""}</span>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                {qbs.map((qb) => (
                  <QBCard key={qb.name} qb={qb} isExpanded={expandedQb === qb.name}
                    onToggle={() => setExpandedQb(expandedQb === qb.name ? null : qb.name)}
                    onBadgeClick={setSelectedBadge} />
                ))}
              </div>
            </div>
          ))
        ) : (
          <FullGlossary onBadgeClick={setSelectedBadge} />
        )}
      </main>

      <GlossaryModal badge={selectedBadge} onClose={() => setSelectedBadge(null)} />
    </div>
  );
}
