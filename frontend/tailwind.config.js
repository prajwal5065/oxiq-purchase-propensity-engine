/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          900: "#FAFAF8",
          800: "#FFFFFF",
          700: "#F1F1EE",
          600: "#E4E2DC",
          500: "#D3D0C8",
        },
        paper: {
          DEFAULT: "#17181C",
          dim: "#55585F",
          faint: "#8A8D93",
        },
        signal: {
          DEFAULT: "#00C9A7",
          dim: "#0EA88C",
          glow: "#00A88C",
        },
        amber: {
          DEFAULT: "#B45309",
          dim: "#7C4A0A",
        },
        rose: {
          DEFAULT: "#C81E3A",
          dim: "#7A1228",
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
          "radial-gradient(circle at 50% 50%, rgba(0,201,167,0.06) 0%, rgba(0,201,167,0) 70%)",
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
