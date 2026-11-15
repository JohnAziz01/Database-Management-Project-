import { NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/quote", label: "New Quote" },
  { to: "/policies", label: "Policies" },
  { to: "/policyholders", label: "Policyholders" },
  { to: "/vehicles", label: "Vehicles" },
  { to: "/claims", label: "Claims" },
  { to: "/coverage", label: "Coverage" },
  { to: "/rate-tables", label: "Rate Tables" },
  { to: "/regions", label: "Regions" },
  { to: "/risk-analysis", label: "Risk Analysis" },
  { to: "/reports", label: "Reports" },
  { to: "/users", label: "Accounts" },
];

export default function Sidebar() {
  const { user, logout } = useAuth();

  return (
    <aside className="app-sidebar">
      <div className="brand-row">
        <div className="mark">AR</div>
        <div className="brand-name">AutoRisk</div>
      </div>

      <nav>
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) => "nav-link" + (isActive ? " active" : "")}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-foot">
        <div className="sidebar-user">{user?.email}</div>
        <button className="btn btn-ghost btn-sm" onClick={logout}>
          Sign out
        </button>
      </div>
    </aside>
  );
}
