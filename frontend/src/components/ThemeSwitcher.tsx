import { useState, useRef, useEffect } from "react";
import { Palette } from "lucide-react";
import { THEMES, useTheme } from "../context/ThemeContext";
import UpgradeBadge from "./UpgradeBadge";

export default function ThemeSwitcher() {
  const { theme, setTheme, availableThemes, isThemeLocked } = useTheme();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="inline-flex h-10 items-center gap-2 rounded-xl border border-[var(--border)]
          bg-[var(--bg-input)]/80 px-3 text-sm text-[var(--text-secondary)]
          transition-colors hover:bg-[var(--hover-bg)] hover:text-[var(--text-primary)]"
        title="Switch theme"
      >
        <Palette className="w-4 h-4" />
        <span className="hidden sm:inline">Theme</span>
      </button>

      {open && (
        <div
          className="absolute bottom-full right-0 z-50 mb-2 w-56 rounded-2xl border
            border-[var(--border)] bg-[var(--bg-card-strong)] p-1.5 shadow-2xl"
        >
          {THEMES.map((t) => (
            <button
              key={t.id}
              onClick={() => {
                if (!isThemeLocked(t.id)) {
                  setTheme(t.id);
                  setOpen(false);
                }
              }}
              className={`flex items-center gap-3 w-full px-3 py-2 text-sm transition-colors
                ${
                  theme === t.id
                    ? "text-[var(--accent)] bg-[var(--accent-bg)]"
                    : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--hover-bg)]"
                } ${isThemeLocked(t.id) ? "opacity-70" : ""}`}
              disabled={isThemeLocked(t.id)}
            >
              <span
                className="w-3 h-3 rounded-full shrink-0 border border-white/20"
                style={{ backgroundColor: t.swatch }}
              />
              {t.label}
              {isThemeLocked(t.id) && <UpgradeBadge label="Pro" />}
              {theme === t.id && <span className="ml-auto text-xs">&#10003;</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
