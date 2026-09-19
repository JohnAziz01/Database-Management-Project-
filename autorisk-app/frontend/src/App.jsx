/**
 * LESSON: React Router's route tree.
 *
 * <Routes> looks at the current URL and renders whichever <Route> matches.
 * Nesting matters here: everything nested inside the RequireAuth ->
 * Layout routes automatically gets the sidebar/topbar AND the login
 * check, without each page having to remember to add either one. This
 * is the same "wrap once, reuse everywhere" idea as Layout.jsx itself.
 */
import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import RequireAuth from "./components/RequireAuth";

import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Quote from "./pages/Quote";
import Policies from "./pages/Policies";
import Policyholders from "./pages/Policyholders";
import Vehicles from "./pages/Vehicles";
import Claims from "./pages/Claims";
import Coverage from "./pages/Coverage";
import Regions from "./pages/Regions";
import ComingSoon from "./pages/ComingSoon";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      {/* Every route below requires a logged-in user (RequireAuth), and
          every one of them renders inside the shared sidebar/topbar
          shell (Layout). */}
      <Route element={<RequireAuth />}>
        <Route element={<Layout title="Executive Dashboard" breadcrumbs={["Dashboard"]} />}>
          <Route path="/dashboard" element={<Dashboard />} />
        </Route>
        <Route element={<Layout title="New Insurance Quote" breadcrumbs={["Quote", "New"]} />}>
          <Route path="/quote" element={<Quote />} />
        </Route>
        <Route element={<Layout title="Policies" breadcrumbs={["Policies"]} />}>
          <Route path="/policies" element={<Policies />} />
        </Route>
        <Route element={<Layout title="Policyholders" breadcrumbs={["Policyholders"]} />}>
          <Route path="/policyholders" element={<Policyholders />} />
        </Route>
        <Route element={<Layout title="Vehicles" breadcrumbs={["Vehicles"]} />}>
          <Route path="/vehicles" element={<Vehicles />} />
        </Route>
        <Route element={<Layout title="Claims" breadcrumbs={["Claims"]} />}>
          <Route path="/claims" element={<Claims />} />
        </Route>
        <Route element={<Layout title="Coverage" breadcrumbs={["Coverage"]} />}>
          <Route path="/coverage" element={<Coverage />} />
        </Route>
        <Route element={<Layout title="Regions" breadcrumbs={["Administration", "Regions"]} />}>
          <Route path="/regions" element={<Regions />} />
        </Route>
        <Route element={<Layout title="Pricing / Rate Tables" breadcrumbs={["Pricing", "Rate Tables"]} />}>
          <Route path="/rate-tables" element={<ComingSoon title="Rate Tables" />} />
        </Route>
        <Route element={<Layout title="Risk Analysis" breadcrumbs={["Risk Analysis"]} />}>
          <Route path="/risk-analysis" element={<ComingSoon title="Risk Analysis" />} />
        </Route>
        <Route element={<Layout title="Reports" breadcrumbs={["Reports"]} />}>
          <Route path="/reports" element={<ComingSoon title="Reports" />} />
        </Route>
        <Route element={<Layout title="Accounts / Security" breadcrumbs={["Accounts"]} />}>
          <Route path="/users" element={<ComingSoon title="Accounts" />} />
        </Route>
      </Route>

      {/* Anything else (including "/") redirects to the dashboard, which
          itself redirects to /login if nobody's signed in. */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
