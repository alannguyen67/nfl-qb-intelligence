import { useState, useMemo } from "react";
import QB_DATA_RAW from "./data/qb_data.json";

// ── NFL Team colors ──
const TEAM_COLORS = {
  KC: "#E31837", BUF: "#00338D", PHI: "#004C54", DET: "#0076B6",
  SF: "#AA0000", BAL: "#241773", CIN: "#FB4F14", DAL: "#003594",
  GB: "#203731", MIA: "#008E97", LAR: "#003594", MIN: "#4F2683",
  SEA: "#002244", HOU: "#03202F", LAC: "#0080C6", PIT: "#FFB612",
  TB: "#D50A0A", ATL: "#A71930", CHI: "#0B162A", NO: "#D3BC8D",
  ARI: "#97233F", WAS: "#773141", NYJ: "#125740", NYG: "#0B2265",
  IND: "#002C5F", DEN: "#FB4F14", CLE: "#311D00", LV: "#000000",
  TEN: "#4B92DB", JAX: "#006778", NE: "#002244", CAR: "#0085CA",
};

const TIER_CONFIG = {
  "Elite": { color: "#F5C518", bg: "rgba(245,197,24,0.06)", border: "rgba(245,197,24,0.25)", icon: "★" },
  "Blue Chip": { color: "#4ECDC4", bg: "rgba(78,205,196,0.06)", border: "rgba(78,205,196,0.2)", icon: "◆" },
  "Quality Starter": { color: "#7B8CDE", bg: "rgba(123,140,222,0.06)", border: "rgba(123,140,222,0.15)", icon: "●" },
  "Bridge / Backup": { color: "#8B8B8B", bg: "rgba(139,139,139,0.05)", border: "rgba(139,139,139,0.12)", icon: "○" },
};

const BADGE_COLORS = {
  "Dual Threat": "#F5C518", "Clutch": "#E8453C", "Aggressive": "#FF6B35",
  "Mobile": "#4ECDC4", "Efficient": "#2ECC71", "Playmaker": "#9B59B6",
  "Gunslinger": "#E74C3C", "Creative": "#F39C12", "Accurate": "#3498DB",
  "Pocket Passer": "#7B8CDE", "Composed": "#1ABC9C", "Rising": "#2ECC71",
  "Volume": "#95A5A6", "Veteran": "#7F8C8D", "Game Manager": "#85929E",
  "Steady": "#5DADE2", "Developing": "#F4D03F", "Quick Release": "#48C9B0",
  "Inconsistent": "#E67E22", "Conservative": "#85929E", "Arm Talent": "#8E44AD",
  "Fragile": "#C0392B", "Inaccurate": "#E74C3C", "Turnover Prone": "#C0392B",
  "Declining": "#7F8C8D", "Undersized": "#BDC3C7", "Holds Ball": "#E67E22",
  "Struggling": "#C0392B",
};

const STAT_COLUMNS = [
  { key: "rank", label: "#", w: "48px" },
  { key: "name", label: "QUARTERBACK", w: "180px" },
  { key: "team", label: "TM", w: "56px" },
  { key: "rating", label: "RTG", w: "64px", highlight: true },
  { key: "epa", label: "EPA/PLAY", w: "90px", format: v => v > 0 ? `+${v.toFixed(3)}` : v.toFixed(3), colorScale: true },
  { key: "cpoe", label: "CPOE", w: "72px", format: v => v > 0 ? `+${v.toFixed(1)}` : v.toFixed(1), colorScale: true },
  { key: "compPct", label: "CMP%", w: "72px", format: v => v.toFixed(1) },
  { key: "passYds", label: "YDS", w: "72px", format: v => v.toLocaleString() },
  { key: "passTd", label: "TD", w: "56px" },
  { key: "int", label: "INT", w: "56px", invertColor: true },
  { key: "sackRate", label: "SK%", w: "64px", format: v => v.toFixed(1), invertColor: true },
  { key: "rushYds", label: "RUSH", w: "72px" },
  { key: "rushTd", label: "RTD", w: "56px" },
];

