import { useState } from "react";
import { ScatterChart, Scatter, XAxis, YAxis, ZAxis, Tooltip, ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, Legend } from "recharts";
import qbData from "./data/qb_data.json"; 

// ─── Constants ───
const TIER_COLORS = { "Elite": "#f59e0b", "Blue Chip": "#3b82f6", "Quality Starter": "#22c55e", "Bridge / Backup": "#6b7280" };
const TEAM_COLORS = {
  ARI:"#97233F",ATL:"#A71930",BAL:"#241773",BUF:"#00338D",CAR:"#0085CA",CHI:"#0B162A",
  CIN:"#FB4F14",CLE:"#311D00",DAL:"#003594",DEN:"#FB4F14",DET:"#0076B6",GB:"#203731",
  HOU:"#03202F",IND:"#002C5F",JAX:"#006778",KC:"#E31837",LAC:"#0080C6",LAR:"#003594",
  LV:"#000000",MIA:"#008E97",MIN:"#4F2683",NE:"#002244",NO:"#D3BC8D",NYG:"#0B2265",
  NYJ:"#125740",PHI:"#004C54",PIT:"#FFB612",SEA:"#002244",SF:"#AA0000",TB:"#D50A0A",
  TEN:"#0C2340",WAS:"#5A1414",
};

const AXIS_OPTIONS = [
  { key: "throwEpa", label: "Throw EPA", fmt: v => v > 0 ? `+${v.toFixed(3)}` : v.toFixed(3) },
  { key: "cpoe", label: "CPOE", fmt: v => v > 0 ? `+${v.toFixed(1)}` : v.toFixed(1) },
  { key: "rushEpaPerGame", label: "Rush EPA/G", fmt: v => v > 0 ? `+${v.toFixed(2)}` : v.toFixed(2) },
  { key: "pressureResilience", label: "Pressure Res.", fmt: v => v.toFixed(3) },
  { key: "highLeverageEpa", label: "Hi-Lev EPA", fmt: v => v > 0 ? `+${v.toFixed(3)}` : v.toFixed(3) },
  { key: "winPct", label: "Win %", fmt: v => `${v.toFixed(1)}%` },
  { key: "ypa", label: "YPA", fmt: v => v.toFixed(1) },
  { key: "sackRate", label: "Sack Rate", fmt: v => `${v.toFixed(1)}%` },
  { key: "avgAirYards", label: "Avg Air Yards", fmt: v => v.toFixed(1) },
  { key: "positivePlayRate", label: "Pos Play %", fmt: v => `${v.toFixed(1)}%` },
  { key: "rating", label: "Overall Rating", fmt: v => v.toFixed(0) },
];

const RADAR_METRICS = [
  { key: "throwEpa", label: "Passing", min: -0.05, max: 0.35 },
  { key: "pressureResilience", label: "Poise", min: -0.6, max: -0.15 },
  { key: "highLeverageEpa", label: "Clutch", min: -0.05, max: 0.3 },
  { key: "rushEpaPerGame", label: "Rushing", min: -0.5, max: 1.5 },
  { key: "cpoe", label: "Accuracy", min: -3, max: 8 },
  { key: "ypa", label: "Explosiveness", min: 5.5, max: 9 },
];

function normalize(val, min, max) { return Math.max(0, Math.min(100, ((val - min) / (max - min)) * 100)); }

// ─── Custom Scatter Dot ───
function QBDot({ cx, cy, payload, hovered, selected, onClick }) {
  const isHovered = hovered === payload.name;
  const isSelected = selected.includes(payload.name);
  const tc = TIER_COLORS[payload.tier] || "#6b7280";
  const r = isHovered || isSelected ? 9 : 6;

  return (
    <g onClick={() => onClick(payload.name)} style={{ cursor: "pointer" }}>
      {(isHovered || isSelected) && (
        <circle cx={cx} cy={cy} r={r + 5} fill={tc} opacity={0.15} />
      )}
      <circle cx={cx} cy={cy} r={r} fill={tc} stroke={isSelected ? "#fff" : tc}
        strokeWidth={isSelected ? 2.5 : 1} opacity={isHovered || isSelected ? 1 : 0.75} />
      {(isHovered || isSelected) && (
        <text x={cx} y={cy - r - 6} textAnchor="middle" fill="#e2e8f0"
          fontSize={11} fontFamily="'DM Sans', sans-serif" fontWeight={600}>
          {payload.name}
        </text>
      )}
    </g>
  );
}

