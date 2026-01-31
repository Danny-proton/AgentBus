/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                background: "#0a0b10",
                panel: "rgba(26, 27, 38, 0.7)",
                primary: {
                    light: "#6366f1",
                    dark: "#a855f7",
                },
                success: "#10b981",
                warning: "#f59e0b",
                error: "#ef4444",
            },
            backdropBlur: {
                xs: "2px",
            }
        },
    },
    plugins: [],
    darkMode: 'class',
}
