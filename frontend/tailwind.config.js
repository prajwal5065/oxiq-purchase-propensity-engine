/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          900: "#000000",
          800: "#17181C",
          700: "#202226",
          600: "#2B2D31",
          500: "#3A3D42",
        },
        paper: {
          DEFAULT: "#FFFFFF",
          dim: "#B2B6BD",
          faint: "#656A76",
        },
        signal: {
          DEFAULT: "#17E7C4",
          dim: "#0FA88F",
          glow: "#74F5DE",
        },
        amber: {
          DEFAULT: "#E8B92E",
          dim: "#8A6A0E",
        },
        rose: {
          DEFAULT: "#E0483E",
          dim: "#7A241F",
        },
      },
      fontFamily: {
        display: ["Inter", "system-ui", "sans-serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["'Geist Mono'", "ui-monospace", "monospace"],
      },
      borderRadius: {
        sm: "12px",
        md: "8px",
      },
      backgroundImage: {
        "grid-fade":
          "radial-gradient(circle at 50% 50%, rgba(23,231,196,0.06) 0%, rgba(23,231,196,0) 70%)",
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
