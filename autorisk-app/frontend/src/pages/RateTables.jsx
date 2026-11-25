import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import StatusPill from "../components/StatusPill";

// Rates are versioned, never edited: "Revise" publishes a new version that
// starts on a chosen date and closes the one in force. Issued policies keep
// the premium they were sold at.
export default function RateTables() {
  const { canManage } = useAuth();
  const [rates, setRates] = useState([]);
  const [regions, setRegions] = useState([]);
  const [coverages, setCoverages] = useState([]);
  const [filters, setFilters] = useState({ region_id: "", coverage_id: "", status: "Current" });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [editing, setEditing] = useState(null); // prefill for the publish form, or null
  const [notice, setNotice] = useState(null);

  useEffect(() => {
    Promise.all([api.getRegions(), api.getCoverages()])
      .then(([r, c]) => {
        setRegions(r);
        setCoverages(c);
      })
      .catch((err) => setError(err.message));
  }, []);

  const load = useCallback(() => {
    setLoading(true);
    api
      .getRateTables(filters)
      .then(setRates)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [filters]);

  useEffect(load, [load]);

  const setFilter = (k, v) => setFilters((f) => ({ ...f, [k]: v }));

  function handlePublished(rate) {
    setEditing(null);
    setNotice(`Published ${rate.coverage_name} rates for ${rate.region_name}, effective ${rate.effective_date}.`);
    load();
  }

  return (
    <div className="card">
      <div className="table-toolbar">
        <div className="toolbar-filters">
          <select className="field-sm" aria-label="Region" value={filters.region_id} onChange={(e) => setFilter("region_id", e.target.value)}>
            <option value="">All regions</option>
            {regions.map((r) => (
              <option key={r.region_id} value={r.region_id}>{r.name}</option>
            ))}
          </select>
          <select className="field-sm" aria-label="Coverage" value={filters.coverage_id} onChange={(e) => setFilter("coverage_id", e.target.value)}>
            <option value="">All coverages</option>
            {coverages.map((c) => (
              <option key={c.coverage_id} value={c.coverage_id}>{c.coverage_name}</option>
            ))}
          </select>
          <select className="field-sm" aria-label="Status" value={filters.status} onChange={(e) => setFilter("status", e.target.value)}>
            <option value="">All versions</option>
            <option value="Current">Current</option>
            <option value="Scheduled">Scheduled</option>
            <option value="Expired">Expired</option>
          </select>
        </div>
        {canManage && (
          <button className="btn btn-primary" onClick={() => setEditing({})}>
            New Rate Version
          </button>
        )}
      </div>
      {notice && <div className="form-success">{notice}</div>}
      {error && <div className="form-error">{error}</div>}
      <div className="table-scroll">
        <table className="data-table compact">
          <thead>
            <tr>
              <th>Region</th>
              <th>Coverage</th>
              <th>Status</th>
              <th>Effective</th>
              <th>Expires</th>
              <th className="num">Base / yr</th>
              <th className="num">Young</th>
              <th className="num">Senior</th>
              <th className="num">Power</th>
              <th className="num" title="Bonus-malus step">BM Step</th>
              {canManage && <th />}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={11} className="empty-state">Loading…</td></tr>
            ) : rates.length === 0 ? (
              <tr><td colSpan={11} className="empty-state">No rate versions match these filters.</td></tr>
            ) : (
              rates.map((r) => (
                <tr key={r.rate_table_id}>
                  <td className="cell-strong">{r.region_name}</td>
                  <td>{r.coverage_name}</td>
                  <td><StatusPill value={r.status} /></td>
                  <td>{r.effective_date}</td>
                  <td>{r.expiry_date || "—"}</td>
                  <td className="num data">${r.base_rate.toFixed(2)}</td>
                  <td className="num data">{r.age_factor_young.toFixed(2)}</td>
                  <td className="num data">{r.age_factor_senior.toFixed(2)}</td>
                  <td className="num data">{r.vehicle_power_factor.toFixed(2)}</td>
                  <td className="num data">{r.bonus_malus_step.toFixed(2)}</td>
                  {canManage && (
                    <td>
                      {r.status !== "Expired" && (
                        <button className="btn btn-ghost btn-sm" onClick={() => setEditing(r)}>
                          Revise
                        </button>
                      )}
                    </td>
                  )}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      {editing && (
        <PublishRateModal
          prefill={editing}
          regions={regions}
          coverages={coverages}
          onClose={() => setEditing(null)}
          onPublished={handlePublished}
        />
      )}
    </div>
  );
}

function tomorrow() {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() + 1);
  return d.toISOString().slice(0, 10);
}

const FACTORS = [
  ["base_rate", "Base Rate ($ / year)", "0.01", 0.01],
  ["age_factor_young", "Young Driver Factor (< 25)", "0.01", 0.5],
  ["age_factor_senior", "Senior Driver Factor (65+)", "0.01", 0.5],
  ["vehicle_power_factor", "Vehicle Power Factor (per 50 kW)", "0.01", 0.5],
  ["bonus_malus_step", "Bonus-Malus Step", "0.01", 0.5],
];

function PublishRateModal({ prefill, regions, coverages, onClose, onPublished }) {
  const revising = Boolean(prefill.rate_table_id);
  const [form, setForm] = useState({
    region_id: prefill.region_id ? String(prefill.region_id) : "",
    coverage_id: prefill.coverage_id ? String(prefill.coverage_id) : "",
    effective_date: tomorrow(),
    base_rate: prefill.base_rate ?? "",
    age_factor_young: prefill.age_factor_young ?? "1.00",
    age_factor_senior: prefill.age_factor_senior ?? "1.00",
    vehicle_power_factor: prefill.vehicle_power_factor ?? "1.00",
    bonus_malus_step: prefill.bonus_malus_step ?? "1.00",
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const update = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const payload = { ...form, region_id: Number(form.region_id), coverage_id: Number(form.coverage_id) };
      FACTORS.forEach(([k]) => (payload[k] = Number(form[k])));
      onPublished(await api.publishRateVersion(payload));
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="modal-backdrop" style={{ display: "flex" }}>
      <div className="modal-box">
        <div className="modal-head">
          <h3>{revising ? `Revise ${prefill.coverage_name} · ${prefill.region_name}` : "New Rate Version"}</h3>
          <button className="modal-close" onClick={onClose} aria-label="Close">×</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <p className="form-note">
              The version in force will expire on the effective date you choose. Policies already issued keep their premium.
            </p>
            <div className="form-grid">
              <div className="form-group">
                <label htmlFor="rt-region">Region</label>
                <select id="rt-region" className="form-control" value={form.region_id} disabled={revising}
                  onChange={(e) => update("region_id", e.target.value)} required>
                  <option value="">Select…</option>
                  {regions.map((r) => <option key={r.region_id} value={r.region_id}>{r.name}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label htmlFor="rt-coverage">Coverage</label>
                <select id="rt-coverage" className="form-control" value={form.coverage_id} disabled={revising}
                  onChange={(e) => update("coverage_id", e.target.value)} required>
                  <option value="">Select…</option>
                  {coverages.map((c) => <option key={c.coverage_id} value={c.coverage_id}>{c.coverage_name}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label htmlFor="rt-effective">Effective Date</label>
                <input id="rt-effective" className="form-control" type="date" value={form.effective_date}
                  onChange={(e) => update("effective_date", e.target.value)} required />
              </div>
              {FACTORS.map(([k, label, step, min]) => (
                <div className="form-group" key={k}>
                  <label htmlFor={`rt-${k}`}>{label}</label>
                  <input id={`rt-${k}`} className="form-control" type="number" step={step} min={min}
                    value={form[k]} onChange={(e) => update(k, e.target.value)} required />
                </div>
              ))}
            </div>
            {error && <div className="form-error">{error}</div>}
          </div>
          <div className="modal-foot">
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? "Publishing…" : "Publish Version"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
