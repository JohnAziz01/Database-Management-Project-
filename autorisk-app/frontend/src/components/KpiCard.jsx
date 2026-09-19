/**
 * LESSON: a small, reusable, "presentational" component driven by props.
 *
 * `props` are just the attributes you pass when using a component, e.g.
 *   <KpiCard label="Active Policies" value={42} delta="+3 this month" />
 * Inside the component, `{ label, value, delta }` destructures those
 * props out of the single `props` object React passes in. This one
 * component replaces the repeated kpi-card template string from main.js
 * and gets reused on Dashboard, Claims, Risk Analysis, and Accounts.
 */
export default function KpiCard({ label, value, delta }) {
  return (
    <div className="kpi-card">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value}</div>
      {delta && <div className="kpi-delta">{delta}</div>}
    </div>
  );
}
