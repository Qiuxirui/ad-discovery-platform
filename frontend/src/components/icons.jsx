import React from 'react';

/**
 * 内联 SVG 图标集。禁止使用 @mui/icons-material（需外网安装、体积大）。
 * 全部 24×24 viewBox、currentColor 描边、无外部引用。
 */

/**
 * @param {{size?: number, style?: object, children: React.ReactNode}} props
 */
function Svg({ size = 20, style, children, ...rest }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      focusable="false"
      style={{ display: 'block', flex: '0 0 auto', ...style }}
      {...rest}
    >
      {children}
    </svg>
  );
}

const strokeProps = {
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
};

export function IconSearch(props) {
  return (
    <Svg {...props}>
      <circle cx="11" cy="11" r="6.5" {...strokeProps} />
      <path d="M16 16l4 4" {...strokeProps} />
    </Svg>
  );
}

export function IconStar({ filled = false, ...props }) {
  return (
    <Svg {...props}>
      <path
        d="M12 3.6l2.6 5.3 5.9.9-4.3 4.1 1 5.8-5.2-2.7-5.2 2.7 1-5.8L3.5 9.8l5.9-.9L12 3.6z"
        {...strokeProps}
        fill={filled ? 'currentColor' : 'none'}
      />
    </Svg>
  );
}

export function IconMore(props) {
  return (
    <Svg {...props}>
      <circle cx="5" cy="12" r="1.6" fill="currentColor" />
      <circle cx="12" cy="12" r="1.6" fill="currentColor" />
      <circle cx="19" cy="12" r="1.6" fill="currentColor" />
    </Svg>
  );
}

export function IconClose(props) {
  return (
    <Svg {...props}>
      <path d="M6 6l12 12M18 6L6 18" {...strokeProps} />
    </Svg>
  );
}

export function IconChevronLeft(props) {
  return (
    <Svg {...props}>
      <path d="M14.5 5.5L8 12l6.5 6.5" {...strokeProps} />
    </Svg>
  );
}

export function IconChevronRight(props) {
  return (
    <Svg {...props}>
      <path d="M9.5 5.5L16 12l-6.5 6.5" {...strokeProps} />
    </Svg>
  );
}

export function IconChevronDown(props) {
  return (
    <Svg {...props}>
      <path d="M5.5 9l6.5 6.5L18.5 9" {...strokeProps} />
    </Svg>
  );
}

export function IconArrowLeft(props) {
  return (
    <Svg {...props}>
      <path d="M19 12H5M11 6l-6 6 6 6" {...strokeProps} />
    </Svg>
  );
}

export function IconExternal(props) {
  return (
    <Svg {...props}>
      <path d="M14 4h6v6" {...strokeProps} />
      <path d="M20 4l-8.5 8.5" {...strokeProps} />
      <path d="M18 14.5V19a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h4.5" {...strokeProps} />
    </Svg>
  );
}

export function IconShield(props) {
  return (
    <Svg {...props}>
      <path d="M12 3.2l7 2.6v5.6c0 4.3-2.9 7.4-7 9.4-4.1-2-7-5.1-7-9.4V5.8l7-2.6z" {...strokeProps} />
      <path d="M9 12l2.1 2.1L15.4 10" {...strokeProps} />
    </Svg>
  );
}

export function IconReport(props) {
  return (
    <Svg {...props}>
      <path d="M5 4.5h9l5 5v10a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-14a1 1 0 0 1 1-1z" {...strokeProps} />
      <path d="M13.5 4.6V10h5" {...strokeProps} />
      <path d="M12 13v3.4M12 18.6v.2" {...strokeProps} />
    </Svg>
  );
}

export function IconCheck(props) {
  return (
    <Svg {...props}>
      <path d="M5 12.5l4.5 4.5L19 7.5" {...strokeProps} />
    </Svg>
  );
}

export function IconCheckCircle(props) {
  return (
    <Svg {...props}>
      <circle cx="12" cy="12" r="8.5" {...strokeProps} />
      <path d="M8.2 12.2l2.6 2.6 5-5.2" {...strokeProps} />
    </Svg>
  );
}

export function IconWarn(props) {
  return (
    <Svg {...props}>
      <path d="M12 4.2l8.4 15H3.6L12 4.2z" {...strokeProps} />
      <path d="M12 9.6v4.2M12 16.6v.2" {...strokeProps} />
    </Svg>
  );
}

export function IconDownload(props) {
  return (
    <Svg {...props}>
      <path d="M12 4v10.5M7.5 10.5L12 15l4.5-4.5" {...strokeProps} />
      <path d="M5 18.5h14" {...strokeProps} />
    </Svg>
  );
}

export function IconUpload(props) {
  return (
    <Svg {...props}>
      <path d="M12 15.5V5M7.5 9.5L12 5l4.5 4.5" {...strokeProps} />
      <path d="M5 18.5h14" {...strokeProps} />
    </Svg>
  );
}

