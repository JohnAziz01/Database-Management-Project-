/**
 * LESSON: controlled inputs, useState, forms, and events.
 *
 * In plain HTML/JS (the old login.html), the <input> owns its own value
 * and you reach into the DOM with document.getElementById(...).value when
 * you need it. In React, we usually flip that: STATE owns the value, and
 * the <input> just reflects whatever state currently holds. That's a
 * "controlled input" — value={email} + onChange={...} together mean
 * "this input's value is always exactly what `email` says it is".
 *
 * Why bother? Because now `email` is just a normal JS variable you can
 * validate, transform, or send to an API — no DOM queries required, and
 * React automatically re-renders anything that depends on it.
 */
import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  // useState(initialValue) returns [currentValue, setterFunction].
  // Every call to the setter schedules a re-render with the new value.
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  async function handleSubmit(e) {
    e.preventDefault(); // stop the browser's default full-page form submit
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      // If RequireAuth redirected us here from a protected page, send the
      // user back to where they were headed; otherwise go to /dashboard.
      const redirectTo = location.state?.from?.pathname || "/dashboard";
      navigate(redirectTo, { replace: true });
    } catch (err) {
      setError(err.message || "Sign in failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="login-shell">
      <aside className="login-aside">
        <div className="brand-row">
          <div className="mark">AR</div>
          <div>
            <div className="brand-name">AutoRisk</div>
            <div className="brand-sub">Car Insurance Pricing &amp; Risk Analytics</div>
          </div>
        </div>
        <p className="aside-quote">
          Rate every policy on <span className="accent">actual risk</span> — driver
          history, vehicle profile, and regional loss experience, all in one workspace.
        </p>
      </aside>

      <div className="login-main">
        <div className="login-card">
          <h1>Sign in</h1>
          <p className="login-sub">Enter your credentials to access the AutoRisk dashboard.</p>

          <form className="login-form" onSubmit={handleSubmit} noValidate>
            <div className="form-group">
              <label htmlFor="login-email">Email</label>
              <input
                className="form-control"
                type="email"
                id="login-email"
                value={email}
                // Every keystroke fires onChange -> we update state ->
                // React re-renders the input with the new value. This is
                // the core React loop: event -> state update -> re-render.
                onChange={(e) => setEmail(e.target.value)}
                placeholder="analyst@autorisk.demo"
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="login-password">Password</label>
              <input
                className="form-control"
                type="password"
                id="login-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
              />
            </div>

            {/* Conditional rendering: `error && <div>...</div>` only
                renders the div when `error` is truthy. This is the most
                common pattern for "show this if that". */}
            {error && <div className="form-error">{error}</div>}

            <button type="submit" className="btn btn-primary btn-lg btn-block" disabled={submitting}>
              {submitting ? "Signing in…" : "Sign in"}
            </button>
          </form>

          <p className="login-footnote">
            CSCI-4560 Database Management Systems Project · authenticated against
            FastAPI + PostgreSQL.
          </p>
        </div>
      </div>
    </div>
  );
}
