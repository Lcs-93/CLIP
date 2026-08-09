"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

type Theme = "light" | "dark" | "system";
type ResolvedTheme = "light" | "dark";

interface ThemeContextValue {
  theme: Theme;
  resolvedTheme: ResolvedTheme;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

function resolveTheme(theme: Theme, prefersDark: boolean): ResolvedTheme {
  if (theme === "system") return prefersDark ? "dark" : "light";
  return theme;
}

function readStoredTheme(): Theme {
  if (typeof window === "undefined") return "light";
  const stored = window.localStorage.getItem("theme");
  if (stored === "light" || stored === "dark") return stored;
  if (stored === "system") return "light";
  return "light";
}

function getPreferredTheme(theme: Theme): ResolvedTheme {
  if (typeof window === "undefined") return "light";
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  return resolveTheme(theme, prefersDark);
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<Theme>(() => readStoredTheme());
  const [resolvedTheme, setResolvedTheme] = useState<ResolvedTheme>(() => getPreferredTheme(readStoredTheme()));

  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const applyTheme = () => {
      const nextResolved = resolveTheme(theme, media.matches);
      setResolvedTheme((current) => (current === nextResolved ? current : nextResolved));
      document.documentElement.classList.toggle("dark", nextResolved === "dark");
      document.documentElement.dataset.theme = nextResolved;
    };

    applyTheme();
    const listener = () => {
      if (theme === "system") applyTheme();
    };
    media.addEventListener("change", listener);
    return () => media.removeEventListener("change", listener);
  }, [theme]);

  useEffect(() => {
    localStorage.setItem("theme", theme);
  }, [theme]);

  const value = useMemo(
    () => ({
      theme,
      resolvedTheme,
      setTheme,
      toggleTheme: () =>
        setTheme((current) => {
          const active = current === "system" ? resolvedTheme : current;
          return active === "dark" ? "light" : "dark";
        }),
    }),
    [theme, resolvedTheme]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within ThemeProvider");
  }
  return context;
}
