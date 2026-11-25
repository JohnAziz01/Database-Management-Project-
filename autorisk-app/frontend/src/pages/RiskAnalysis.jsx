import { useEffect, useState } from "react";
import { api } from "../api/client";
import KpiCard from "../components/KpiCard";

// Claim experience by rating factor: does each pricing factor match reality?
// A segment whose loss ratio is well above the book's is under-priced.
const SMALL_SAMPLE = 10; // fewer policies than this: too few to trust

const pct = (r) => (r == null ? "—" : `${(r * 100).toFixed(1)}%`);
const money = (n) => (n == null ? "—" : `$${Number(n).toLocaleString(undefined, { maximumFractionDigits: 0 })}`);

export default function RiskAnalysis() {
  const [dimensions, setDimensions] = useState([]);
  const [dimension, setDimension] = useState("driver_age");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.getRiskDimensions().then(setDimensions).catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .getRiskAnalysis(dimension)
      .then((d) => !cancelled && setData(d))
      .catch((err) => !cancelled && setError(err.message))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [dimension]);

  const o = data?.overall;
  const segments = data?.segments || [];
  const reliable = segments.filter((s) => s.policies >= SMALL_SAMPLE && s.loss_ratio != null);
  const worst = reliable.reduce((a, b) => (b.loss_ratio > (a?.loss_ratio ?? -1) ? b : a), null);
  const maxFreq = Math.max(...segments.map((s) => s.claim_frequency || 0), 0.0001);
  const maxLR = Math.max(...segments.map((s) => s.loss_ratio || 0), 0.0001);

  return (
    <div>
      <div className="tabs" role="tablist" aria-label="Rating factor">
        {dimensions.map((d) => (
          <button
            key={d.key}
            role="tab"
            aria-selected={d.key === dimension}
            className={`tab${d.key === dimension ? " tab-active" : ""}`}
            onClick={() => setDimension(d.key)}
          >
            {d.label}
          </button>
        ))}
      </div>

      {error && <div className="form-error">{error}</div>}
      {data && (
        <>
          <div className="kpi-grid kpi-5">
            <KpiCard label="Policies analysed" value={o.policies.toLocaleString()} />
            <KpiCard label="Claims" value={o.claims.toLocaleString()} />
            <KpiCard label="Claim frequency (per policy)" value={pct(o.claim_frequency)} />
            <KpiCard label="Average claim cost" value={money(o.average_severity)} />
            <KpiCard label="Loss ratio (paid ÷ premium)" value={pct(o.loss_ratio)} />
          </div>

          <div className="card">
            <div className="card-header">
              <div>
                <h3>Claim experience by {data.label.toLowerCase()}</h3>
                <div className="subtitle">{data.description}</div>
              </div>
            </div>
            {worst && (
              <div className="insight">
                <strong>{worst.segment}</strong> has the highest loss ratio among segments with at least {SMALL_SAMPLE} policies:{" "}
                <strong>{pct(worst.loss_ratio)}</strong> against {pct(o.loss_ratio)} for the whole book.
                {worst.loss_ratio > o.loss_ratio * 1.25 ? " Its pricing factor may be too low." : ""}
              </div>
            )}
            <div className="table-scroll">
              <table className="data-table compact">
                <thead>
                  <tr>
                    <th>{data.label}</th>
                    <th className="num">Policies</th>
                    <th className="num">Claims</th>
                    <th>Claim Frequency</th>
                    <th className="num">Avg Claim</th>
                    <th className="num">Premium</th>
                    <th className="num">Paid</th>
                    <th>Loss Ratio</th>
                  </tr>
                </thead>
                <tbody>
                  {loading ? (
                    <tr><td colSpan={8} className="empty-state">Loading…</td></tr>
                  ) : segments.length === 0 ? (
                    <tr><td colSpan={8} className="empty-state">No policies to analyse yet.</td></tr>
                  ) : (
                    segments.map((s) => (
                      <tr key={s.segment} className={s.policies < SMALL_SAMPLE ? "row-muted" : ""}>
                        <td className="cell-strong">
                          {s.segment}
                          {s.policies < SMALL_SAMPLE && <span className="tag">small sample</span>}
                        </td>
                        <td className="num data">{s.policies.toLocaleString()}</td>
                        <td className="num data">{s.claims.toLocaleString()}</td>
                        <td><Bar value={s.claim_frequency} max={maxFreq} label={pct(s.claim_frequency)} /></td>
                        <td className="num data">{money(s.average_severity)}</td>
                        <td className="num data">{money(s.premium)}</td>
                        <td className="num data">{money(s.paid)}</td>
                        <td><Bar value={s.loss_ratio} max={maxLR} label={pct(s.loss_ratio)} warn={s.loss_ratio > 1} /></td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
            <div className="card-foot muted">
              Claim frequency = claims ÷ policies. Loss ratio above 100% means the segment paid out more than it earned.
              Rows marked “small sample” have under {SMALL_SAMPLE} policies and should not drive pricing decisions.
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function Bar({ value, max, label, warn = false }) {
  return (
    <div className="inline-bar">
      <span className="inline-bar-track">
        <span className={`inline-bar-fill${warn ? " warn" : ""}`} style={{ width: `${((value || 0) / max) * 100}%` }} />
      </span>
      <span className="data">{label}</span>
    </div>
  );
}
