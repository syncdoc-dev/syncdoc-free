import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import { updateMe } from "../api/client";
import { useAuth } from "./AuthContext";

export type ThemeId =
  | "original"
  | "original_light"
  | "catppuccin"
  | "tokyonight"
  | "dracula"
  | "nord"
  | "gruvbox";

export interface ThemeMeta {
  id: ThemeId;
  label: string;
  swatch: string;
}

export const THEMES: ThemeMeta[] = [
  { id: "original", label: "Original", swatch: "#34d1e8" },
  { id: "original_light", label: "Original Light", swatch: "#149a73" },
  { id: "catppuccin", label: "Catppuccin Mocha", swatch: "#cba6f7" },
  { id: "tokyonight", label: "Tokyo Night", swatch: "#7aa2f7" },
  { id: "dracula", label: "Dracula", swatch: "#bd93f9" },
  { id: "nord", label: "Nord", swatch: "#88c0d0" },
  { id: "gruvbox", label: "Gruvbox Dark", swatch: "#fe8019" },
];

const FREE_THEME_IDS: ThemeId[] = ["original", "original_light"];

interface ThemeContextValue {
  theme: ThemeId;
  setTheme: (id: ThemeId) => void;
  availableThemes: ThemeMeta[];
  isThemeLocked: (id: ThemeId) => boolean;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

const STORAGE_KEY_PREFIX = "syncdoc-theme";

function isValidTheme(value: string | null | undefined): value is ThemeId {
  return Boolean(value && THEMES.some((themeMeta) => themeMeta.id === value));
}

function getStorageKey(userId: string | number | null | undefined) {
  return `${STORAGE_KEY_PREFIX}:${userId ?? "anonymous"}`;
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const { user, token, entitlements } = useAuth();
  const storageKey = getStorageKey(user?.id);
  const [theme, setThemeState] = useState<ThemeId>("original");
  const entitlementsLoaded = entitlements !== null;
  const isFreePlan = entitlementsLoaded && entitlements.plan === "free";
  const availableThemes = isFreePlan
    ? THEMES.filter((themeMeta) => FREE_THEME_IDS.includes(themeMeta.id))
    : THEMES;

  const isThemeLocked = (id: ThemeId) =>
    isFreePlan && !FREE_THEME_IDS.includes(id);

  const setTheme = useCallback((id: ThemeId) => {
    if (isThemeLocked(id)) {
      id = "original";
    }
    setThemeState(id);
    localStorage.setItem(storageKey, id);
    if (token) {
      updateMe({ theme_id: id }).catch(() => {
        // Ignore transient failures; local storage keeps the preference.
      });
    }
  }, [storageKey, token, isThemeLocked]);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  useEffect(() => {
    if (!entitlementsLoaded) return;
    if (isThemeLocked(theme)) {
      setThemeState("original");
      localStorage.setItem(storageKey, "original");
      if (token) {
        updateMe({ theme_id: "original" }).catch(() => {});
      }
    }
  }, [entitlementsLoaded, isFreePlan, storageKey, theme, token]);

  useEffect(() => {
    if (isValidTheme(user?.theme_id)) {
      setThemeState(user.theme_id);
      localStorage.setItem(storageKey, user.theme_id);
      return;
    }

    const storedTheme = localStorage.getItem(storageKey);
    setThemeState(isValidTheme(storedTheme) ? storedTheme : "original");
  }, [storageKey, user?.theme_id]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme, availableThemes, isThemeLocked }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within ThemeProvider");
  return ctx;
}
