import { createTheme } from '@mui/material/styles';

/**
 * 设计 token —— 唯一来源，逐字对应 ARCHITECTURE.md §6.2 与 PRD §9.1。
 * accent（橙）只允许用于「广告」角标与「即将结束」徽标，不可作为装饰色。
 */
export const tokens = {
  primary: '#1F3A5F',
  accent: '#E8590C',
  bg: '#F7F8FA',
  surface: '#FFFFFF',
  textPrimary: '#1A1A1A',
  textSecondary: '#5A6472',
  border: '#E2E6EC',
  danger: '#B3261E',
  success: '#1E7A46',
  radiusCard: 12,
  shadowCard: '0 1px 2px rgba(15,23,42,.06)',
  shadowCardHover: '0 6px 16px rgba(15,23,42,.12)',
};

const FONT_STACK =
  "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'Helvetica Neue', Arial, sans-serif";

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: tokens.primary, contrastText: '#FFFFFF' },
    secondary: { main: tokens.accent, contrastText: '#FFFFFF' },
    background: { default: tokens.bg, paper: tokens.surface },
    text: { primary: tokens.textPrimary, secondary: tokens.textSecondary },
    error: { main: tokens.danger },
    success: { main: tokens.success },
    divider: tokens.border,
    action: {
      hover: 'rgba(31,58,95,.06)',
      selected: 'rgba(31,58,95,.10)',
    },
  },
  shape: { borderRadius: 12 },
  typography: {
    fontFamily: FONT_STACK,
    fontSize: 16,
    body1: { fontSize: 16, lineHeight: 1.65 },
    body2: { fontSize: 14, lineHeight: 1.6 },
    caption: { fontSize: 12, lineHeight: 1.5 },
    h1: { fontSize: 30, fontWeight: 700, lineHeight: 1.3 },
    h2: { fontSize: 24, fontWeight: 700, lineHeight: 1.35 },
    h3: { fontSize: 20, fontWeight: 700, lineHeight: 1.4 },
    h4: { fontSize: 18, fontWeight: 600, lineHeight: 1.45 },
    h5: { fontSize: 16, fontWeight: 600, lineHeight: 1.5 },
    h6: { fontSize: 15, fontWeight: 600, lineHeight: 1.5 },
    button: { textTransform: 'none', fontWeight: 600, letterSpacing: 0 },
  },
  transitions: {
    duration: { shortest: 150, short: 200 },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: { backgroundColor: tokens.bg },
      },
    },
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: {
        root: { borderRadius: 8, textTransform: 'none', fontWeight: 600, minHeight: 40 },
        sizeLarge: { minHeight: 48, fontSize: 16 },
      },
    },
    MuiPaper: {
      defaultProps: { elevation: 0 },
      styleOverrides: {
        root: { backgroundImage: 'none' },
        outlined: { borderColor: tokens.border },
      },
    },
    MuiCard: {
      defaultProps: { elevation: 0 },
      styleOverrides: {
        root: {
          borderRadius: tokens.radiusCard,
          border: `1px solid ${tokens.border}`,
          boxShadow: tokens.shadowCard,
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { borderRadius: 6, fontWeight: 600, fontSize: 12 },
        sizeSmall: { height: 22 },
      },
    },
    MuiTextField: {
      defaultProps: { size: 'small', variant: 'outlined' },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: { borderRadius: 8, backgroundColor: tokens.surface },
      },
    },
    MuiTabs: {
      styleOverrides: {
        root: { minHeight: 44 },
        indicator: { height: 3, borderRadius: '3px 3px 0 0' },
      },
    },
    MuiTab: {
      styleOverrides: {
        root: { minHeight: 44, textTransform: 'none', fontSize: 14, fontWeight: 600, minWidth: 72 },
      },
    },
    MuiTooltip: {
      defaultProps: { arrow: true },
      styleOverrides: {
        tooltip: { fontSize: 12, maxWidth: 280, backgroundColor: '#33404F', lineHeight: 1.6 },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: { borderColor: tokens.border, fontSize: 14 },
        head: { fontWeight: 700, color: tokens.textSecondary, backgroundColor: '#FBFCFD' },
      },
    },
    MuiLink: {
      defaultProps: { underline: 'hover' },
      styleOverrides: {
        root: { color: tokens.primary, cursor: 'pointer' },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: { borderRadius: 14 },
      },
    },
    MuiAlert: {
      styleOverrides: {
        root: { borderRadius: 10, fontSize: 14 },
      },
    },
  },
});

export default theme;
