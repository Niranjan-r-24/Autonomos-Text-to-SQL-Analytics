/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        clay: {
          50: "#F9FAFB",
          100: "#F3F4F6", // Primary Light Clay Background
          150: "#ECEEF2",
          200: "#E2E5EB",
          300: "#CBD1DC",
          400: "#9CA3AF",
          900: "#111827", // Dark Graphite Pills
        },
        lime: {
          300: "#BEF264",
          400: "#A3E635", // Signature Lime Neon Accent
          500: "#84CC16",
          600: "#65A30D",
        }
      },
      borderRadius: {
        '3xl': '1.5rem',
        '4xl': '2rem',
      },
      boxShadow: {
        'clay-card': '0 10px 30px -5px rgba(0, 0, 0, 0.04), 0 4px 12px -2px rgba(0, 0, 0, 0.02)',
        'pill-dark': '0 4px 14px 0 rgba(0, 0, 0, 0.25)',
        'lime-glow': '0 4px 20px -2px rgba(163, 230, 53, 0.5)',
      }
    },
  },
  plugins: [],
};
