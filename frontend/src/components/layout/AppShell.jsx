import { Link, Outlet } from "react-router-dom";

function AppShell() {
  return (
    <div>
      <h1>Insurance App</h1>

      <nav>
        <Link to="/dashboard">Dashboard</Link>
        <Link to="/claims">Claims</Link>
        <Link to="/patients">Patients</Link>
      </nav>

      <Outlet />
    </div>

  );
}

export default AppShell;