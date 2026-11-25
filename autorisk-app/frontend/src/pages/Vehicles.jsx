import { useEffect, useState } from "react";
import { api } from "../api/client";
import { formatId } from "../utils/formatId";

export default function Vehicles() {
  const [vehicles, setVehicles] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getVehicles().then(setVehicles).finally(() => setLoading(false));
  }, []);

  return (
    <div className="card">
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>Vehicle ID</th>
              <th>Policyholder</th>
              <th>Make</th>
              <th>Model</th>
              <th>Year</th>
              <th>Power (kW)</th>
              <th>VIN</th>
              <th>Usage</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={8} className="empty-state">Loading…</td></tr>
            ) : vehicles.length === 0 ? (
              <tr><td colSpan={8} className="empty-state">No vehicles yet.</td></tr>
            ) : (
              vehicles.map((v) => (
                <tr key={v.vehicle_id}>
                  <td className="cell-strong">{formatId("VEH", v.vehicle_id)}</td>
                  <td>{formatId("PH", v.policyholder_id)}</td>
                  <td>{v.make}</td>
                  <td>{v.model}</td>
                  <td>{v.manufacture_year}</td>
                  <td>{v.engine_power_kw}</td>
                  <td>{v.vin || "—"}</td>
                  <td>{v.usage_type}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
