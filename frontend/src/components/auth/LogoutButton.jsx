import { useAuth } from "@/auth/AuthContext";
function LogoutButton() {
  const { logout } = useAuth();

  return (
    <button onClick={logout}>
      Logout
    </button>
  );
}

export default LogoutButton;