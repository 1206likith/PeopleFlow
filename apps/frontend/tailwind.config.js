/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Deep space background layers
        void:    "#060812",
        abyss:   "#09101e",
        deep:    "#0d1628",
        surface: "#111927",
        // Glass surfaces (used via rgba in CSS)
        glass:   "#1a2540",
        // Accent palette
        violet:  "#a855f7",
        sky:     "#38bdf8",
        emerald: "#34d399",
        rose:    "#f87171",
        amber:   "#fbbf24",
        // Text
        snow:    "#f0f4ff",
        mist:    "#a8b8cc",
        fog:     "#5a6f85",
        // Legacy aliases kept for backward-compat with untouched components
        ink:     "#09101e",
        steel:   "#1a2540",
        slate:   "#5a6f85",
        cyan:    "#38bdf8",
      },
      fontFamily: {
        heading: ["var(--font-heading)", "sans-serif"],
        body:    ["var(--font-body)", "sans-serif"],
        mono:    ["var(--font-mono)", "monospace"],
      },
      boxShadow: {
        panel:  "0 8px 32px rgba(0, 0, 0, 0.5)",
        glow:   "0 0 24px rgba(168, 85, 247, 0.25)",
        "glow-sky": "0 0 24px rgba(56, 189, 248, 0.2)",
        "glow-sm": "0 0 12px rgba(168, 85, 247, 0.18)",
        card:   "0 4px 24px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255,255,255,0.06)",
        "inner-glow": "inset 0 0 40px rgba(168, 85, 247, 0.06)",
      },
      backdropBlur: {
        glass: "16px",
        "glass-sm": "8px",
      },
      backgroundImage: {
        "gradient-mesh": "radial-gradient(ellipse at 15% 0%, #280d4a 0%, #06102a 45%, #060812 100%)",
        "gradient-card": "linear-gradient(135deg, rgba(255,255,255,0.07) 0%, rgba(255,255,255,0.02) 100%)",
        "gradient-violet": "linear-gradient(135deg, #7c3aed 0%, #a855f7 100%)",
        "gradient-sky": "linear-gradient(135deg, #0ea5e9 0%, #38bdf8 100%)",
        "gradient-hero": "linear-gradient(135deg, rgba(124,58,237,0.3) 0%, rgba(56,189,248,0.15) 50%, rgba(6,8,18,0) 100%)",
      },
      animation: {
        "fade-rise":    "fadeRise 350ms cubic-bezier(0.16, 1, 0.3, 1)",
        "fade-rise-sm": "fadeRiseSm 280ms cubic-bezier(0.16, 1, 0.3, 1)",
        "fade-in":      "fadeIn 250ms ease-out",
        "fade-in-sm":   "fadeInSm 180ms ease-out",
        "slide-in":     "slideIn 300ms cubic-bezier(0.16, 1, 0.3, 1)",
        "slide-in-left":   "slideInLeft 320ms cubic-bezier(0.16, 1, 0.3, 1)",
        "slide-in-right":  "slideInRight 320ms cubic-bezier(0.16, 1, 0.3, 1)",
        "slide-in-top":    "slideInTop 300ms cubic-bezier(0.16, 1, 0.3, 1)",
        "slide-in-down":   "slideInDown 300ms cubic-bezier(0.16, 1, 0.3, 1)",
        "mesh-drift":   "meshDrift 25s ease-in-out infinite alternate",
        "orb-float-1":  "orbFloat1 18s ease-in-out infinite",
        "orb-float-2":  "orbFloat2 22s ease-in-out infinite",
        "orb-float-3":  "orbFloat3 28s ease-in-out infinite",
        "pulse-glow":   "pulseGlow 2.5s ease-in-out infinite",
        "pulse-glow-sm": "pulseGlowSm 1.8s ease-in-out infinite",
        shimmer:        "shimmer 1.8s ease-in-out infinite",
        "shimmer-fast": "shimmerFast 1.2s ease-in-out infinite",
        "spin-slow":    "spin 8s linear infinite",
        "bounce-lg":    "bounceLg 2s ease-in-out infinite",
        "float-bounce": "floatBounce 2.4s ease-in-out infinite",
        "glow-pulse":   "glowPulse 3s ease-in-out infinite",
        "scale-pulse":  "scalePulse 2s ease-in-out infinite",
        "rotate-slow":  "rotateSlow 20s linear infinite",
        "accordion-open": "accordionOpen 300ms cubic-bezier(0.16, 1, 0.3, 1)",
        "accordion-close": "accordionClose 250ms ease-in",
      },
      keyframes: {
        fadeRise: {
          "0%":   { opacity: "0", transform: "scale(0.97) translateY(12px)" },
          "100%": { opacity: "1", transform: "scale(1) translateY(0)" },
        },
        fadeRiseSm: {
          "0%":   { opacity: "0", transform: "scale(0.98) translateY(6px)" },
          "100%": { opacity: "1", transform: "scale(1) translateY(0)" },
        },
        fadeIn: {
          "0%":   { opacity: "0" },
          "100%": { opacity: "1" },
        },
        fadeInSm: {
          "0%":   { opacity: "0" },
          "50%":  { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideIn: {
          "0%":   { opacity: "0", transform: "translateX(-16px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        slideInLeft: {
          "0%":   { opacity: "0", transform: "translateX(-24px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        slideInRight: {
          "0%":   { opacity: "0", transform: "translateX(24px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        slideInTop: {
          "0%":   { opacity: "0", transform: "translateY(-20px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        slideInDown: {
          "0%":   { opacity: "0", transform: "translateY(20px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        meshDrift: {
          "0%":   { backgroundPosition: "0% 0%" },
          "100%": { backgroundPosition: "100% 100%" },
        },
        orbFloat1: {
          "0%, 100%": { transform: "translate(0, 0) scale(1)" },
          "33%":      { transform: "translate(40px, -30px) scale(1.05)" },
          "66%":      { transform: "translate(-20px, 20px) scale(0.97)" },
        },
        orbFloat2: {
          "0%, 100%": { transform: "translate(0, 0) scale(1)" },
          "50%":      { transform: "translate(-50px, 40px) scale(1.08)" },
        },
        orbFloat3: {
          "0%, 100%": { transform: "translate(0, 0)" },
          "40%":      { transform: "translate(30px, -50px)" },
          "80%":      { transform: "translate(-40px, 20px)" },
        },
        pulseGlow: {
          "0%, 100%": { boxShadow: "0 0 12px rgba(45, 212, 191, 0.2)" },
          "50%":      { boxShadow: "0 0 28px rgba(45, 212, 191, 0.5)" },
        },
        pulseGlowSm: {
          "0%, 100%": { boxShadow: "0 0 8px rgba(45, 212, 191, 0.15)" },
          "50%":      { boxShadow: "0 0 16px rgba(45, 212, 191, 0.35)" },
        },
        shimmer: {
          "0%":   { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        shimmerFast: {
          "0%":   { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        bounceLg: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%":      { transform: "translateY(-8px)" },
        },
        floatBounce: {
          "0%, 100%": { transform: "translateY(0) translateX(0)" },
          "25%":      { transform: "translateY(-8px) translateX(2px)" },
          "50%":      { transform: "translateY(0) translateX(0)" },
          "75%":      { transform: "translateY(-4px) translateX(-2px)" },
        },
        glowPulse: {
          "0%, 100%": { opacity: "0.6" },
          "50%":      { opacity: "1" },
        },
        scalePulse: {
          "0%, 100%": { transform: "scale(1)" },
          "50%":      { transform: "scale(1.02)" },
        },
        rotateSlow: {
          "0%":   { transform: "rotate(0deg)" },
          "100%": { transform: "rotate(360deg)" },
        },
        accordionOpen: {
          "0%":   { opacity: "0", maxHeight: "0" },
          "100%": { opacity: "1", maxHeight: "500px" },
        },
        accordionClose: {
          "0%":   { opacity: "1", maxHeight: "500px" },
          "100%": { opacity: "0", maxHeight: "0" },
        },
        shake: {
          "0%, 100%": { transform: "translateX(0)" },
          "10%, 30%, 50%, 70%, 90%": { transform: "translateX(-4px)" },
          "20%, 40%, 60%, 80%": { transform: "translateX(4px)" },
        },
      },
      borderRadius: {
        "2xl": "1rem",
        "3xl": "1.25rem",
        "4xl": "1.5rem",
      },
    },
  },
  plugins: [],
};
