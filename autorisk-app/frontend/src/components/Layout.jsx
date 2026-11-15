import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";

export default function Layout({ title, breadcrumbs = [] }) {
  return (
    <div className="app-shell">
      <Sidebar />
      <main className="app-main">
        <header className="app-topbar">
          <div className="breadcrumbs">{breadcrumbs.join(" / ") || title}</div>
          <h1>{title}</h1>
        </header>
        <div className="page-content">
          {/* Whatever child route matched renders here */}
          <Outlet />
        </div>
      </main>
    </div>
  );
}
