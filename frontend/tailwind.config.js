/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Rojo institucional tomado del escudo de la DUBSS.
        brand: {
          50:  "#fef2f2",
          100: "#fee2e2",
          200: "#fecaca",
          300: "#fca5a5",
          400: "#f26b6e",
          500: "#e03a3d",
          600: "#d21115",
          700: "#ac0e11",
          800: "#8a0c0f",
          900: "#6b0a0c",
        },
        // Neutros fríos para texto, superficies y barra lateral.
        ink: {
          50:  "#f6f7f9",
          100: "#eceef2",
          200: "#dde0e7",
          300: "#c3c8d3",
          400: "#9199a9",
          500: "#6b7385",
          600: "#4d5465",
          700: "#363c4b",
          800: "#242834",
          900: "#171a23",
          950: "#0f1117",
        },
      },
      fontFamily: {
        sans:    ["var(--font-inter)", "system-ui", "sans-serif"],
        display: ["var(--font-inter)", "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(23,26,35,0.04), 0 1px 3px rgba(23,26,35,0.06)",
        pop:  "0 10px 30px -8px rgba(23,26,35,0.25)",
      },
      keyframes: {
        "fade-in":  { from: { opacity: "0" }, to: { opacity: "1" } },
        "slide-up": { from: { opacity: "0", transform: "translateY(8px)" }, to: { opacity: "1", transform: "translateY(0)" } },
        "sheet-up": { from: { transform: "translateY(100%)" }, to: { transform: "translateY(0)" } },
        "float-slow": { "0%, 100%": { transform: "translateY(0) scale(1)" }, "50%": { transform: "translateY(-18px) scale(1.04)" } },
        "pulse-ring": { "0%": { boxShadow: "0 0 0 0 rgba(255,255,255,0.45)" }, "100%": { boxShadow: "0 0 0 18px rgba(255,255,255,0)" } },
        "pop": { "0%": { transform: "scale(0.9)", opacity: "0" }, "60%": { transform: "scale(1.04)" }, "100%": { transform: "scale(1)", opacity: "1" } },
      },
      animation: {
        "fade-in":  "fade-in 0.15s ease-out",
        "slide-up": "slide-up 0.2s ease-out",
        "sheet-up": "sheet-up 0.25s cubic-bezier(0.16, 1, 0.3, 1)",
        "float-slow": "float-slow 9s ease-in-out infinite",
        "pulse-ring": "pulse-ring 2.4s ease-out infinite",
        "pop": "pop 0.28s ease-out",
      },
    },
  },
  plugins: [],
};
