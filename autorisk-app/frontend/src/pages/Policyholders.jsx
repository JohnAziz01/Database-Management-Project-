import { useEffect, useState } from "react";
import { api } from "../api/client";

export default function Policyholders() {
  const [policyholders, setPolicyholders] = useState([]);
  const [regions, setRegions] = useState([]);
  const [search, setSearch] = useState("");
  const [regionId, setRegionId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showAddForm, setShowAddForm] = useState(false);

  // Load the region dropdown options once, on mount.
  useEffect(() => {
    api.getRegions().then(setRegions).catch((err) => setError(err.message));
  }, []);

  // Re-fetch policyholders whenever `search` or `regionId` changes.
  // Unlike Dashboard's effect (deps = []), this effect's dependency array
  // is [search, regionId] — React re-runs it any time either value
  // changes, which is exactly what "live search" needs.
  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    // A small debounce: wait 300ms after the user stops typing before
    // actually calling the API, so we're not firing a request per
    // keystroke. `setTimeout` schedules the call; the cleanup function
    // cancels it if `search`/`regionId` changes again before it fires.
    const timer = setTimeout(async () => {
      try {
        const params = {};
        if (search) params.q = search;
        if (regionId) params.region_id = regionId;
        const data = await api.getPolicyholders(params);
        if (!cancelled) setPolicyholders(data);
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, 300);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [search, regionId]);

  async function handleCreated() {
    setShowAddForm(false);
    // Re-request the list with the SAME filters the user has on screen.
    // (BUG-019: this used to pass only the search text, so the region
    // filter was silently dropped while the dropdown still showed it.)
    const params = {};
    if (search) params.q = search;
    if (regionId) params.region_id = regionId;
    const data = await api.getPolicyholders(params);
    setPolicyholders(data);
  }

  return (
    <div className="card">
      <div className="table-toolbar">
        <div className="toolbar-filters">
          <div className="search-input">
            <input
              placeholder="Search name, email, or license…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <select value={regionId} onChange={(e) => setRegionId(e.target.value)} className="field-sm">
            <option value="">All Regions</option>
            {regions.map((r) => (
              <option key={r.region_id} value={r.region_id}>
                {r.name}
              </option>
            ))}
          </select>
        </div>
        <button className="btn btn-primary" onClick={() => setShowAddForm(true)}>
          Add Policyholder
        </button>
      </div>

      {error && <div className="form-error">{error}</div>}

      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>Email</th>
              <th>License #</th>
              <th>Region</th>
              <th>Risk Tier</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6} className="empty-state">
                  Loading…
                </td>
              </tr>
            ) : policyholders.length === 0 ? (
              <tr>
                <td colSpan={6} className="empty-state">
                  No policyholders match your filters.
                </td>
              </tr>
            ) : (
              policyholders.map((p) => (
                <tr key={p.policyholder_id}>
                  <td className="cell-strong">PH-{String(p.policyholder_id).padStart(4, "0")}</td>
                  <td>
                    {p.first_name} {p.last_name}
                  </td>
                  <td>{p.email}</td>
                  <td>{p.license_number}</td>
                  <td>{regions.find((r) => r.region_id === p.region_id)?.name || "—"}</td>
                  <td>{p.risk_tier || "—"}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {showAddForm && (
        <AddPolicyholderModal
          regions={regions}
          onClose={() => setShowAddForm(false)}
          onCreated={handleCreated}
        />
      )}
    </div>
  );
}

/**
 * A separate component for the "add" form. Splitting it out keeps
 * Policyholders.jsx focused on the list, and demonstrates passing
 * callback props down (`onClose`, `onCreated`) so a child component can
 * tell its parent "I'm done" without needing to know how the parent
 * actually handles that.
 */
function AddPolicyholderModal({ regions, onClose, onCreated }) {
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    date_of_birth: "",
    license_number: "",
    license_issue_date: "",
    email: "",
    phone: "",
    region_id: "",
    risk_tier: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  // One generic handler for every field, keyed by the input's `name`
  // attribute — avoids writing a separate onChange per field.
  function update(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api.createPolicyholder({
        ...form,
        region_id: form.region_id ? Number(form.region_id) : null,
        risk_tier: form.risk_tier || null,
        phone: form.phone || null,
      });
      onCreated();
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
          <h3>Add Policyholder</h3>
          <button className="modal-close" onClick={onClose}>
            ×
          </button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <div className="form-grid">
              <div className="form-group">
                <label htmlFor="ph-first-name">First Name</label>
                <input
                  id="ph-first-name"
                  className="form-control"
                  value={form.first_name}
                  onChange={(e) => update("first_name", e.target.value)}
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="ph-last-name">Last Name</label>
                <input
                  id="ph-last-name"
                  className="form-control"
                  value={form.last_name}
                  onChange={(e) => update("last_name", e.target.value)}
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="ph-dob">Date of Birth</label>
                <input
                  id="ph-dob"
                  className="form-control"
                  type="date"
                  value={form.date_of_birth}
                  onChange={(e) => update("date_of_birth", e.target.value)}
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="ph-license-number">License Number</label>
                <input
                  id="ph-license-number"
                  className="form-control"
                  value={form.license_number}
                  onChange={(e) => update("license_number", e.target.value)}
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="ph-license-date">License Issue Date</label>
                <input
                  id="ph-license-date"
                  className="form-control"
                  type="date"
                  value={form.license_issue_date}
                  onChange={(e) => update("license_issue_date", e.target.value)}
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="ph-email">Email</label>
                <input
                  id="ph-email"
                  className="form-control"
                  type="email"
                  value={form.email}
                  onChange={(e) => update("email", e.target.value)}
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="ph-phone">Phone</label>
                <input
                  id="ph-phone"
                  className="form-control"
                  value={form.phone}
                  onChange={(e) => update("phone", e.target.value)}
                />
              </div>
              <div className="form-group">
                <label htmlFor="ph-region">Region</label>
                <select
                  id="ph-region"
                  className="form-control"
                  value={form.region_id}
                  onChange={(e) => update("region_id", e.target.value)}
                >
                  <option value="">Not specified</option>
                  {regions.map((r) => (
                    <option key={r.region_id} value={r.region_id}>
                      {r.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label htmlFor="ph-risk-tier">Risk Tier</label>
                <select
                  id="ph-risk-tier"
                  className="form-control"
                  value={form.risk_tier}
                  onChange={(e) => update("risk_tier", e.target.value)}
                >
                  <option value="">Not specified</option>
                  <option value="Low">Low</option>
                  <option value="Medium">Medium</option>
                  <option value="High">High</option>
                </select>
              </div>
            </div>
            {error && <div className="form-error">{error}</div>}
          </div>
          <div className="modal-foot">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? "Saving…" : "Save Policyholder"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
