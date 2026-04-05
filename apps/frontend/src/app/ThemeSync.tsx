import { useEffect } from "react";
import { useSessionStore } from "@/lib/state/sessionStore";
import { useReducedMotionPreference } from "@/lib/hooks/useReducedMotionPreference";

export function ThemeSync() {
  const theme = useSessionStore((state) => state.theme);
  useReducedMotionPreference();

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme === "light" ? "aurora-light" : "aurora-research");
  }, [theme]);

  return null;
}
