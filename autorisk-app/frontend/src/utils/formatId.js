// Display IDs like POL-0042. Rows imported from the freMTPL2 data handoff use
// negative IDs (so they never collide with the app's own serial IDs); show
// those as historical records, e.g. POL-H0001, instead of "POL-00-1".
export function formatId(prefix, id) {
  const n = Number(id);
  return n < 0
    ? `${prefix}-H${String(-n).padStart(4, "0")}`
    : `${prefix}-${String(n).padStart(4, "0")}`;
}
