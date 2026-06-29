export const colors = {
  background: "#07141f",
  foreground: "#f8f7f2",
  primary: "#c59b3b",
  primaryForeground: "#07141f",
  accent: "#2f4556",
  muted: "#e8e3d4",
  mutedForeground: "#4a5565",
  border: "#31465a",
  success: "#2f7d4f",
  warning: "#c67c1f",
  danger: "#b63b3b",
} as const;

export const spacing = {
  xs: "0.25rem",
  sm: "0.5rem",
  md: "0.75rem",
  lg: "1rem",
  xl: "1.5rem",
  "2xl": "2rem",
} as const;

export const radii = {
  sm: "0.25rem",
  md: "0.5rem",
  lg: "0.75rem",
} as const;

export const shadows = {
  card: "0 10px 30px rgba(7, 20, 31, 0.16)",
} as const;

export const typography = {
  body: "16px",
  heading: "1.5rem",
  label: "0.875rem",
} as const;

export const breakpoints = {
  sm: "640px",
  md: "768px",
  lg: "1024px",
  xl: "1280px",
} as const;
