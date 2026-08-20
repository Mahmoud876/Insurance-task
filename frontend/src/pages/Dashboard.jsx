import { useAuth } from "@/auth/AuthContext";
import LoginButton from "@/components/auth/LoginButton";
import LogoutButton from "@/components/auth/LogoutButton";
function Dashboard() {
  const { authenticated } = useAuth();
  return (
    <div>
      <h1>Dashboard</h1>
      <p>Welcome to the Insurance Dashboard.</p>

      <p>
        {authenticated ? "You are logged in." : "You are not logged in."}
      </p>
      {!authenticated && <LoginButton />}
      {authenticated && <LogoutButton />}
    </div>
  );
}

export default Dashboard;