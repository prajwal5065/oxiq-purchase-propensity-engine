/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          900: "#0F1216",
          800: "#161B21",
          700: "#1D242C",
          600: "#2A323C",
          500: "#3A4450",
        },
        paper: {
          DEFAULT: "#E7E4DC",
          dim: "#9AA2AC",
          faint: "#5C6570",
        },
        signal: {
          DEFAULT: "#3ED6C4",
          dim: "#237A70",
          glow: "#9FF0E6",
        },
        amber: {
          DEFAULT: "#F0A83B",
          dim: "#8A5F1F",
        },
        rose: {
          DEFAULT: "#E4636F",
          dim: "#7A2E35",
        },
      },
      fontFamily: {
        display: ["'Source Serif 4'", "Georgia", "serif"],
        sans: ["'IBM Plex Sans'", "system-ui", "sans-serif"],
        mono: ["'IBM Plex Mono'", "ui-monospace", "monospace"],
      },
      backgroundImage: {
        "grid-fade":
          "radial-gradient(circle at 50% 50%, rgba(62,214,196,0.08) 0%, rgba(62,214,196,0) 70%)",
      },
      keyframes: {
        sweep: {
          "0%": { transform: "rotate(0deg)" },
          "100%": { transform: "rotate(360deg)" },
        },
        "pulse-glow": {
          "0%, 100%": { opacity: "0.55" },
          "50%": { opacity: "1" },
        },
      },
      animation: {
        sweep: "sweep 4s linear infinite",
        "pulse-glow": "pulse-glow 2.4s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
