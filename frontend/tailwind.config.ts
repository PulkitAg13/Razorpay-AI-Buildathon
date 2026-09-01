/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: { DEFAULT: '#0A0B0F', card: '#12141A', border: '#1E2230' },
        primary: { DEFAULT: '#6366F1', light: '#818CF8', dark: '#4F46E5' },
        success: { DEFAULT: '#10B981', light: '#34D399' },
        warning: { DEFAULT: '#F59E0B', light: '#FCD34D' },
        danger: { DEFAULT: '#EF4444', light: '#F87171' },
        muted: '#94A3B8',
        subtle: '#1E2230',
      },
      fontFamily: { sans: ['Inter', 'system-ui', 'sans-serif'] },
      boxShadow: {
        card: '0 0 0 1px rgba(99,102,241,0.08), 0 4px 24px rgba(0,0,0,0.4)',
        glow: '0 0 20px rgba(99,102,241,0.25)',
      },
      animation: {
        'pulse-slow': 'pulse 3s ease-in-out infinite',
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
      },
      keyframes: {
        fadeIn: { from: { opacity: 0 }, to: { opacity: 1 } },
        slideUp: { from: { opacity: 0, transform: 'translateY(8px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
      },
    },
  },
  plugins: [],
}