// ─── Scatter Plot Panel ───
function ScatterPanel({ xKey, yKey, selected, setSelected, hovered, setHovered }) {
  const xOpt = AXIS_OPTIONS.find(a => a.key === xKey);
  const yOpt = AXIS_OPTIONS.find(a => a.key === yKey);

  const toggle = (name) => {
    setSelected(prev =>
      prev.includes(name) ? prev.filter(n => n !== name) : prev.length < 3 ? [...prev, name] : prev
    );
  };

  // Calculate league averages
  const xAvg = qbData.reduce((s, q) => s + q[xKey], 0) / qbData.length;
  const yAvg = qbData.reduce((s, q) => s + q[yKey], 0) / qbData.length;

  return (
    <div style={{ position: "relative" }}>
      <ResponsiveContainer width="100%" height={420}>
        <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 10 }}>
          <XAxis dataKey={xKey} type="number" name={xOpt.label} tick={{ fill: "#64748b", fontSize: 11 }}
            axisLine={{ stroke: "#1e293b" }} tickLine={false} />
          <YAxis dataKey={yKey} type="number" name={yOpt.label} tick={{ fill: "#64748b", fontSize: 11 }}
            axisLine={{ stroke: "#1e293b" }} tickLine={false} />
          <ZAxis dataKey="rating" range={[30, 300]} name="Rating" />
          <Tooltip content={({ payload: p }) => {
            if (!p || !p[0]) return null;
            const d = p[0].payload;
            return (
              <div style={{ background: "#111827ee", border: "1px solid #334155", borderRadius: 8,
                padding: "10px 14px", backdropFilter: "blur(12px)" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                  {d.headshotUrl && <img src={d.headshotUrl} alt="" style={{ width: 28, height: 28,
                    borderRadius: "50%", objectFit: "cover", border: `2px solid ${TEAM_COLORS[d.team]}` }} />}
                  <span style={{ fontWeight: 700, color: "#f1f5f9", fontFamily: "'DM Sans'" }}>{d.name}</span>
                  <span style={{ fontSize: 11, color: TIER_COLORS[d.tier], fontWeight: 600 }}>{d.rating}</span>
                </div>
                <div style={{ fontSize: 12, color: "#94a3b8", fontFamily: "'DM Mono'" }}>
                  {xOpt.label}: <span style={{ color: "#e2e8f0" }}>{xOpt.fmt(d[xKey])}</span>
                  {" · "}
                  {yOpt.label}: <span style={{ color: "#e2e8f0" }}>{yOpt.fmt(d[yKey])}</span>
                </div>
              </div>
            );
          }} />
          {/* Reference lines for league average */}
          <Scatter data={qbData}
            shape={(props) => <QBDot {...props} hovered={hovered} selected={selected} onClick={toggle} />}
            onMouseEnter={(_, idx) => setHovered(qbData[idx]?.name)}
            onMouseLeave={() => setHovered(null)} />
        </ScatterChart>
      </ResponsiveContainer>
      {/* Axis labels */}
      <div style={{ position: "absolute", bottom: 0, left: "50%", transform: "translateX(-50%)",
        fontSize: 12, color: "#64748b", fontFamily: "'DM Mono'", letterSpacing: 0.5 }}>{xOpt.label}</div>
      <div style={{ position: "absolute", left: -4, top: "50%", transform: "translateY(-50%) rotate(-90deg)",
        fontSize: 12, color: "#64748b", fontFamily: "'DM Mono'", letterSpacing: 0.5 }}>{yOpt.label}</div>
    </div>
  );
}

