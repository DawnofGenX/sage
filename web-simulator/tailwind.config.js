/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        alexa: {
          blue: '#00CAFF',
          dark: '#1A1A2E',
          card: '#16213E',
          accent: '#0F3460'
        }
      }
    },
  },
  plugins: [],
}
