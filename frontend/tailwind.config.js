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
        forest: {
          950: "#08160E",
          900: "#0E2418", // Dark forest green sidebar
          850: "#132E20",
          800: "#1B3B2B",
          700: "#244E39",
          600: "#2F654B",
          500: "#3D8260",
        },
        sage: {
          50: "#F4F7F5",
          100: "#E5ECE7",
          200: "#CCDAD0",
          300: "#A8C0B0",
          400: "#7CA289",
          500: "#578568", // Subtle sage green accent
          600: "#436C52",
          700: "#365642",
          800: "#2D4536",
          900: "#263B2F",
        },
        warm: {
          50: "#FBFBFA",
          100: "#F7F6F3",
          200: "#EFECE6",
          300: "#E3DFD5",
          400: "#D1CBBF",
          500: "#A8A193",
        },
        emerald: {
          50: "#ECFDF5",
          100: "#D1FAE5",
          200: "#A7F3D0",
          300: "#6EE7B7",
          400: "#34D399",
          500: "#10B981",
          600: "#059669",
          700: "#047857",
          800: "#065F46",
          900: "#064E3B",
        },
        slate: {
          50: "#F8FAFC",
          100: "#F1F5F9",
          200: "#E2E8F0",
          300: "#CBD5E1",
          400: "#94A3B8",
          500: "#64748B",
          600: "#475569",
          700: "#334155",
          800: "#1E293B",
          900: "#0F172A",
          950: "#020617",
        },
      },
      boxShadow: {
        'card': '0 1px 2px 0 rgba(0, 0, 0, 0.04), 0 1px 1px 0 rgba(0, 0, 0, 0.02)',
        'card-hover': '0 4px 12px 0 rgba(0, 0, 0, 0.05), 0 1px 3px 0 rgba(0, 0, 0, 0.04)',
        'subtle': '0 1px 3px 0 rgba(0, 0, 0, 0.03)',
        'popover': '0 8px 24px -4px rgba(0, 0, 0, 0.08), 0 4px 8px -2px rgba(0, 0, 0, 0.04)',
      },
    },
  },
  plugins: [],
};
