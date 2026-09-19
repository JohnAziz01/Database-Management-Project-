/**
 * LESSON: a tiny wrapper around fetch().
 *
 * In the old HTML/mock-data version, every page read from a hardcoded
 * MOCK object. Now, every page calls one of the functions below, which
 * calls the real FastAPI backend, which queries real PostgreSQL.
 *
 * Centralizing fetch logic here means: one place to add the auth token,
 * one place to handle errors consistently, and pages themselves stay
 * simple ("give me the policyholders" instead of "build a fetch request").
 */

const BASE_URL = "/api"; // the Vite dev proxy forwards this to FastAPI

function authHeaders() {
  const token = localStorage.getItem("autorisk_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
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

  if (!res.ok) {
    // FastAPI sends { "detail": "..." } on errors — surface it.
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
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

  getQuote: (payload) => request("/quote", { method: "POST", body: JSON.stringify(payload) }),
};
