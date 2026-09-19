import { useEffect, useState } from "react";
import { api } from "../api/client";
import StatusPill from "../components/StatusPill";

export default function Claims() {
  const [claims, setClaims] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getClaims().then(setClaims).finally(() => setLoading(false));
  }, []);

  return (
    <div className="card">
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>Claim ID</th>
              <th>Policy ID</th>
              <th>Date</th>
              <th>Type</th>
              <th>Status</th>
              <th>Fault %</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} className="empty-state">Loading…</td></tr>
            ) : claims.length === 0 ? (
              <tr><td colSpan={6} className="empty-state">No claims yet.</td></tr>
            ) : (
              claims.map((c) => (
                <tr key={c.claim_id}>
                  <td className="cell-strong">CLM-{String(c.claim_id).padStart(4, "0")}</td>
                  <td>POL-{String(c.policy_id).padStart(4, "0")}</td>
                  <td>{c.claim_date}</td>
                  <td>{c.claim_type}</td>
                  <td><StatusPill value={c.status} /></td>
                  <td>{c.fault_percentage}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
