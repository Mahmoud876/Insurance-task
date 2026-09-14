import { useCallback, useEffect, useRef, useState } from "react";
import { AuthContext } from "./AuthContext";

const AUTH_API_BASE_URL = (import.meta.env.VITE_AUTH_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");

function AuthProvider({ children }) {
  const [authenticated, setAuthenticated] = useState(false);
  const [initialized, setInitialized] = useState(false);
  const initRun = useRef(false);
  const [accessToken, setAccessToken] = useState(null);
  const refreshTimerRef = useRef(null);
  const refreshAccessTokenRef = useRef(null);

  const clearRefreshTimer = useCallback(() => {
    if (refreshTimerRef.current) {
      window.clearTimeout(refreshTimerRef.current);
      refreshTimerRef.current = null;
    }
  }, []);

  const scheduleRefresh = useCallback((expiresInSeconds) => {
    clearRefreshTimer();
    if (typeof expiresInSeconds !== "number" || expiresInSeconds <= 30) {
      return;
    }
    const refreshInMs = Math.max((expiresInSeconds - 30) * 1000, 1_000);
    refreshTimerRef.current = window.setTimeout(() => {
      if (!refreshAccessTokenRef.current) {
        return;
      }
      refreshAccessTokenRef.current().catch((error) => {
        console.error("Scheduled token refresh failed", error);
      });
    }, refreshInMs);
  }, [clearRefreshTimer]);

  const refreshAccessToken = useCallback(async () => {
    try {
      const response = await fetch(`${AUTH_API_BASE_URL}/auth/refresh`, {
        method: "POST",
        credentials: "include",
      });

      if (response.status === 401) {
        setAccessToken(null);
        setAuthenticated(false);
        return null;
      }
      if (!response.ok) {
        throw new Error(`Refresh failed with status ${response.status}`);
      }

      const payload = await response.json();
      setAccessToken(payload.access_token);
      setAuthenticated(true);
      scheduleRefresh(payload.expires_in);
      return payload.access_token;
    } catch (error) {
      setAccessToken(null);
      setAuthenticated(false);
      return null;
    }
  }, [scheduleRefresh]);

  useEffect(() => {
    refreshAccessTokenRef.current = refreshAccessToken;
  }, [refreshAccessToken]);

  useEffect(() => {
    if (initRun.current) return;
    initRun.current = true;

    console.log("[AuthProvider] Initializing authentication...");
    refreshAccessToken()
      .then((token) => {
        if (token) {
          console.log("[AuthProvider] Authentication successful. Token received.");
        } else {
          console.log("[AuthProvider] Authentication check returned no token (User not signed in).");
        }
      })
      .catch((err) => {
        console.error("[AuthProvider] Initial refresh failed:", err);
        setAccessToken(null);
        setAuthenticated(false);
      })
      .finally(() => {
        console.log("[AuthProvider] Initialization complete.");
        setInitialized(true);
      });

    return () => {
      clearRefreshTimer();
    };
  }, [clearRefreshTimer, refreshAccessToken]);

  function login() {
    console.log("Login button clicked. Redirecting to:", `${AUTH_API_BASE_URL}/auth/login`);
    window.location.assign(`${AUTH_API_BASE_URL}/auth/login`);
  }

  async function logout() {
    const response = await fetch(`${AUTH_API_BASE_URL}/auth/logout`, {
      method: "POST",
      credentials: "include",
    });
    if (!response.ok) {
      throw new Error(`Logout failed with status ${response.status}`);
    }

    clearRefreshTimer();
    setAccessToken(null);
    setAuthenticated(false);
    window.location.assign("/login");
  }

  return (
    <AuthContext.Provider
      value={{
        authenticated,
        initialized,
        accessToken,
        login,
        logout,
        refreshAccessToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
export default AuthProvider;
