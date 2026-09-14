import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "@/auth/AuthContext";

function PublicRoute() {
  const { authenticated, initialized } = useAuth();

  if (!initialized) {
    return <div className="flex h-screen items-center justify-center">Loading...</div>;
  }

  if (authenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return <Outlet />;
}

export default PublicRoute;
