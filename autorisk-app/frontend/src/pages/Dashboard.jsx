import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import KpiCard from "../components/KpiCard";
import PortfolioPanels from "../components/PortfolioPanels";
import StatusPill from "../components/StatusPill";
import { formatId } from "../utils/formatId";

export default function Dashboard() {
  // Three independent pieces of state: the data itself, whether we're
  // still loading it, and any error. Keeping them separate (rather than
  // one big object) keeps each update simple.
  const [summary, setSummary] = useState(null);
  const [recentClaims, setRecentClaims] = useState([]);
  const [portfolio, setPortfolio] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false; // guards against setting state after unmount

    async function load() {
      try {
        // Promise.all runs both requests in parallel instead of one after
        // another — the dashboard has two independent pieces of data.
        const [summaryData, claimsData, portfolioData] = await Promise.all([
          api.getDashboardSummary(),
          api.getRecentClaims(),
          api.getPortfolio(),
        ]);
        if (!cancelled) {
          setSummary(summaryData);
          setRecentClaims(claimsData);
          setPortfolio(portfolioData);
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true; // cleanup function: runs if the component unmounts
    };
  }, []); // <- empty dependency array: run once on mount, not on every render

  if (loading) return <div className="empty-state">Loading dashboard…</div>;
  if (error) return <div className="form-error">Couldn't load dashboard: {error}</div>;

  // Build the list of KPI cards to render from the summary object. This
  // keeps the JSX below focused on "how to render one card" rather than
  // repeating five near-identical <KpiCard> tags by hand.
  const kpis = [
    { label: "Active Policies", value: summary.active_policies },
    { label: "Total Premium Written", value: `$${summary.total_premium_written.toFixed(2)}` },
    { label: "Open Claims", value: summary.open_claims },
    { label: "Total Claims Paid", value: `$${summary.total_claims_paid.toFixed(2)}` },
    { label: "Policyholders", value: summary.policyholders },
  ];

  return (
    <div>
      <div className="kpi-grid kpi-5">
        {/* .map() over an array of data, returning one <KpiCard> per item.
            React needs a stable `key` on each item in a list so it can
            track which DOM node corresponds to which piece of data across
            re-renders (important once data starts changing/reordering). */}
        {kpis.map((k) => (
          <KpiCard key={k.label} label={k.label} value={k.value} />
        ))}
      </div>

      <div className="card" style={{ marginTop: 20 }}>
        <div className="card-header">
          <div>
            <h3>Recent Claims</h3>
            <div className="subtitle">Latest {recentClaims.length} claims</div>
          </div>
          <Link className="btn btn-ghost" to="/claims">
            View all claims
          </Link>
        </div>
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Claim ID</th>
                <th>Policy ID</th>
                <th>Date</th>
                <th>Status</th>
                <th>Fault %</th>
              </tr>
            </thead>
            <tbody>
              {recentClaims.length === 0 ? (
                <tr>
                  <td colSpan={5} className="empty-state">
                    No claims yet.
                  </td>
                </tr>
              ) : (
                recentClaims.map((c) => (
                  <tr key={c.claim_id}>
                    <td className="cell-strong">{formatId("CLM", c.claim_id)}</td>
                    <td>{formatId("POL", c.policy_id)}</td>
                    <td>{c.claim_date}</td>
                    <td>
                      <StatusPill value={c.status} />
                    </td>
                    <td>{c.fault_percentage}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
      {portfolio && <PortfolioPanels data={portfolio} />}
    </div>
  );
}
