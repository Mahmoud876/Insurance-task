import { Link, NavLink, Outlet } from "react-router-dom";

const navLinkClasses = ({ isActive }) =>
  `px-3 py-2 text-sm font-medium rounded-md transition-colors ${
    isActive
      ? "bg-gray-900 text-white"
      : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
  }`;

function AppShell() {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
          <Link to="/dashboard" className="text-lg font-bold text-gray-900">
            Insurance App
          </Link>
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
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">
        <Outlet />
      </main>
    </div>
  );
}
export default AppShell;
