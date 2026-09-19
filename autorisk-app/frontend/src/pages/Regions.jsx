import { useEffect, useState } from "react";
import { api } from "../api/client";

export default function Regions() {
  const [regions, setRegions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getRegions().then(setRegions).finally(() => setLoading(false));
  }, []);

  return (
    <div className="card">
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>Region ID</th>
              <th>Name</th>
              <th>Type</th>
              <th>Parent Region</th>
              <th>Base Risk Factor</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5} className="empty-state">Loading…</td></tr>
            ) : (
              regions.map((r) => (
                <tr key={r.region_id}>
                  <td className="cell-strong">{r.region_id}</td>
                  <td>{r.name}</td>
                  <td>{r.region_type}</td>
                  <td>
                    {r.parent_region_id
                      ? regions.find((p) => p.region_id === r.parent_region_id)?.name || r.parent_region_id
                      : "—"}
                  </td>
                  <td className="data">{r.base_risk_factor}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
