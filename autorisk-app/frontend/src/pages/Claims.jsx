import { useEffect, useState } from "react";
import { api } from "../api/client";
import StatusPill from "../components/StatusPill";
import { formatId } from "../utils/formatId";

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
                  <td className="cell-strong">{formatId("CLM", c.claim_id)}</td>
                  <td>{formatId("POL", c.policy_id)}</td>
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
