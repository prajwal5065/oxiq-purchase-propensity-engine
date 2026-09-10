/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          900: "#0A0E17",
          800: "#10141F",
          700: "#161B29",
          600: "#232A3B",
          500: "#313A4F",
        },
        paper: {
          DEFAULT: "#F5F6F8",
          dim: "#A8AFBD",
          faint: "#6C7486",
        },
        signal: {
          DEFAULT: "#00D9A4",
          dim: "#00A67D",
          glow: "#6BE8CC",
        },
        amber: {
          DEFAULT: "#F5A623",
          dim: "#8A5C12",
        },
        rose: {
          DEFAULT: "#FF5C72",
          dim: "#8A2036",
        },
      },
      fontFamily: {
        display: ["Inter", "system-ui", "sans-serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["'Geist Mono'", "ui-monospace", "monospace"],
      },
      borderRadius: {
        sm: "12px",
      },
      backgroundImage: {
        "grid-fade":
          "radial-gradient(circle at 50% 50%, rgba(0,217,164,0.08) 0%, rgba(0,217,164,0) 70%)",
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