function getStatColor(key, value, allValues, invert = false) {
  if (!allValues || allValues.length === 0) return "#C8CCD0";
  const min = Math.min(...allValues);
  const max = Math.max(...allValues);
  if (max === min) return "#C8CCD0";
  let pct = (value - min) / (max - min);
  if (invert) pct = 1 - pct;
  if (pct > 0.75) return "#2ECC71";
  if (pct > 0.5) return "#7DCEA0";
  if (pct > 0.25) return "#E67E22";
  return "#E74C3C";
}

function Badge({ label }) {
  const color = BADGE_COLORS[label] || "#7B8CDE";
  return (
    <span style={{
      display: "inline-block",
      padding: "2px 8px",
      borderRadius: "3px",
      fontSize: "10px",
      fontWeight: 600,
      letterSpacing: "0.5px",
      textTransform: "uppercase",
      color: color,
      background: `${color}18`,
      border: `1px solid ${color}35`,
      marginRight: "5px",
      marginBottom: "3px",
      fontFamily: "'JetBrains Mono', monospace",
    }}>
      {label}
    </span>
  );
}

function QBCard({ qb, index }) {
  const tierCfg = TIER_CONFIG[qb.tier] || TIER_CONFIG["Quality Starter"];
  const teamColor = TEAM_COLORS[qb.team] || "#666";
  const [hovered, setHovered] = useState(false);

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background: hovered ? "rgba(255,255,255,0.04)" : tierCfg.bg,
        border: `1px solid ${hovered ? tierCfg.color + "50" : tierCfg.border}`,
        borderRadius: "8px",
        padding: "20px 24px",
        display: "flex",
        alignItems: "center",
        gap: "20px",
        transition: "all 0.25s ease",
        cursor: "default",
        position: "relative",
        overflow: "hidden",
        animation: `fadeSlideIn 0.4s ease ${index * 0.04}s both`,
      }}
    >
      <div style={{ minWidth: "44px", textAlign: "center" }}>
        <div style={{
          fontSize: "28px", fontWeight: 800, color: tierCfg.color,
          fontFamily: "'Outfit', sans-serif", lineHeight: 1,
        }}>{qb.rank}</div>
      </div>

      <div style={{
        width: "3px", height: "52px",
        background: `linear-gradient(to bottom, ${teamColor}, ${teamColor}44)`,
        borderRadius: "2px", flexShrink: 0,
      }} />

      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: "10px", marginBottom: "4px", flexWrap: "wrap" }}>
          <span style={{
            fontSize: "18px", fontWeight: 700, color: "#E8EAED",
            fontFamily: "'Outfit', sans-serif", letterSpacing: "-0.02em",
          }}>{qb.name}</span>
          <span style={{
            fontSize: "11px", fontWeight: 700, color: teamColor,
            background: `${teamColor}20`, padding: "1px 6px", borderRadius: "3px",
            fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.5px",
          }}>{qb.team}</span>
          <span style={{
            fontSize: "10px", fontWeight: 500, color: tierCfg.color, opacity: 0.7,
            fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.5px", textTransform: "uppercase",
          }}>{tierCfg.icon} {qb.tier}</span>
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "2px" }}>
          {(qb.badges || []).map(b => <Badge key={b} label={b} />)}
        </div>
      </div>

      <div style={{ display: "flex", gap: "20px", flexShrink: 0, flexWrap: "wrap" }}>
        {[
          { label: "EPA/PLAY", value: qb.epa > 0 ? `+${qb.epa.toFixed(3)}` : qb.epa.toFixed(3), color: qb.epa > 0.1 ? "#2ECC71" : qb.epa > 0 ? "#7DCEA0" : "#E74C3C" },
          { label: "CPOE", value: qb.cpoe > 0 ? `+${qb.cpoe.toFixed(1)}` : qb.cpoe.toFixed(1), color: qb.cpoe > 1 ? "#2ECC71" : qb.cpoe > 0 ? "#7DCEA0" : "#E74C3C" },
          { label: "CMP%", value: qb.compPct.toFixed(1), color: qb.compPct > 66 ? "#2ECC71" : qb.compPct > 62 ? "#7DCEA0" : "#E74C3C" },
          { label: "TD:INT", value: `${qb.passTd}:${qb.int}`, color: (qb.passTd / Math.max(qb.int, 1)) > 2.5 ? "#2ECC71" : "#C8CCD0" },
        ].map(s => (
          <div key={s.label} style={{ textAlign: "center", minWidth: "56px" }}>
            <div style={{
              fontSize: "15px", fontWeight: 700, color: s.color,
              fontFamily: "'JetBrains Mono', monospace", lineHeight: 1.2,
            }}>{s.value}</div>
            <div style={{
              fontSize: "9px", color: "#6B7280", fontWeight: 600,
              letterSpacing: "0.8px", fontFamily: "'JetBrains Mono', monospace", marginTop: "2px",
            }}>{s.label}</div>
          </div>
        ))}
      </div>

      <div style={{
        width: "48px", height: "48px", borderRadius: "50%",
        border: `2px solid ${tierCfg.color}60`,
        display: "flex", alignItems: "center", justifyContent: "center",
        flexShrink: 0, background: `${tierCfg.color}10`,
      }}>
        <span style={{
          fontSize: "16px", fontWeight: 800, color: tierCfg.color,
          fontFamily: "'Outfit', sans-serif",
        }}>{qb.rating}</span>
      </div>
    </div>
  );
}

