import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ['"Space Grotesk"', "ui-sans-serif", "system-ui"],
        mono: ['"JetBrains Mono"', "ui-monospace", "SFMono-Regular"],
      },
      colors: {
        ink: "#0b0b10",
        panel: "#11121a",
        edge: "#1d1f2c",
        muted: "#7a7d92",
        accent: "#c4ff3e",
        accent2: "#7a5cff",
        danger: "#ff5a78",
        warn: "#ffb13a",
        ok: "#3aff9d",
      },
      keyframes: {
        pulseDot: {
          "0%,100%": { opacity: "1" },
          "50%": { opacity: "0.35" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        pulseDot: "pulseDot 1.2s ease-in-out infinite",
        slideUp: "slideUp 220ms ease-out",
      },
    },
  },
  plugins: [],
};

export default config;
