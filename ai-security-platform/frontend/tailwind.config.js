/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        danger:  { DEFAULT: "#E24B4A", light: "#FCEBEB", text: "#791F1F" },
        warning: { DEFAULT: "#BA7517", light: "#FAEEDA", text: "#633806" },
        success: { DEFAULT: "#639922", light: "#EAF3DE", text: "#27500A" },
        info:    { DEFAULT: "#378ADD", light: "#E6F1FB", text: "#0C447C" },
      },
      fontFamily: {
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