export function IconLogout(props) {
  return (
    <Svg {...props}>
      <path d="M15 5.5H6.5a1 1 0 0 0-1 1v11a1 1 0 0 0 1 1H15" {...strokeProps} />
      <path d="M11 12h9M17 8.5l3.5 3.5L17 15.5" {...strokeProps} />
    </Svg>
  );
}

export function IconClock(props) {
  return (
    <Svg {...props}>
      <circle cx="12" cy="12" r="8.5" {...strokeProps} />
      <path d="M12 7.5V12l3 1.8" {...strokeProps} />
    </Svg>
  );
}

export function IconPlus(props) {
  return (
    <Svg {...props}>
      <path d="M12 5v14M5 12h14" {...strokeProps} />
    </Svg>
  );
}

export function IconEdit(props) {
  return (
    <Svg {...props}>
      <path d="M4.5 19.5h4l10-10a2.1 2.1 0 0 0-3-3l-10 10v3z" {...strokeProps} />
      <path d="M14.5 6.5l3 3" {...strokeProps} />
    </Svg>
  );
}

export function IconTrash(props) {
  return (
    <Svg {...props}>
      <path d="M4.5 7h15M9.5 7V4.8h5V7" {...strokeProps} />
      <path d="M6.5 7l.8 12a1 1 0 0 0 1 .9h7.4a1 1 0 0 0 1-.9L17.5 7" {...strokeProps} />
    </Svg>
  );
}

export function IconEye(props) {
  return (
    <Svg {...props}>
      <path d="M2.8 12S6 6.2 12 6.2 21.2 12 21.2 12 18 17.8 12 17.8 2.8 12 2.8 12z" {...strokeProps} />
      <circle cx="12" cy="12" r="2.6" {...strokeProps} />
    </Svg>
  );
}

export function IconEyeOff(props) {
  return (
    <Svg {...props}>
      <path d="M4 4l16 16" {...strokeProps} />
      <path d="M9.6 6.6A9.7 9.7 0 0 1 12 6.2c6 0 9.2 5.8 9.2 5.8a15 15 0 0 1-2.6 3.3" {...strokeProps} />
      <path d="M6.4 8.1A15.6 15.6 0 0 0 2.8 12s3.2 5.8 9.2 5.8a9.4 9.4 0 0 0 3.2-.5" {...strokeProps} />
    </Svg>
  );
}

export function IconFilter(props) {
  return (
    <Svg {...props}>
      <path d="M4 6.5h16M7 12h10M10 17.5h4" {...strokeProps} />
    </Svg>
  );
}

export function IconInfo(props) {
  return (
    <Svg {...props}>
      <circle cx="12" cy="12" r="8.5" {...strokeProps} />
      <path d="M12 11v5.5M12 7.6v.2" {...strokeProps} />
    </Svg>
  );
}

export function IconHome(props) {
  return (
    <Svg {...props}>
      <path d="M4.5 10.5L12 4l7.5 6.5V19a1 1 0 0 1-1 1h-13a1 1 0 0 1-1-1v-8.5z" {...strokeProps} />
      <path d="M9.5 20v-5.5h5V20" {...strokeProps} />
    </Svg>
  );
}

export function IconMenu(props) {
  return (
    <Svg {...props}>
      <path d="M4 7h16M4 12h16M4 17h16" {...strokeProps} />
    </Svg>
  );
}

export function IconRefresh(props) {
  return (
    <Svg {...props}>
      <path d="M19.5 12a7.5 7.5 0 1 1-2.2-5.3" {...strokeProps} />
      <path d="M19.8 4.5v4.2h-4.2" {...strokeProps} />
    </Svg>
  );
}

export function IconImage(props) {
  return (
    <Svg {...props}>
      <rect x="3.5" y="5" width="17" height="14" rx="1.6" {...strokeProps} />
      <circle cx="8.7" cy="10" r="1.4" {...strokeProps} />
      <path d="M4.2 16.6l4.6-4.2 3.4 3.1 3.2-2.6 3.6 3.4" {...strokeProps} />
    </Svg>
  );
}

export const icons = {
  Search: IconSearch,
  Star: IconStar,
  More: IconMore,
  Close: IconClose,
  ChevronLeft: IconChevronLeft,
  ChevronRight: IconChevronRight,
  ChevronDown: IconChevronDown,
  External: IconExternal,
  Shield: IconShield,
  Report: IconReport,
  Check: IconCheck,
  CheckCircle: IconCheckCircle,
  Warn: IconWarn,
  Download: IconDownload,
  Upload: IconUpload,
  Logout: IconLogout,
  Clock: IconClock,
  Plus: IconPlus,
  Edit: IconEdit,
  Trash: IconTrash,
  Eye: IconEye,
  EyeOff: IconEyeOff,
  Filter: IconFilter,
  Info: IconInfo,
  Home: IconHome,
  Menu: IconMenu,
  Refresh: IconRefresh,
  Image: IconImage,
};

export default icons;
