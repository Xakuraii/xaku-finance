import React, { useEffect, useState } from "react";
import { Sun, Moon, Laptop } from "lucide-react";

export type ThemeMode = "light" | "dark" | "system";

interface ThemeToggleProps {
  value?: ThemeMode;
  onChange?: (theme: ThemeMode) => void;
  className?: string;
}

export const ThemeToggle: React.FC<ThemeToggleProps> = ({
  value,
  onChange,
  className = "",
}) => {
  const [selected, setSelected] = useState<ThemeMode>(() => {
    if (value) return value;
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("theme") as ThemeMode | null;
      if (stored && ["light", "dark", "system"].includes(stored)) return stored;
    }
    return "system";
  });

  useEffect(() => {
    if (value && value !== selected) {
      setSelected(value);
    }
  }, [value, selected]);

  const applyTheme = (theme: ThemeMode) => {
    const root = document.documentElement;
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const isDark = theme === "dark" || (theme === "system" && prefersDark);

    if (isDark) {
      root.classList.add("dark");
      root.setAttribute("data-theme", "dark");
    } else {
      root.classList.remove("dark");
      root.setAttribute("data-theme", "light");
    }
  };

  const handleSelect = (theme: ThemeMode) => {
    setSelected(theme);
    localStorage.setItem("theme", theme);
    applyTheme(theme);
    onChange?.(theme);
  };

  return (
    <div
      role="radiogroup"
      aria-label="Theme selection"
      className={`inline-flex items-center p-1 rounded-xl bg-muted/60 border border-border ${className}`}
    >
      <button
        type="button"
        role="radio"
        aria-checked={selected === "light"}
        onClick={() => handleSelect("light")}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer ${
          selected === "light"
            ? "bg-card text-foreground shadow-xs border border-border"
            : "text-muted-foreground hover:text-foreground"
        }`}
      >
        <Sun className="w-3.5 h-3.5" />
        <span>Light</span>
      </button>

      <button
        type="button"
        role="radio"
        aria-checked={selected === "dark"}
        onClick={() => handleSelect("dark")}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer ${
          selected === "dark"
            ? "bg-card text-foreground shadow-xs border border-border"
            : "text-muted-foreground hover:text-foreground"
        }`}
      >
        <Moon className="w-3.5 h-3.5" />
        <span>Dark</span>
      </button>

      <button
        type="button"
        role="radio"
        aria-checked={selected === "system"}
        onClick={() => handleSelect("system")}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer ${
          selected === "system"
            ? "bg-card text-foreground shadow-xs border border-border"
            : "text-muted-foreground hover:text-foreground"
        }`}
      >
        <Laptop className="w-3.5 h-3.5" />
        <span>System</span>
      </button>
    </div>
  );
};
