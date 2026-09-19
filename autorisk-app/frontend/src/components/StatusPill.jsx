/**
 * LESSON: conditional rendering / conditional CSS classes.
 *
 * This replaces the old statusPill()/riskPill() helper functions in
 * main.js. Notice there's no if/else needed for the markup itself — we
 * compute a CSS class name from the `value` prop and let CSS handle the
 * color, keeping the JSX itself simple.
 */
export default function StatusPill({ value }) {
  const tone = String(value || "").toLowerCase().replace(/\s+/g, "-");
  return <span className={`pill pill-${tone}`}>{value}</span>;
}
