import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./components/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        ink: "#14251f",
        moss: "#315b43",
        paper: "#f7f8f3",
        lime: "#c5e1a5",
      },
    },
  },
  plugins: [],
};

export default config;
