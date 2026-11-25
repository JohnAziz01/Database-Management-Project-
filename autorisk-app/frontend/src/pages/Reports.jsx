import { useEffect, useState } from "react";
import { api } from "../api/client";
import { formatId } from "../utils/formatId";

// Standard business reports: pick one, optionally limit the dates, preview
// the first rows here and download every row as CSV.
const PREVIEW_ROWS = 100;

function label(column) {
  return column.replaceAll("_", " ");
}

const ID_PREFIX = { claim_id: "CLM", policy_id: "POL", policyholder_id: "PH", vehicle_id: "VEH" };

function cell(column, value) {
  if (value == null || value === "") return "—";
  if (ID_PREFIX[column]) return formatId(ID_PREFIX[column], value);
  if (typeof value === "number") {
    if (column === "loss_ratio") return `${(value * 100).toFixed(1)}%`;
    if (/premium|amount|paid|limit|deductible/.test(column)) {
      return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }
    return value.toLocaleString();
  }
  return String(value);
}

export default function Reports() {
  const [catalog, setCatalog] = useState([]);
  const [selected, setSelected] = useState(null);
  const [range, setRange] = useState({ date_from: "", date_to: "" });
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .getReports()
      .then((list) => {
        setCatalog(list);
        setSelected(list[0]?.key ?? null);
      })
      .catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    if (!selected) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .getReport(selected, { ...range, limit: PREVIEW_ROWS })
      .then((r) => !cancelled && setReport(r))
      .catch((err) => !cancelled && setError(err.message))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [selected, range]);

  async function handleDownload() {
    setDownloading(true);
    setError(null);
    try {
      await api.downloadReport(selected, range);
    } catch (err) {
      setError(err.message);
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div className="reports-layout">
      <nav className="card report-list" aria-label="Reports">
        {catalog.map((r) => (
          <button
            key={r.key}
            className={`report-item${r.key === selected ? " active" : ""}`}
            aria-current={r.key === selected ? "true" : undefined}
            onClick={() => setSelected(r.key)}
          >
            <span className="report-title">{r.title}</span>
            <span className="report-desc">{r.description}</span>
          </button>
        ))}
      </nav>

      <div className="card report-view">
        <div className="card-header">
          <div>
            <h3>{report?.title || "Report"}</h3>
            <div className="subtitle">
              {report ? `${report.total_rows.toLocaleString()} rows` : "…"}
              {report && report.total_rows > report.rows.length ? ` · showing the first ${report.rows.length}` : ""}
            </div>
          </div>
          <button className="btn btn-primary" onClick={handleDownload} disabled={!selected || downloading}>
            {downloading ? "Preparing…" : "Download CSV"}
          </button>
        </div>
        <div className="table-toolbar">
          <div className="toolbar-filters">
            <label className="inline-field">
              From
              <input type="date" className="field-sm" value={range.date_from}
                onChange={(e) => setRange((r) => ({ ...r, date_from: e.target.value }))} />
            </label>
            <label className="inline-field">
              To
              <input type="date" className="field-sm" value={range.date_to}
                onChange={(e) => setRange((r) => ({ ...r, date_to: e.target.value }))} />
            </label>
            {(range.date_from || range.date_to) && (
              <button className="btn btn-ghost btn-sm" onClick={() => setRange({ date_from: "", date_to: "" })}>
                Clear dates
              </button>
            )}
          </div>
        </div>
        {error && <div className="form-error">{error}</div>}
        <div className="table-scroll report-scroll">
          <table className="data-table compact">
            <thead>
              <tr>
                {(report?.columns || []).map((c) => (
                  <th key={c} className={typeof report.rows[0]?.[report.columns.indexOf(c)] === "number" && !ID_PREFIX[c] ? "num" : ""}>
                    {label(c)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={99} className="empty-state">Loading…</td></tr>
              ) : !report || report.rows.length === 0 ? (
                <tr><td colSpan={99} className="empty-state">No rows for these dates.</td></tr>
              ) : (
                report.rows.map((row, i) => (
                  <tr key={i}>
                    {row.map((v, j) => (
                      <td key={j} className={typeof v === "number" && !ID_PREFIX[report.columns[j]] ? "num data" : ""}>
                        {cell(report.columns[j], v)}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
