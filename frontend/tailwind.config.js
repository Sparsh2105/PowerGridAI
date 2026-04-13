/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'core': '#0b0e14',
        'surface': '#151921',
        'elevated': '#1c212c',
        'accent-blue': '#3b82f6',
        'accent-purple': '#8b5cf6',
        'accent-cyan': '#06b6d4',
        'primary': '#f8fafc',
        'secondary': '#94a3b8',
        'success': '#10b981',
        'danger': '#ef4444',
      },
    },
  },
  plugins: [],
}
