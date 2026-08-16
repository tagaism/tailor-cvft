import { createTheme } from "@mui/material/styles";

declare module "@mui/material/styles" {
  interface Palette {
    status: Record<string, string>;
  }
  interface PaletteOptions {
    status?: Record<string, string>;
  }
}

const theme = createTheme({
  palette: {
    primary: { main: "#9a3412", dark: "#7c2d12", light: "#c2410c", contrastText: "#fffdf8" },
    secondary: { main: "#57534e" },
    background: { default: "#f3efe6", paper: "#fffdf8" },
    text: { primary: "#1c1917", secondary: "#6f675e" },
    success: { main: "#3f6212", light: "#ecfccb" },
    warning: { main: "#92400e", light: "#fef3c7" },
    error: { main: "#9f1239", light: "#ffe4e6" },
    divider: "#e4dccf",
    status: {
      saved: "#78716c",
      applied: "#1d4ed8",
      under_consideration: "#b45309",
      rejected: "#9f1239",
      declined: "#57534e",
    },
  },
  shape: { borderRadius: 10 },
  typography: {
    fontFamily: '"Avenir Next", "Segoe UI", "Helvetica Neue", Helvetica, Arial, sans-serif',
    h1: { fontSize: "1.75rem", fontWeight: 650 },
    h2: { fontSize: "1.15rem", fontWeight: 650 },
    button: { textTransform: "none", fontWeight: 600 },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          background:
            "radial-gradient(1200px 500px at 10% -10%, #fff7ed 0%, transparent 55%), #f3efe6",
        },
      },
    },
    MuiPaper: {
      defaultProps: { elevation: 0 },
      styleOverrides: {
        root: { border: "1px solid #e4dccf" },
      },
    },
    MuiButton: {
      defaultProps: { disableElevation: true },
    },
    MuiTextField: {
      defaultProps: { size: "small", fullWidth: true },
    },
    MuiChip: {
      defaultProps: { size: "small" },
    },
  },
});

export default theme;
