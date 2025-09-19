/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        fuel: {
          grass: '#4ade80',
          shrub: '#fb923c',
          timber: '#22c55e',
          slash: '#ef4444',
          urban: '#64748b',
          water: '#3b82f6',
        }
      }
    },
  },
  plugins: [],
}