import { Link, NavLink, Outlet } from "react-router-dom";
import { useAuth } from "@/auth/AuthContext";
import { Button } from "@/components/ui/button";

const navLinkClasses = ({ isActive }) =>
  `px-3 py-2 text-sm font-medium rounded-md transition-colors ${
    isActive
      ? "bg-gray-900 text-white"
      : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
  }`;

function AppShell() {
  const { authenticated, initialized, login, logout } = useAuth();

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
          <Link to="/dashboard" className="text-lg font-bold text-gray-900">
            Insurance App
          </Link>
          <div className="flex items-center gap-3">
            <nav className="flex items-center gap-1">
              <NavLink to="/dashboard" className={navLinkClasses}>
                Dashboard
              </NavLink>
              <NavLink to="/claims" className={navLinkClasses}>
                Claims
              </NavLink>
              <NavLink to="/patients" className={navLinkClasses}>
                Patients
              </NavLink>
            </nav>

            {!initialized && (
              <span className="text-sm text-gray-500">Checking auth...</span>
            )}

            {initialized && !authenticated && (
              <Button type="button" size="sm" onClick={login}>
                Login
              </Button>
            )}

            {initialized && authenticated && (
              <Button type="button" variant="outline" size="sm" onClick={logout}>
                Logout
              </Button>
            )}
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">
        <Outlet />
      </main>
    </div>
  );
}
export default AppShell;
