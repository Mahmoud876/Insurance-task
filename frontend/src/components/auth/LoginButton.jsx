import { useAuth } from "@/auth/AuthContext";
function LoginButton() {
  const { login, initialized } = useAuth();

  return (
    <button
      type="button"
      onClick={login}
      disabled={!initialized}
      className="flex w-full items-center justify-center rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-600/20 hover:bg-indigo-700 focus:outline-none focus:ring-4 focus:ring-indigo-200 disabled:cursor-wait disabled:opacity-60"
    >
      {initialized ? "Continue with secure sign-in" : "Preparing secure sign-in…"}
    </button>
  );
}

export default LoginButton;
