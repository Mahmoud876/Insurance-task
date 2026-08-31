import { useEffect, useRef, useState } from "react";
import { AuthContext } from "./AuthContext";
import keycloak from "./keycloak";

function AuthProvider({ children }) {
  const [authenticated, setAuthenticated] = useState(false);
  const [initialized, setInitialized] = useState(false);
  const initRun = useRef(false);
  const [accessToken, setAccessToken] = useState(null);

  useEffect(() => {
    if (initRun.current) return;
    initRun.current = true;

    keycloak
      .init({ onLoad: "check-sso", pkceMethod: "S256" })
      .then((auth) => {
        setAuthenticated(auth);
        setInitialized(true);
        setAccessToken(keycloak.token);
      })
      .catch((err) => {
        console.error("Keycloak init failed", err);

        // DEV-ONLY BYPASS: if a dev token is provided via env var, use it
        // instead of real Keycloak login. Remove once real auth is set up.
        const devToken = import.meta.env.VITE_DEV_AUTH_TOKEN;
        if (devToken) {
          console.warn(
            "AuthProvider: using VITE_DEV_AUTH_TOKEN dev bypass — not for production"
          );
          setAccessToken(devToken);
          setAuthenticated(true);
        }

        setInitialized(true);
      });
  }, []);

  function login() {
    keycloak.login({ redirectUri: window.location.origin + "/dashboard" });
  }
  function logout() {
    keycloak.logout();
  }

  return (
    <AuthContext.Provider value={{ authenticated, initialized, accessToken, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
export default AuthProvider;
