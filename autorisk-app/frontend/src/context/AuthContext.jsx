/**
 * LESSON: React Context = "global state without prop drilling".
 *
 * Without context, if <App> knew the logged-in user, and a deeply nested
 * <Sidebar><UserBadge> needed it too, you'd have to pass `user` as a prop
 * through every component in between, even ones that don't care about it.
 * That's called "prop drilling" and it gets painful fast.
 *
 * Context lets any descendant component "subscribe" directly:
 *   const { user, login, logout } = useAuth();
 * no matter how deeply nested it is.
 *
 * Steps to build a context:
 *   1. createContext()            -> the "channel"
 *   2. a Provider component       -> holds the actual state (useState) and
 *                                    broadcasts it down the tree
 *   3. a custom hook (useAuth)    -> a convenience wrapper so components
 *                                    don't need to import useContext + the
 *                                    context object every time
 */
import { createContext, useContext, useState, useCallback } from "react";
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
    };
    localStorage.setItem("autorisk_user", JSON.stringify(loggedInUser));
    setUser(loggedInUser); // <-- this triggers a re-render of everything
    // that reads `user` from context, e.g. the sidebar and route guards.
    return loggedInUser;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("autorisk_token");
    localStorage.removeItem("autorisk_user");
    setUser(null);
  }, []);

  // The `value` object is what every consumer of useAuth() receives.
  const value = { user, login, logout, isAuthenticated: !!user };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// Custom hook: components call useAuth() instead of useContext(AuthContext).
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
