/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#15201B",
        stage: "#1B2620",
        panel: "#243530",
        panelLight: "#2E433C",
        cream: "#F6F1E7",
        mute: "#B8C4BC",
        amber: "#E8A33D",
        amberDark: "#C7842A",
        sage: "#5FA88F",
        coral: "#E0735C"
      },
      fontFamily: {
        display: ["Fraunces", "serif"],
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"]
      },
      boxShadow: {
        glow: "0 0 80px 10px rgba(232, 163, 61, 0.18)"
      },
      keyframes: {
        sweep: {
          "0%": { transform: "translateX(-30%)" },
          "100%": { transform: "translateX(30%)" }
        },
        rise: {
          "0%": { opacity: 0, transform: "translateY(14px)" },
          "100%": { opacity: 1, transform: "translateY(0)" }
        },
        pulseBar: {
          "0%, 100%": { transform: "scaleY(0.4)" },
          "50%": { transform: "scaleY(1)" }
        }
      },
      animation: {
        sweep: "sweep 6s ease-in-out infinite alternate",
        rise: "rise 0.7s ease-out forwards",
        pulseBar: "pulseBar 1.2s ease-in-out infinite"
      }
    }
  },
  plugins: []
};
