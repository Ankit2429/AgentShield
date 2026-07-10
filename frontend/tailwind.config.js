/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html"
  ],
  theme: {
    extend: {
      colors: {
        darkBg: "#0b0f19",
        cardBg: "rgba(17, 24, 39, 0.7)",
        accentCyan: "#06b6d4",
        accentViolet: "#8b5cf6"
      }
    },
  },
  plugins: [],
}