// ─── Radar Comparison ───
function RadarComparison({ selected }) {
  const radarData = RADAR_METRICS.map(m => {
    const row = { metric: m.label };
    selected.forEach(name => {
      const qb = qbData.find(q => q.name === name);
      if (qb) row[name] = normalize(qb[m.key], m.min, m.max);
    });
    return row;
  });

  const colors = ["#f59e0b", "#3b82f6", "#ef4444"];

  return (
    <ResponsiveContainer width="100%" height={340}>
      <RadarChart data={radarData} cx="50%" cy="50%" outerRadius="75%">
        <PolarGrid stroke="#1e293b" />
        <PolarAngleAxis dataKey="metric" tick={{ fill: "#94a3b8", fontSize: 11, fontFamily: "'DM Sans'" }} />
        <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
        {selected.map((name, i) => (
          <Radar key={name} name={name} dataKey={name} stroke={colors[i]}
            fill={colors[i]} fillOpacity={0.12} strokeWidth={2.5} dot={{ r: 3, fill: colors[i] }} />
        ))}
        <Legend wrapperStyle={{ fontSize: 12, fontFamily: "'DM Sans'" }} />
      </RadarChart>
    </ResponsiveContainer>
  );
}

// ─── Tier Distribution Bar ───
function TierBar() {
  const tiers = ["Elite", "Blue Chip", "Quality Starter", "Bridge / Backup"];
  const data = tiers.map(t => ({
    tier: t.replace("Bridge / Backup", "Bridge/Backup"),
    count: qbData.filter(q => q.tier === t).length,
    avgRating: Math.round(qbData.filter(q => q.tier === t).reduce((s, q) => s + q.rating, 0) / Math.max(1, qbData.filter(q => q.tier === t).length)),
    color: TIER_COLORS[t],
  }));

  return (
    <div style={{ display: "flex", gap: 12 }}>
      {data.map(d => (
        <div key={d.tier} style={{ flex: 1, background: "#111827", borderRadius: 10, padding: "16px 14px",
          borderTop: `3px solid ${d.color}`, textAlign: "center" }}>
          <div style={{ fontSize: 28, fontWeight: 800, color: d.color, fontFamily: "'DM Mono'" }}>{d.count}</div>
          <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 2, fontFamily: "'DM Sans'", fontWeight: 600 }}>{d.tier}</div>
          <div style={{ fontSize: 11, color: "#475569", marginTop: 4, fontFamily: "'DM Mono'" }}>Avg: {d.avgRating}</div>
        </div>
      ))}
    </div>
  );
}

// ─── QB Chip (selectable) ───
function QBChip({ qb, isSelected, onClick }) {
  const tc = TIER_COLORS[qb.tier];
  return (
    <button onClick={onClick} style={{
      display: "inline-flex", alignItems: "center", gap: 6, padding: "5px 12px 5px 5px",
      borderRadius: 20, fontSize: 12, fontWeight: 600, fontFamily: "'DM Sans'",
      background: isSelected ? tc + "22" : "#111827", color: isSelected ? tc : "#94a3b8",
      border: `1.5px solid ${isSelected ? tc : "#1e293b"}`, cursor: "pointer",
      transition: "all 0.2s", whiteSpace: "nowrap",
    }}>
      {qb.headshotUrl && (
        <img src={qb.headshotUrl} alt="" style={{ width: 22, height: 22, borderRadius: "50%",
          objectFit: "cover", border: `1.5px solid ${isSelected ? tc : "#334155"}` }} />
      )}
      {qb.name}
    </button>
  );
}

// ─── Selector Dropdown ───
function AxisSelector({ value, onChange, label }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <span style={{ fontSize: 11, color: "#64748b", fontFamily: "'DM Mono'", textTransform: "uppercase",
        letterSpacing: 1 }}>{label}</span>
      <select value={value} onChange={e => onChange(e.target.value)} style={{
        background: "#111827", border: "1px solid #1e293b", borderRadius: 6, padding: "5px 10px",
        color: "#e2e8f0", fontSize: 12, fontFamily: "'DM Sans'", cursor: "pointer", outline: "none",
      }}>
        {AXIS_OPTIONS.map(a => <option key={a.key} value={a.key}>{a.label}</option>)}
      </select>
    </div>
  );
}

