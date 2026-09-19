/**
 * LESSON: layout components + <Outlet>.
 *
 * In the old app, every page (dashboard.html, claims.html, ...) duplicated
 * <div id="app-shell"> and called renderShell(). In React we write that
 * shell ONCE as <Layout>, and each individual page becomes the "hole" that
 * react-router drops into <Outlet />. See App.jsx for how routes nest
 * inside this layout.
 */
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
