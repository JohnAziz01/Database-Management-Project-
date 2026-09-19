/**
 * LESSON: a "route guard" component.
 *
 * This wraps protected routes. If there's no logged-in user, <Navigate>
 * redirects to /login instead of rendering children. `replace` means it
 * swaps the current history entry instead of adding a new one, so the
 * back button doesn't bounce the user back into the protected page.
 */
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function RequireAuth() {
  const { isAuthenticated } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  return <Outlet />;
}