// ─── Main ───
export default function AnalyticsLab() {
  const [xAxis, setXAxis] = useState("throwEpa");
  const [yAxis, setYAxis] = useState("rushEpaPerGame");
  const [selected, setSelected] = useState(["J.Allen", "L.Jackson"]);
  const [hovered, setHovered] = useState(null);

  return (
    <div style={{ minHeight: "100vh", background: "#080b12", color: "#e2e8f0", fontFamily: "'DM Sans', sans-serif" }}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet" />
      <style>{`
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: #080b12; }
        ::selection { background: #f59e0b33; }
        select option { background: #111827; }
        .recharts-cartesian-grid line { stroke: #1e293b; }
        @keyframes fadeUp { from { opacity:0; transform:translateY(12px); } to { opacity:1; transform:translateY(0); } }
        .fade-up { animation: fadeUp 0.5s ease both; }
      `}</style>

      {/* Header */}
      <header style={{ padding: "36px 40px 28px", borderBottom: "1px solid #151a25",
        background: "linear-gradient(180deg, #0d1117 0%, #080b12 100%)" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 6 }}>
            <div style={{ width: 32, height: 32, borderRadius: 8, background: "linear-gradient(135deg, #f59e0b, #ef4444)",
              display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, fontWeight: 800,
              color: "#fff", fontFamily: "'DM Mono'" }}>Q</div>
            <h1 style={{ fontSize: 26, fontWeight: 800, letterSpacing: "-0.5px", color: "#f1f5f9" }}>
              Analytics Lab
            </h1>
            <span style={{ fontSize: 12, color: "#475569", fontFamily: "'DM Mono'", marginLeft: 4,
              padding: "3px 10px", background: "#111827", borderRadius: 12, border: "1px solid #1e293b" }}>
              QB INTELLIGENCE
            </span>
          </div>
          <p style={{ color: "#4b5563", fontSize: 13, maxWidth: 600 }}>
            Interactive analysis of {qbData.length} NFL quarterbacks across 13 advanced metrics.
            Select up to 3 QBs to compare on the radar chart.
          </p>
        </div>
      </header>

      <main style={{ maxWidth: 1100, margin: "0 auto", padding: "28px 40px 60px" }}>

        {/* Tier overview */}
        <section className="fade-up" style={{ marginBottom: 32 }}>
          <TierBar />
        </section>

        {/* QB Selector */}
        <section className="fade-up" style={{ marginBottom: 28, animationDelay: "0.1s" }}>
          <div style={{ fontSize: 11, color: "#64748b", fontFamily: "'DM Mono'", textTransform: "uppercase",
            letterSpacing: 1.5, marginBottom: 10 }}>
            Compare QBs <span style={{ color: "#475569" }}>(select up to 3)</span>
          </div>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {qbData.map(qb => (
              <QBChip key={qb.name} qb={qb} isSelected={selected.includes(qb.name)}
                onClick={() => setSelected(prev =>
                  prev.includes(qb.name) ? prev.filter(n => n !== qb.name) :
                  prev.length < 3 ? [...prev, qb.name] : prev
                )} />
            ))}
          </div>
        </section>

        {/* Main grid */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 380px", gap: 20, alignItems: "start" }}>

          {/* Scatter Plot */}
          <section className="fade-up" style={{ background: "#0d1117", borderRadius: 14,
            border: "1px solid #151a25", padding: "20px 16px 12px", animationDelay: "0.15s" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center",
              marginBottom: 12, padding: "0 8px" }}>
              <AxisSelector value={xAxis} onChange={setXAxis} label="X" />
              <span style={{ color: "#1e293b", fontSize: 18 }}>×</span>
              <AxisSelector value={yAxis} onChange={setYAxis} label="Y" />
            </div>
            <ScatterPanel xKey={xAxis} yKey={yAxis} selected={selected} setSelected={setSelected}
              hovered={hovered} setHovered={setHovered} />
            <div style={{ display: "flex", gap: 16, justifyContent: "center", padding: "8px 0 4px" }}>
              {Object.entries(TIER_COLORS).map(([tier, color]) => (
                <div key={tier} style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 11,
                  color: "#64748b", fontFamily: "'DM Sans'" }}>
                  <div style={{ width: 8, height: 8, borderRadius: "50%", background: color }} />
                  {tier}
                </div>
              ))}
            </div>
          </section>

          {/* Right column: Radar + Selected details */}
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>

            {/* Radar */}
            <section className="fade-up" style={{ background: "#0d1117", borderRadius: 14,
              border: "1px solid #151a25", padding: "16px 8px 8px", animationDelay: "0.2s" }}>
              <div style={{ fontSize: 11, color: "#64748b", fontFamily: "'DM Mono'", textTransform: "uppercase",
                letterSpacing: 1.5, padding: "0 12px 8px", borderBottom: "1px solid #151a25", marginBottom: 4 }}>
                Skill Radar
              </div>
              {selected.length > 0 ? (
                <RadarComparison selected={selected} />
              ) : (
                <div style={{ height: 300, display: "flex", alignItems: "center", justifyContent: "center",
                  color: "#334155", fontSize: 13 }}>
                  Select QBs to compare
                </div>
              )}
            </section>

            {/* Selected QB cards */}
            {selected.map((name, i) => {
              const qb = qbData.find(q => q.name === name);
              if (!qb) return null;
              const colors = ["#f59e0b", "#3b82f6", "#ef4444"];
              return (
                <div key={name} className="fade-up" style={{
                  background: "#0d1117", borderRadius: 12, border: `1px solid ${colors[i]}33`,
                  padding: 14, display: "flex", gap: 12, alignItems: "center", animationDelay: `${0.25 + i * 0.05}s`,
                }}>
                  {qb.headshotUrl && (
                    <img src={qb.headshotUrl} alt="" style={{ width: 48, height: 48, borderRadius: 10,
                      objectFit: "cover", border: `2px solid ${colors[i]}`, flexShrink: 0 }} />
                  )}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 700, fontSize: 14, color: "#f1f5f9", marginBottom: 2 }}>
                      {qb.name}
                      <span style={{ fontSize: 11, color: colors[i], marginLeft: 6, fontWeight: 600,
                        fontFamily: "'DM Mono'" }}>{qb.rating}</span>
                    </div>
                    <div style={{ fontSize: 11, color: "#64748b", fontFamily: "'DM Mono'" }}>
                      {qb.team} · {qb.tier} · {qb.wins}-{qb.losses}
                    </div>
                    <div style={{ display: "flex", gap: 10, marginTop: 6, fontSize: 11, fontFamily: "'DM Mono'" }}>
                      <span style={{ color: "#94a3b8" }}>EPA <span style={{ color: qb.throwEpa > 0.2 ? "#22c55e" : "#f59e0b" }}>
                        {qb.throwEpa > 0 ? "+" : ""}{qb.throwEpa.toFixed(3)}</span></span>
                      <span style={{ color: "#94a3b8" }}>CPOE <span style={{ color: qb.cpoe > 2 ? "#22c55e" : "#f59e0b" }}>
                        {qb.cpoe > 0 ? "+" : ""}{qb.cpoe.toFixed(1)}</span></span>
                      <span style={{ color: "#94a3b8" }}>Rush <span style={{ color: "#e2e8f0" }}>
                        {qb.rushYds}</span></span>
                    </div>
                  </div>
                  <button onClick={() => setSelected(prev => prev.filter(n => n !== name))} style={{
                    background: "none", border: "none", color: "#475569", cursor: "pointer", fontSize: 18,
                    padding: 4, lineHeight: 1,
                  }}>×</button>
                </div>
              );
            })}
          </div>
        </div>

        {/* Footer note */}
        <div style={{ marginTop: 40, padding: "16px 0", borderTop: "1px solid #151a25", textAlign: "center",
          fontSize: 11, color: "#334155", fontFamily: "'DM Mono'" }}>
          QB Intelligence v2.0 · Two-Pillar Rating System (Quality 65% + Impact 35%) · 2024–2025 nflverse data
        </div>
      </main>
    </div>
  );
}
