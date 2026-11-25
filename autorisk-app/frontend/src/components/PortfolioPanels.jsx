import { useState } from "react";
import KpiCard from "./KpiCard";

// Whole-book view for the Dashboard: every policy, including the expired
// historical policies imported from the freMTPL2 data handoff, which the
// "active only" cards above leave out. Data: GET /api/dashboard/portfolio.

const money = (n) =>
  `$${Number(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const moneyShort = (n) =>
  n >= 1e6 ? `$${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `$${(n / 1e3).toFixed(1)}k` : `$${Math.round(n)}`;
const pct = (r) => (r == null ? "—" : `${(r * 100).toFixed(1)}%`);

export default function PortfolioPanels({ data }) {
  const t = data.totals;
  const kpis = [
    { label: "All Policies (incl. historical)", value: t.policies.toLocaleString() },
    { label: "Premium Written (all time)", value: money(t.premium) },
    { label: "Claims Filed", value: t.claims.toLocaleString() },
    { label: "Claims Paid (all time)", value: money(t.paid) },
    { label: "Loss Ratio (paid ÷ premium)", value: pct(t.loss_ratio) },
    { label: "Average Paid Claim", value: t.average_claim == null ? "—" : money(t.average_claim) },
  ];

  return (
    <section style={{ marginTop: 28 }}>
      <div className="section-heading">
        <h2>Portfolio</h2>
        <span className="subtitle">Every policy on the books, including expired historical policies</span>
      </div>

      <div className="kpi-grid kpi-6">
        {kpis.map((k) => (
          <KpiCard key={k.label} label={k.label} value={k.value} />
        ))}
      </div>

      <div className="grid-charts">
        <div className="card">
          <div className="card-header">
            <div>
              <h3>Claims Paid by Policy Year</h3>
              <div className="subtitle">Paid amount on policies starting each year</div>
            </div>
          </div>
          <div className="card-pad">
            <YearBars rows={data.by_year} />
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <div>
              <h3>By Region</h3>
              <div className="subtitle">Sorted by claims paid · policyholder's region</div>
            </div>
          </div>
          <div className="table-scroll region-scroll">
            <RegionTable rows={data.by_region} />
          </div>
        </div>
      </div>
    </section>
  );
}

// Single-series column chart: one hue, thin columns with rounded tops on a
// shared baseline, and a hover tooltip per column. Year labels sit under
// each column; the value is shown on hover (and in the tooltip's table row).
function YearBars({ rows }) {
  const [hover, setHover] = useState(null);
  if (rows.length === 0) return <div className="empty-state">No policies yet.</div>;
  const max = Math.max(...rows.map((r) => r.paid), 1);

  return (
    <div className="year-chart" role="img" aria-label="Claims paid by policy start year">
      <div className="year-plot">
        {rows.map((r) => (
          <div
            key={r.year}
            className="year-col"
            onMouseEnter={() => setHover(r)}
            onMouseLeave={() => setHover(null)}
            onFocus={() => setHover(r)}
            onBlur={() => setHover(null)}
            tabIndex={0}
          >
            <div className="year-value">{hover?.year === r.year ? moneyShort(r.paid) : ""}</div>
            <div
              className={`year-bar${hover && hover.year !== r.year ? " dim" : ""}`}
              style={{ height: `${Math.max((r.paid / max) * 100, r.paid ? 1.5 : 0)}%` }}
            />
          </div>
        ))}
      </div>
      <div className="year-axis">
        {rows.map((r) => (
          <div key={r.year} className="year-label">
            {r.year}
          </div>
        ))}
      </div>
      <div className="year-tooltip" aria-live="polite">
        {hover ? (
          <>
            <strong>{hover.year}</strong> · {hover.policies} policies · {hover.claims} claims · paid{" "}
            <strong>{money(hover.paid)}</strong> · loss ratio {pct(hover.loss_ratio)}
          </>
        ) : (
          <span className="muted">Hover a column for details</span>
        )}
      </div>
    </div>
  );
}

function RegionTable({ rows }) {
  const max = Math.max(...rows.map((r) => r.paid), 1);
  return (
    <table className="data-table compact">
      <thead>
        <tr>
          <th>Region</th>
          <th className="num">Policies</th>
          <th className="num">Claims</th>
          <th>Claims Paid</th>
          <th className="num">Loss Ratio</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.region}>
            <td className="cell-strong">{r.region}</td>
            <td className="num">{r.policies}</td>
            <td className="num">{r.claims}</td>
            <td>
              <div className="inline-bar">
                <span className="inline-bar-track">
                  <span className="inline-bar-fill" style={{ width: `${(r.paid / max) * 100}%` }} />
                </span>
                <span className="data">{moneyShort(r.paid)}</span>
              </div>
            </td>
            <td className="num data">{pct(r.loss_ratio)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
