/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./pages/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#4B7BEC",
          dark: "#274690",
          light: "#A3C4F3"
        }
      }
    }
  },
  plugins: [require("@tailwindcss/typography")]
};
