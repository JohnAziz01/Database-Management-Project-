/**
 * A simpler list page than Policyholders — no search/filter UI, just
 * fetch-on-mount and render. Compare this to Dashboard.jsx and
 * Policyholders.jsx: same shape (loading -> data -> table), less
 * complexity, because this page doesn't need it yet.
 */
import { useEffect, useState } from "react";
import { api } from "../api/client";
import StatusPill from "../components/StatusPill";
import { formatId } from "../utils/formatId";

export default function Policies() {
  const [policies, setPolicies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .getPolicies()
      .then(setPolicies)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="card">
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>Policy ID</th>
              <th>Policyholder</th>
              <th>Vehicle</th>
              <th>Start</th>
              <th>End</th>
              <th>Status</th>
              <th>Bonus-Malus</th>
              <th>Total Premium</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={8} className="empty-state">Loading…</td>
              </tr>
            ) : error ? (
              <tr>
                <td colSpan={8} className="form-error">{error}</td>
              </tr>
            ) : policies.length === 0 ? (
              <tr>
                <td colSpan={8} className="empty-state">No policies yet.</td>
              </tr>
            ) : (
              policies.map((p) => (
                <tr key={p.policy_id}>
                  <td className="cell-strong">{formatId("POL", p.policy_id)}</td>
                  <td>{formatId("PH", p.policyholder_id)}</td>
                  <td>{formatId("VEH", p.vehicle_id)}</td>
                  <td>{p.start_date}</td>
                  <td>{p.end_date}</td>
                  <td><StatusPill value={p.status} /></td>
                  <td className="data">{p.bonus_malus_coefficient}</td>
                  <td className="data">${p.total_premium.toFixed(2)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
