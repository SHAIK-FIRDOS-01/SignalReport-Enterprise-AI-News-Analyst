/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,jsx}',
  ],
  theme: {
    borderRadius: {
      'none': '0',
      DEFAULT: '0',
    },
    extend: {
      colors: {
        'swiss-black': 'var(--swiss-black, #000000)',
        'swiss-white': 'var(--swiss-white, #FFFFFF)',
        'swiss-red': 'var(--swiss-red, #E60000)',
        'swiss-gray': 'var(--swiss-gray, #F5F5F5)',
      },
      borderWidth: {
        'heavy': '2px',
      },
      letterSpacing: {
        'tighter': '-0.04em',
        'widest': '0.15em',
      },
    },
  },
  plugins: [],
};
