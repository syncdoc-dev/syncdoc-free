import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { getApiBase } from "../api/client";
import type { Entitlements, User } from "../types";

interface AuthContextType {
  user: User | null;
  token: string | null;
  entitlements: Entitlements | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  logout: () => void;
  setToken: (token: string) => void;
  refreshEntitlements: () => Promise<void>;
  hasFeature: (feature: string) => boolean;
  getLimit: (limitName: string) => number | null;
}

const AuthContext = createContext<AuthContextType | null>(null);

const TOKEN_KEY = "syncdoc_token";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(() =>
    localStorage.getItem(TOKEN_KEY)
  );
  const [user, setUser] = useState<User | null>(null);
  const [entitlements, setEntitlements] = useState<Entitlements | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const setToken = (newToken: string) => {
    localStorage.setItem(TOKEN_KEY, newToken);
    setTokenState(newToken);
  };

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY);
    setTokenState(null);
    setUser(null);
    setEntitlements(null);
  };

  const refreshEntitlements = useCallback(async () => {
    if (!token) {
      setEntitlements(null);
      return;
    }

    try {
      const response = await fetch(`${getApiBase()}/license/entitlements`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        setEntitlements(null);
        return;
      }
      const data = (await response.json()) as Entitlements;
      setEntitlements(data);
    } catch {
      setEntitlements(null);
    }
  }, [token]);

  const hasFeature = useCallback(
    (feature: string) => Boolean(entitlements?.features.includes(feature)),
    [entitlements]
  );

  const getLimit = useCallback(
    (limitName: string) => entitlements?.limits[limitName] ?? null,
    [entitlements]
  );

  useEffect(() => {
    if (!token) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setEntitlements(null);
      setIsLoading(false);
      return;
    }

    fetch(`${getApiBase()}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => {
        if (!r.ok) {
          logout();
          return null;
        }
        return r.json();
      })
      .then(async (data) => {
        if (data) {
          setUser(data);
          await refreshEntitlements();
        }
      })
      .finally(() => setIsLoading(false));
  }, [token, refreshEntitlements]);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        entitlements,
        isLoading,
        isAuthenticated: !!token,
        logout,
        setToken,
        refreshEntitlements,
        hasFeature,
        getLimit,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
