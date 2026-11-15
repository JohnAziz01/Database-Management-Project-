export default function StatusPill({ value }) {
  const tone = String(value || "").toLowerCase().replace(/\s+/g, "-");
  return <span className={`pill pill-${tone}`}>{value}</span>;
}
