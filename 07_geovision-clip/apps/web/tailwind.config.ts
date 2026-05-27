import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        "surface-1": "var(--surface-1)",
        "surface-2": "var(--surface-2)",
        "border-subtle": "var(--border-subtle)",
        "border-strong": "var(--border-strong)",
        muted: "var(--muted)",
        "muted-foreground": "var(--muted-foreground)",
        accent: "var(--accent)",
        "accent-foreground": "var(--accent-foreground)",
        success: "var(--success)",
        warning: "var(--warning)",
        danger: "var(--danger)",
        info: "var(--info)",
      },
      fontFamily: {
        sans: ["var(--font-geist-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["var(--font-geist-mono)", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      borderRadius: {
        base: "6px",
        md: "8px",
        lg: "12px",
      },
      boxShadow: {
        "elevation-1": "0 1px 2px rgba(0, 0, 0, 0.04)",
        "elevation-2": "0 2px 8px rgba(0, 0, 0, 0.06)",
        "elevation-3": "0 8px 24px rgba(0, 0, 0, 0.08)",
      },
      transitionTimingFunction: {
        "out-soft": "cubic-bezier(0, 0, 0.2, 1)",
        "in-soft": "cubic-bezier(0.4, 0, 1, 1)",
      },
      keyframes: {
        "fade-in": {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        "fade-out": {
          from: { opacity: "1" },
          to: { opacity: "0" },
        },
        "zoom-in": {
          from: { transform: "scale(0.95)", opacity: "0" },
          to: { transform: "scale(1)", opacity: "1" },
        },
        "zoom-out": {
          from: { transform: "scale(1)", opacity: "1" },
          to: { transform: "scale(0.95)", opacity: "0" },
        },
      },
      animation: {
        "fade-in-0": "fade-in 150ms cubic-bezier(0, 0, 0.2, 1)",
        "fade-out-0": "fade-out 100ms cubic-bezier(0.4, 0, 1, 1)",
        "zoom-in-95": "zoom-in 150ms cubic-bezier(0, 0, 0.2, 1)",
        "zoom-out-95": "zoom-out 100ms cubic-bezier(0.4, 0, 1, 1)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
