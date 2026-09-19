import { useEffect, useState } from "react";
import { api } from "../api/client";

export default function Coverage() {
  const [coverages, setCoverages] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getCoverages().then(setCoverages).finally(() => setLoading(false));
  }, []);

  return (
    <div className="card">
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>Coverage ID</th>
              <th>Name</th>
              <th>Description</th>
              <th>Mandatory</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={4} className="empty-state">Loading…</td></tr>
            ) : (
              coverages.map((c) => (
                <tr key={c.coverage_id}>
                  <td className="cell-strong">{c.coverage_id}</td>
                  <td>{c.coverage_name}</td>
                  <td>{c.description}</td>
                  <td>{c.is_mandatory ? "Yes" : "No"}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
