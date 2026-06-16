import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        score: {
          low: "#ef4444",
          mid: "#f59e0b",
          high: "#22c55e",
        },
      },
    },
  },
  plugins: [],
};

export default config;
