import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import StatusPill from "../components/StatusPill";
import { formatId } from "../utils/formatId";

const ROLES = ["Analyst", "Administrator", "Manager"];

function when(ts) {
  return ts ? new Date(ts.endsWith("Z") ? ts : ts + "Z").toLocaleString() : "Never";
}

export default function Accounts() {
  const { user, canManage } = useAuth();
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [adding, setAdding] = useState(false);
  const [resetting, setResetting] = useState(null);

  const load = useCallback(() => {
    setLoading(true);
    api
      .getAccounts()
      .then(setAccounts)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);
  useEffect(load, [load]);

  async function change(account, data, message) {
    setError(null);
    setNotice(null);
    try {
      await api.updateAccount(account.account_id, data);
      setNotice(message);
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  const staff = accounts.filter((a) => a.account_type === "Admin").length;

  return (
    <div className="card">
      <div className="table-toolbar">
        <div className="muted">
          {accounts.length} accounts · {staff} staff · {accounts.length - staff} customers
          {!canManage && " · read-only for Analysts"}
        </div>
        {canManage && (
          <button className="btn btn-primary" onClick={() => setAdding(true)}>
            Add Account
          </button>
        )}
      </div>
      {notice && <div className="form-success">{notice}</div>}
      {error && <div className="form-error">{error}</div>}
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>Email</th>
              <th>Type</th>
              <th>Role / Policyholder</th>
              <th>Status</th>
              <th>Last Sign-in</th>
              {canManage && <th>Actions</th>}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} className="empty-state">Loading…</td></tr>
            ) : (
              accounts.map((a) => {
                const self = a.account_id === user?.accountId;
                return (
                  <tr key={a.account_id}>
                    <td className="cell-strong">
                      {a.email}
                      {self && <span className="tag">you</span>}
                    </td>
                    <td>{a.account_type === "Admin" ? "Staff" : "Customer"}</td>
                    <td>
                      {a.account_type === "Admin" ? (
                        canManage && !self ? (
                          <select className="field-sm" aria-label={`Role for ${a.email}`} value={a.admin_role}
                            onChange={(e) => change(a, { admin_role: e.target.value }, `${a.email} is now ${e.target.value}.`)}>
                            {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                          </select>
                        ) : (
                          a.admin_role
                        )
                      ) : (
                        <span>
                          {a.policyholder_name} <span className="muted">({formatId("PH", a.policyholder_id)})</span>
                        </span>
                      )}
                    </td>
                    <td><StatusPill value={a.is_active ? "Active" : "Disabled"} /></td>
                    <td>{when(a.last_login_at)}</td>
                    {canManage && (
                      <td>
                        <div className="row-actions">
                        {!self && (
                          <button className="btn btn-ghost btn-sm"
                            onClick={() => change(a, { is_active: !a.is_active },
                              `${a.email} ${a.is_active ? "disabled" : "enabled"}.`)}>
                            {a.is_active ? "Disable" : "Enable"}
                          </button>
                        )}
                        <button className="btn btn-ghost btn-sm" onClick={() => setResetting(a)}>
                          Reset password
                        </button>
                        </div>
                      </td>
                    )}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
      {adding && (
        <AddAccountModal
          accounts={accounts}
          onClose={() => setAdding(false)}
          onCreated={(a) => {
            setAdding(false);
            setNotice(`Created ${a.email}.`);
            load();
          }}
        />
      )}
      {resetting && (
        <ResetPasswordModal
          account={resetting}
          onClose={() => setResetting(null)}
          onDone={() => {
            setNotice(`Password reset for ${resetting.email}.`);
            setResetting(null);
          }}
        />
      )}
    </div>
  );
}

function AddAccountModal({ accounts, onClose, onCreated }) {
  const [form, setForm] = useState({ account_type: "Admin", email: "", password: "", admin_role: "Analyst", policyholder_id: "" });
  const [policyholders, setPolicyholders] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const update = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  useEffect(() => {
    // Only policyholders without an account can get one.
    const taken = new Set(accounts.map((a) => a.policyholder_id).filter(Boolean));
    api
      .getPolicyholders()
      .then((list) => setPolicyholders(list.filter((p) => !taken.has(p.policyholder_id))))
      .catch((err) => setError(err.message));
  }, [accounts]);

  function pickPolicyholder(id) {
    const ph = policyholders.find((p) => String(p.policyholder_id) === id);
    setForm((f) => ({ ...f, policyholder_id: id, email: f.email || ph?.email || "" }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    const customer = form.account_type === "Customer";
    try {
      onCreated(
        await api.createAccount({
          email: form.email,
          password: form.password,
          account_type: form.account_type,
          admin_role: customer ? null : form.admin_role,
          policyholder_id: customer ? Number(form.policyholder_id) : null,
        }),
      );
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
          <h3>Add Account</h3>
          <button className="modal-close" onClick={onClose} aria-label="Close">×</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <div className="form-grid">
              <div className="form-group">
                <label htmlFor="acc-type">Account Type</label>
                <select id="acc-type" className="form-control" value={form.account_type}
                  onChange={(e) => update("account_type", e.target.value)}>
                  <option value="Admin">Staff</option>
                  <option value="Customer">Customer</option>
                </select>
              </div>
              {form.account_type === "Admin" ? (
                <div className="form-group">
                  <label htmlFor="acc-role">Role</label>
                  <select id="acc-role" className="form-control" value={form.admin_role}
                    onChange={(e) => update("admin_role", e.target.value)}>
                    {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                  </select>
                </div>
              ) : (
                <div className="form-group">
                  <label htmlFor="acc-ph">Policyholder</label>
                  <select id="acc-ph" className="form-control" value={form.policyholder_id}
                    onChange={(e) => pickPolicyholder(e.target.value)} required>
                    <option value="">Select…</option>
                    {policyholders.map((p) => (
                      <option key={p.policyholder_id} value={p.policyholder_id}>
                        {p.first_name} {p.last_name} ({formatId("PH", p.policyholder_id)})
                      </option>
                    ))}
                  </select>
                </div>
              )}
              <div className="form-group">
                <label htmlFor="acc-email">Email</label>
                <input id="acc-email" className="form-control" type="email" value={form.email}
                  onChange={(e) => update("email", e.target.value)} required />
              </div>
              <div className="form-group">
                <label htmlFor="acc-password">Temporary Password</label>
                <input id="acc-password" className="form-control" type="password" minLength={8} value={form.password}
                  onChange={(e) => update("password", e.target.value)} required autoComplete="new-password" />
              </div>
            </div>
            <p className="form-note">
              Analysts can view everything but cannot change rates or accounts. Administrators and Managers can.
            </p>
            {error && <div className="form-error">{error}</div>}
          </div>
          <div className="modal-foot">
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? "Creating…" : "Create Account"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function ResetPasswordModal({ account, onClose, onDone }) {
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api.resetPassword(account.account_id, password);
      onDone();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="modal-backdrop" style={{ display: "flex" }}>
      <div className="modal-box modal-sm">
        <div className="modal-head">
          <h3>Reset password</h3>
          <button className="modal-close" onClick={onClose} aria-label="Close">×</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <p className="form-note">Set a new password for <strong>{account.email}</strong>. Share it with them securely.</p>
            <div className="form-group">
              <label htmlFor="reset-pw">New Password (8+ characters)</label>
              <input id="reset-pw" className="form-control" type="password" minLength={8} value={password}
                onChange={(e) => setPassword(e.target.value)} required autoComplete="new-password" />
            </div>
            {error && <div className="form-error">{error}</div>}
          </div>
          <div className="modal-foot">
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? "Saving…" : "Set Password"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
