import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "@/auth/AuthContext";

function ProtectedRoute() {
  const { authenticated, initialized } = useAuth();

  if (!initialized) {
    return <div>Loading...</div>; // keycloak.init() still in flight — don't redirect yet
  }

  if (!authenticated) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}

export default ProtectedRoute;
