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
