import { useEffect, useState } from "react";
import { api } from "../api/client";

const initialForm = {
  date_of_birth: "",
  license_issue_date: "",
  bonus_malus_coefficient: "1.00",
  vehicle_manufacture_year: "",
  vehicle_power_kw: "",
  region_id: "",
  coverage_id: "",
};

export default function Quote() {
  // BUG-009 fix: instead of every region x every coverage, load only the
  // pairs that have a current rate table, so every choice can be priced.
  const [options, setOptions] = useState([]);
  const [form, setForm] = useState(initialForm);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api.getQuoteOptions().then(setOptions).catch((err) => setError(err.message));
  }, []);

  // Unique regions that have at least one priced coverage...
  const regions = [...new Map(options.map((o) => [o.region_id, o.region_name])).entries()];
  // ...and the coverages priced in the region currently selected.
  const coverages = options.filter((o) => String(o.region_id) === form.region_id);

  function update(field, value) {
    setForm((prev) => {
      const next = { ...prev, [field]: value };
      // Changing region clears a coverage that isn't priced in the new region.
      if (field === "region_id" && !options.some((o) => String(o.region_id) === value && String(o.coverage_id) === prev.coverage_id)) {
        next.coverage_id = "";
      }
      return next;
    });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    setResult(null);
    try {
      const quote = await api.getQuote({
        ...form,
        bonus_malus_coefficient: Number(form.bonus_malus_coefficient),
        vehicle_manufacture_year: Number(form.vehicle_manufacture_year),
        vehicle_power_kw: Number(form.vehicle_power_kw),
        region_id: Number(form.region_id),
        coverage_id: Number(form.coverage_id),
      });
      setResult(quote);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="grid-2">
      <form onSubmit={handleSubmit}>
        <div className="card card-pad" style={{ marginBottom: 18 }}>
          <div className="form-section-title">Driver &amp; Vehicle</div>
          <div className="form-grid">
            <div className="form-group">
              <label htmlFor="q-dob">Date of Birth</label>
              <input
                id="q-dob"
                className="form-control"
                type="date"
                value={form.date_of_birth}
                onChange={(e) => update("date_of_birth", e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label htmlFor="q-license-date">License Issue Date</label>
              <input
                id="q-license-date"
                className="form-control"
                type="date"
                value={form.license_issue_date}
                onChange={(e) => update("license_issue_date", e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label htmlFor="q-bonus-malus">Bonus-Malus Coefficient</label>
              <input
                id="q-bonus-malus"
                className="form-control"
                type="number"
                step="0.01"
                min="0.5"
                max="3.5"
                value={form.bonus_malus_coefficient}
                onChange={(e) => update("bonus_malus_coefficient", e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label htmlFor="q-vehicle-year">Vehicle Manufacture Year</label>
              <input
                id="q-vehicle-year"
                className="form-control"
                type="number"
                value={form.vehicle_manufacture_year}
                onChange={(e) => update("vehicle_manufacture_year", e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label htmlFor="q-vehicle-power">Vehicle Power (kW)</label>
              <input
                id="q-vehicle-power"
                className="form-control"
                type="number"
                value={form.vehicle_power_kw}
                onChange={(e) => update("vehicle_power_kw", e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label htmlFor="q-region">Region</label>
              <select
                id="q-region"
                className="form-control"
                value={form.region_id}
                onChange={(e) => update("region_id", e.target.value)}
                required
              >
                <option value="">Select…</option>
                {regions.map(([id, name]) => (
                  <option key={id} value={id}>
                    {name}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label htmlFor="q-coverage">Coverage</label>
              <select
                id="q-coverage"
                className="form-control"
                value={form.coverage_id}
                onChange={(e) => update("coverage_id", e.target.value)}
                disabled={!form.region_id}
                required
              >
                <option value="">{form.region_id ? "Select…" : "Choose a region first"}</option>
                {coverages.map((c) => (
                  <option key={c.coverage_id} value={c.coverage_id}>
                    {c.coverage_name}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
        {error && <div className="form-error">{error}</div>}
        <button type="submit" className="btn btn-primary btn-lg" disabled={submitting}>
          {submitting ? "Calculating…" : "Calculate Quote"}
        </button>
      </form>

      <div className="card" style={{ position: "sticky", top: 88 }}>
        <div className="card-header">
          <div>
            <h3>Quote Result</h3>
            <div className="subtitle">Computed by FastAPI from live rate tables</div>
          </div>
        </div>
        <div className="card-pad result-panel">
          {!result ? (
            <div className="empty-state">Fill in the form and calculate a quote.</div>
          ) : (
            <>
              <div className="result-hero">
                <div className="result-label">Estimated Premium</div>
                <div className="result-value data">${result.estimated_premium.toFixed(2)} / year</div>
              </div>
              <div className="metric-list">
                <div className="metric-row">
                  <span className="m-label">Risk Level</span>
                  <span className="m-value">{result.risk_level}</span>
                </div>
                <div className="metric-row">
                  <span className="m-label">Estimated Claim Frequency</span>
                  <span className="m-value data">{(result.estimated_claim_frequency * 100).toFixed(2)}%</span>
                </div>
                <div className="metric-row">
                  <span className="m-label">Estimated Claim Severity</span>
                  <span className="m-value data">${result.estimated_claim_severity.toFixed(2)}</span>
                </div>
                <div className="metric-row">
                  <span className="m-label">Pure Premium</span>
                  <span className="m-value data">${result.pure_premium.toFixed(2)}</span>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
