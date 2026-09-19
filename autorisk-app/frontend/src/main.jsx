/**
 * LESSON 1: Every React app has one entry point.
 *
 * `ReactDOM.createRoot(...).render(<App />)` tells React: "take over this
 * one <div id="root"> in index.html, and from now on YOU decide what's
 * inside it." Everything the user sees is produced by the <App /> component
 * tree below — there is no more hand-written HTML after this point.
 *
 * <React.StrictMode> is a dev-only helper that intentionally double-runs
 * some code to help you catch bugs (like side effects in the wrong place).
 * It does nothing in production and is safe to leave in.
 */
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App.jsx";
import { AuthProvider } from "./context/AuthContext.jsx";
import "./styles/index.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    {/* BrowserRouter enables client-side routing: clicking a <Link>
        changes the URL and swaps components WITHOUT a full page reload. */}
    <BrowserRouter>
      {/* AuthProvider makes "who is logged in" available to any component
          in the tree via the useAuth() hook, without passing props down
          manually through every layer ("prop drilling"). More on this in
          context/AuthContext.jsx. */}
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>
);
