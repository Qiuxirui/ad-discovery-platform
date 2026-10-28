import React from 'react';
import AppRoutes from './routes.jsx';

/**
 * 应用根组件。
 * 布局（顶栏/通知条/页脚）由 AppLayout 提供，路由表见 routes.jsx。
 * Context Provider 在 main.jsx 挂载，保证 Toast 覆盖全站。
 */
export default function App() {
  return <AppRoutes />;
}
