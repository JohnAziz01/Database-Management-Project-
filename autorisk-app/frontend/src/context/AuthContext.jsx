import { createContext, useContext, useState, useCallback, useEffect } from "react";
import { api } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  // useState gives us a piece of state (`user`) and a setter (`setUser`).
  // Lazy initializer function: read localStorage once, on first render only.
  const [user, setUser] = useState(() => {
    const raw = localStorage.getItem("autorisk_user");
    return raw ? JSON.parse(raw) : null;
  });

  // useCallback just memoizes the function so it doesn't get recreated on
  // every render (matters more once you pass it deep into children).
  const login = useCallback(async (email, password) => {
    const result = await api.login(email, password);
    localStorage.setItem("autorisk_token", result.access_token);
    const loggedInUser = {
      accountId: result.account_id,
      email: result.email,
      accountType: result.account_type,
      adminRole: result.admin_role ?? null,
    };
    localStorage.setItem("autorisk_user", JSON.stringify(loggedInUser));
    setUser(loggedInUser); // <-- this triggers a re-render of everything
    // that reads `user` from context, e.g. the sidebar and route guards.
    return loggedInUser;
  }, []);

  // Sessions saved before staff roles existed have no adminRole: fetch it once.
  useEffect(() => {
    if (user && user.adminRole === undefined) {
      api
        .me()
        .then((me) => {
          const updated = { ...user, adminRole: me.admin_role ?? null };
          localStorage.setItem("autorisk_user", JSON.stringify(updated));
          setUser(updated);
        })
        .catch(() => {});
    }
  }, [user]);

  const logout = useCallback(() => {
    localStorage.removeItem("autorisk_token");
    localStorage.removeItem("autorisk_user");
    setUser(null);
  }, []);

  // The `value` object is what every consumer of useAuth() receives.
  // Administrators and Managers may change rates and accounts; Analysts only view.
  const canManage = user?.accountType === "Admin" && ["Administrator", "Manager"].includes(user?.adminRole);
  const value = { user, login, logout, isAuthenticated: !!user, canManage };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// Custom hook: components call useAuth() instead of useContext(AuthContext).
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
