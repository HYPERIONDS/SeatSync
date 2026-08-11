/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#07130f",
        panel: "#10231b",
        mint: "#7fffc4",
        coral: "#ff8b72",
        cream: "#f1f5e9"
      },
      fontFamily: { sans: ["Inter", "ui-sans-serif", "system-ui"], display: ["Georgia", "serif"] }
    }
  },
  plugins: []
};