function StatsTable({ data, sortKey, sortDir, onSort }) {
  const allValues = useMemo(() => {
    const vals = {};
    STAT_COLUMNS.forEach(col => {
      if (col.colorScale || col.invertColor) {
        vals[col.key] = data.map(qb => qb[col.key]);
      }
    });
    return vals;
  }, [data]);

  return (
    <div style={{
      overflowX: "auto", borderRadius: "8px",
      border: "1px solid rgba(255,255,255,0.06)",
    }}>
      <table style={{
        width: "100%", borderCollapse: "collapse",
        fontFamily: "'JetBrains Mono', monospace", fontSize: "12px",
      }}>
        <thead>
          <tr>
            {STAT_COLUMNS.map(col => (
              <th key={col.key} onClick={() => onSort(col.key)} style={{
                padding: "12px 10px",
                textAlign: col.key === "name" ? "left" : "center",
                color: sortKey === col.key ? "#F5C518" : "#6B7280",
                fontSize: "10px", fontWeight: 700, letterSpacing: "1px",
                borderBottom: "1px solid rgba(255,255,255,0.08)",
                cursor: "pointer", userSelect: "none",
                background: "rgba(0,0,0,0.3)", position: "sticky", top: 0,
                whiteSpace: "nowrap", transition: "color 0.2s", width: col.w,
              }}>
                {col.label}
                {sortKey === col.key && (
                  <span style={{ marginLeft: "4px", fontSize: "8px" }}>
                    {sortDir === "asc" ? "▲" : "▼"}
                  </span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((qb) => (
            <tr key={qb.name} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)", transition: "background 0.15s" }}
              onMouseEnter={e => e.currentTarget.style.background = "rgba(255,255,255,0.03)"}
              onMouseLeave={e => e.currentTarget.style.background = "transparent"}
            >
              {STAT_COLUMNS.map(col => {
                const val = qb[col.key];
                const formatted = col.format ? col.format(val) : val;
                let color = "#C8CCD0";
                if (col.colorScale) color = getStatColor(col.key, val, allValues[col.key]);
                if (col.invertColor) color = getStatColor(col.key, val, allValues[col.key], true);
                if (col.key === "name") color = "#E8EAED";
                if (col.key === "rank") color = "#6B7280";
                if (col.key === "team") color = TEAM_COLORS[val] || "#888";

                return (
                  <td key={col.key} style={{
                    padding: "10px 10px",
                    textAlign: col.key === "name" ? "left" : "center",
                    color, fontWeight: col.highlight ? 800 : (col.key === "name" ? 600 : 400),
                    fontSize: col.highlight ? "13px" : "12px",
                    fontFamily: col.key === "name" ? "'Outfit', sans-serif" : "'JetBrains Mono', monospace",
                  }}>
                    {col.key === "rating" ? (
                      <span style={{
                        background: `${TIER_CONFIG[qb.tier]?.color || "#888"}20`,
                        padding: "2px 8px", borderRadius: "4px",
                        color: TIER_CONFIG[qb.tier]?.color || "#888",
                      }}>{formatted}</span>
                    ) : formatted}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function App() {
  const [view, setView] = useState("rankings");
  const [tierFilter, setTierFilter] = useState("All");
  const [sortKey, setSortKey] = useState("rank");
  const [sortDir, setSortDir] = useState("asc");

  const tiers = ["All", "Elite", "Blue Chip", "Quality Starter", "Bridge / Backup"];

  const filteredData = useMemo(() => {
    let d = [...QB_DATA_RAW];
    if (tierFilter !== "All") d = d.filter(qb => qb.tier === tierFilter);
    return d;
  }, [tierFilter]);

  const sortedTableData = useMemo(() => {
    let d = [...filteredData];
    d.sort((a, b) => {
      const av = a[sortKey], bv = b[sortKey];
      if (typeof av === "string") return sortDir === "asc" ? av.localeCompare(bv) : bv.localeCompare(av);
      return sortDir === "asc" ? av - bv : bv - av;
    });
    return d;
  }, [filteredData, sortKey, sortDir]);

  function handleSort(key) {
    if (sortKey === key) setSortDir(d => d === "asc" ? "desc" : "asc");
    else { setSortKey(key); setSortDir(key === "name" || key === "team" ? "asc" : "desc"); }
  }

  const tierGroups = useMemo(() => {
    const groups = {};
    filteredData.forEach(qb => {
      if (!groups[qb.tier]) groups[qb.tier] = [];
      groups[qb.tier].push(qb);
    });
    return groups;
  }, [filteredData]);

  return (
    <div style={{
      minHeight: "100vh", background: "#0A0E14", color: "#C8CCD0",
      fontFamily: "'Outfit', sans-serif",
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700&display=swap');
        @keyframes fadeSlideIn {
          from { opacity: 0; transform: translateY(12px); }
          to { opacity: 1; transform: translateY(0); }
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { height: 6px; width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 3px; }
      `}</style>

      <header style={{
        borderBottom: "1px solid rgba(255,255,255,0.06)", padding: "0 40px",
        background: "rgba(10,14,20,0.95)", backdropFilter: "blur(12px)",
        position: "sticky", top: 0, zIndex: 100,
      }}>
        <div style={{
          maxWidth: "1200px", margin: "0 auto", display: "flex",
          alignItems: "center", justifyContent: "space-between", height: "64px",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
            <div style={{ fontSize: "20px", fontWeight: 900, letterSpacing: "-0.03em", color: "#E8EAED" }}>
              <span style={{ color: "#F5C518" }}>QB</span> Intelligence
            </div>
            <div style={{
              fontSize: "10px", color: "#4B5563", fontFamily: "'JetBrains Mono', monospace",
              letterSpacing: "1px", fontWeight: 500,
              borderLeft: "1px solid rgba(255,255,255,0.08)", paddingLeft: "16px",
            }}>
              2025 SEASON — ADVANCED ANALYTICS
            </div>
          </div>

          <div style={{ display: "flex", gap: "4px", background: "rgba(255,255,255,0.04)", borderRadius: "6px", padding: "3px" }}>
            {[{ id: "rankings", label: "Rankings" }, { id: "stats", label: "Stats Table" }].map(tab => (
              <button key={tab.id} onClick={() => setView(tab.id)} style={{
                padding: "6px 16px", borderRadius: "4px", border: "none", cursor: "pointer",
                fontSize: "12px", fontWeight: 600, fontFamily: "'Outfit', sans-serif",
                letterSpacing: "0.02em", transition: "all 0.2s",
                color: view === tab.id ? "#0A0E14" : "#6B7280",
                background: view === tab.id ? "#F5C518" : "transparent",
              }}>{tab.label}</button>
            ))}
          </div>
        </div>
      </header>

      <main style={{ maxWidth: "1200px", margin: "0 auto", padding: "32px 40px 80px" }}>
        <div style={{ display: "flex", gap: "8px", marginBottom: "28px", flexWrap: "wrap" }}>
          {tiers.map(t => {
            const active = tierFilter === t;
            const cfg = TIER_CONFIG[t];
            const color = cfg?.color || "#C8CCD0";
            return (
              <button key={t} onClick={() => setTierFilter(t)} style={{
                padding: "5px 14px", borderRadius: "20px",
                border: `1px solid ${active ? color : "rgba(255,255,255,0.08)"}`,
                background: active ? `${color}15` : "transparent",
                color: active ? color : "#6B7280",
                fontSize: "11px", fontWeight: 600, cursor: "pointer",
                fontFamily: "'Outfit', sans-serif", letterSpacing: "0.02em", transition: "all 0.2s",
              }}>
                {t !== "All" && cfg && <span style={{ marginRight: "5px" }}>{cfg.icon}</span>}
                {t}
                {t !== "All" && (
                  <span style={{ marginLeft: "6px", fontSize: "10px", opacity: 0.6, fontFamily: "'JetBrains Mono', monospace" }}>
                    {QB_DATA_RAW.filter(qb => qb.tier === t).length}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {view === "rankings" && (
          <div>
            {tierFilter === "All" ? (
              Object.entries(TIER_CONFIG).map(([tier, cfg]) => {
                const qbs = tierGroups[tier];
                if (!qbs || qbs.length === 0) return null;
                return (
                  <div key={tier} style={{ marginBottom: "36px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "14px" }}>
                      <span style={{ fontSize: "16px", color: cfg.color }}>{cfg.icon}</span>
                      <h2 style={{
                        fontSize: "14px", fontWeight: 700, color: cfg.color,
                        letterSpacing: "1.5px", textTransform: "uppercase",
                        fontFamily: "'JetBrains Mono', monospace",
                      }}>{tier}</h2>
                      <div style={{ flex: 1, height: "1px", background: `linear-gradient(to right, ${cfg.color}30, transparent)` }} />
                    </div>
                    <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                      {qbs.map((qb, i) => <QBCard key={qb.name} qb={qb} index={i} />)}
                    </div>
                  </div>
                );
              })
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                {filteredData.map((qb, i) => <QBCard key={qb.name} qb={qb} index={i} />)}
              </div>
            )}
          </div>
        )}

        {view === "stats" && (
          <div>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
              <div>
                <h2 style={{ fontSize: "16px", fontWeight: 700, color: "#E8EAED", letterSpacing: "-0.01em" }}>Advanced Statistics</h2>
                <p style={{ fontSize: "11px", color: "#4B5563", fontFamily: "'JetBrains Mono', monospace", marginTop: "2px" }}>
                  Click any column header to sort · Color-coded by league percentile
                </p>
              </div>
              <div style={{ fontSize: "10px", color: "#4B5563", fontFamily: "'JetBrains Mono', monospace", display: "flex", gap: "12px" }}>
                <span><span style={{ color: "#2ECC71" }}>●</span> Top 25%</span>
                <span><span style={{ color: "#7DCEA0" }}>●</span> Above Avg</span>
                <span><span style={{ color: "#E67E22" }}>●</span> Below Avg</span>
                <span><span style={{ color: "#E74C3C" }}>●</span> Bottom 25%</span>
              </div>
            </div>
            <StatsTable data={sortedTableData} sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
          </div>
        )}

        <div style={{
          marginTop: "48px", paddingTop: "24px",
          borderTop: "1px solid rgba(255,255,255,0.04)",
          display: "flex", justifyContent: "space-between",
          fontSize: "10px", color: "#374151", fontFamily: "'JetBrains Mono', monospace",
        }}>
          <span>Data via nflverse · Play-by-play EPA model via nflfastR</span>
          <span>NFL QB Intelligence — 2025 Season Analysis</span>
        </div>
      </main>
    </div>
  );
}
