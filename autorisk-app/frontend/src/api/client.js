const BASE_URL = "/api"; // the Vite dev proxy forwards this to FastAPI

function authHeaders() {
  const token = localStorage.getItem("autorisk_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/**
 * FastAPI sends { "detail": "some text" } for most errors, but for 422
 * validation errors `detail` is a LIST like
 *   [{ loc: ["body", "email"], msg: "value is not a valid email address", ... }]
 * Passing that list straight to `new Error()` displayed "[object Object]"
 * (BUG-018). Turn it into readable text instead.
 */
function formatDetail(detail) {
  if (!Array.isArray(detail)) return detail;
  return detail
    .map((e) => {
      const field = (e.loc || []).filter((p) => p !== "body").join(".");
      const msg = (e.msg || "").replace(/^Value error, /, "");
      return field ? `${field.replaceAll("_", " ")}: ${msg}` : msg;
    })
    .join("; ");
}

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...options.headers,
    },
  });

  // Token missing/expired/rejected on a protected call: the saved session is
  // no longer valid, so sign out and go to the login page (BUG-024: the UI
  // used to keep looking "logged in" with a dead token).
  if (res.status === 401 && path !== "/auth/login") {
    localStorage.removeItem("autorisk_token");
    localStorage.removeItem("autorisk_user");
    window.location.assign("/login");
    throw new Error("Your session has expired. Please sign in again.");
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = formatDetail(body.detail) || detail;
    } catch {
      /* response wasn't JSON, keep statusText */
    }
    throw new Error(detail);
  }

  if (res.status === 204) return null; // no content
  return res.json();
}

export const api = {
  login: (email, password) =>
    request("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),

  me: () => request("/auth/me"),

  getDashboardSummary: () => request("/dashboard/summary"),
  getRecentClaims: () => request("/dashboard/recent-claims"),
  getPortfolio: () => request("/dashboard/portfolio"),

  getPolicyholders: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request(`/policyholders${qs ? `?${qs}` : ""}`);
  },
  createPolicyholder: (data) =>
    request("/policyholders", { method: "POST", body: JSON.stringify(data) }),

  getRegions: () => request("/regions"),
  getCoverages: () => request("/coverages"),
  getPolicies: () => request("/policies"),
  getClaims: () => request("/claims"),
  getVehicles: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request(`/vehicles${qs ? `?${qs}` : ""}`);
  },

  getQuoteOptions: () => request("/quote/options"),
  getQuote: (payload) => request("/quote", { method: "POST", body: JSON.stringify(payload) }),

  getRateTables: (params = {}) => request(`/rate-tables${qs(params)}`),
  publishRateVersion: (data) => request("/rate-tables", { method: "POST", body: JSON.stringify(data) }),

  getRiskDimensions: () => request("/risk/dimensions"),
  getRiskAnalysis: (dimension) => request(`/risk/analysis${qs({ dimension })}`),

  getReports: () => request("/reports"),
  getReport: (key, params = {}) => request(`/reports/${key}${qs(params)}`),
  downloadReport: (key, params = {}) => download(`/reports/${key}/csv${qs(params)}`),

  getAccounts: () => request("/accounts"),
  createAccount: (data) => request("/accounts", { method: "POST", body: JSON.stringify(data) }),
  updateAccount: (id, data) => request(`/accounts/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  resetPassword: (id, newPassword) =>
    request(`/accounts/${id}/reset-password`, { method: "POST", body: JSON.stringify({ new_password: newPassword }) }),
};

// Build "?a=1&b=2" from an object, skipping empty values.
function qs(params) {
  const clean = Object.fromEntries(Object.entries(params).filter(([, v]) => v !== "" && v != null));
  const s = new URLSearchParams(clean).toString();
  return s ? `?${s}` : "";
}

// File downloads need the Bearer token too, so a plain <a href> won't do:
// fetch the file, then hand the browser a temporary blob URL to save.
async function download(path) {
  const res = await fetch(`${BASE_URL}${path}`, { headers: authHeaders() });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = formatDetail((await res.json()).detail) || detail;
    } catch {
      /* not JSON */
    }
    throw new Error(detail);
  }
  const name = /filename="([^"]+)"/.exec(res.headers.get("Content-Disposition") || "")?.[1] || "report.csv";
  const url = URL.createObjectURL(await res.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
