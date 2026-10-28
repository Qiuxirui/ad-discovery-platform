import React, { useEffect } from 'react';
import { Navigate, Route, Routes, useLocation } from 'react-router-dom';

import AppLayout from './components/AppLayout.jsx';
import MerchantLayout from './components/MerchantLayout.jsx';
import AdminLayout from './components/AdminLayout.jsx';
import RequireAuth from './components/RequireAuth.jsx';

import HomePage from './pages/HomePage.jsx';
import CategoryPage from './pages/CategoryPage.jsx';
import SearchPage from './pages/SearchPage.jsx';
import AdDetailPage from './pages/AdDetailPage.jsx';
import GoPage from './pages/GoPage.jsx';
import FavoritesPage from './pages/FavoritesPage.jsx';
import PreferencesPage from './pages/PreferencesPage.jsx';
import ReportStatusPage from './pages/ReportStatusPage.jsx';
import PolicyPage from './pages/PolicyPage.jsx';
import NotFoundPage from './pages/NotFoundPage.jsx';

import MerchantLoginPage from './pages/merchant/MerchantLoginPage.jsx';
import MerchantSignupPage from './pages/merchant/MerchantSignupPage.jsx';
import MerchantAdsPage from './pages/merchant/MerchantAdsPage.jsx';
import MerchantAdEditPage from './pages/merchant/MerchantAdEditPage.jsx';
import MerchantReportPage from './pages/merchant/MerchantReportPage.jsx';
import MerchantProfilePage from './pages/merchant/MerchantProfilePage.jsx';

import AdminLoginPage from './pages/admin/AdminLoginPage.jsx';
import AdminDashboardPage from './pages/admin/AdminDashboardPage.jsx';
import AdminReviewPage from './pages/admin/AdminReviewPage.jsx';
import AdminAdsPage from './pages/admin/AdminAdsPage.jsx';
import AdminReportsPage from './pages/admin/AdminReportsPage.jsx';
import AdminMerchantsPage from './pages/admin/AdminMerchantsPage.jsx';
import AdminCategoriesPage from './pages/admin/AdminCategoriesPage.jsx';
import AdminStatsPage from './pages/admin/AdminStatsPage.jsx';

import tracker from './tracker/index.js';

/**
 * 路由 → 页面标识（埋点 page 字段枚举：home|list|search|detail|favorites）。
 * @param {string} pathname
 * @returns {string|null}
 */
function resolvePageKey(pathname) {
  if (pathname === '/') return 'home';
  if (pathname.startsWith('/c/')) return 'list';
  if (pathname === '/search') return 'search';
  if (pathname.startsWith('/ad/')) return 'detail';
  if (pathname === '/favorites') return 'favorites';
  return null;
}

/** 路由切换后回到顶部，并按页面标识上报 page_view（去重由后端负责） */
function RouteWatcher() {
  const location = useLocation();

  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
    const page = resolvePageKey(location.pathname);
    if (page) {
      tracker.track('page_view', { page });
    }
  }, [location.pathname, location.search]);

  return null;
}

/**
 * 完整路由表（ARCHITECTURE.md §7.1）。
 * 每个路径都有真实实现，不留占位页。
 */
export default function AppRoutes() {
  return (
    <>
      <RouteWatcher />
      <Routes>
        {/* 用户端：统一走 AppLayout */}
        <Route element={<AppLayout />}>
          <Route index element={<HomePage />} />
          <Route path="c/:slug" element={<CategoryPage />} />
          <Route path="search" element={<SearchPage />} />
          <Route path="ad/:id" element={<AdDetailPage />} />
          <Route path="go/:adId" element={<GoPage />} />
          <Route path="favorites" element={<FavoritesPage />} />
          <Route path="preferences" element={<PreferencesPage />} />
          <Route path="report-status" element={<ReportStatusPage />} />
          <Route path="policy/ads" element={<PolicyPage kind="ads" />} />
          <Route path="policy/privacy" element={<PolicyPage kind="privacy" />} />
          <Route path="policy/report" element={<PolicyPage kind="report" />} />
          <Route path="about" element={<PolicyPage kind="about" />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>

        {/* 商家端：登录/注册为独立页（无侧栏） */}
        <Route path="/merchant/login" element={<MerchantLoginPage />} />
        <Route path="/merchant/signup" element={<MerchantSignupPage />} />
        <Route path="/merchant" element={<RequireAuth role="merchant" />}>
          <Route element={<MerchantLayout />}>
            <Route index element={<Navigate to="/merchant/ads" replace />} />
            <Route path="ads" element={<MerchantAdsPage />} />
            <Route path="ads/new" element={<MerchantAdEditPage mode="create" />} />
            <Route path="ads/:id" element={<MerchantAdEditPage mode="edit" />} />
            <Route path="report" element={<MerchantReportPage />} />
            <Route path="profile" element={<MerchantProfilePage />} />
          </Route>
        </Route>

        {/* 管理端 */}
        <Route path="/admin/login" element={<AdminLoginPage />} />
        <Route path="/admin" element={<RequireAuth role="admin" />}>
          <Route element={<AdminLayout />}>
            <Route index element={<AdminDashboardPage />} />
            <Route path="review" element={<AdminReviewPage />} />
            <Route path="ads" element={<AdminAdsPage />} />
            <Route path="reports" element={<AdminReportsPage />} />
            <Route path="merchants" element={<AdminMerchantsPage />} />
            <Route path="categories" element={<AdminCategoriesPage />} />
            <Route path="stats" element={<AdminStatsPage />} />
          </Route>
        </Route>

        {/* 兜底：未知路径（同上，AppLayout 内的 * 已覆盖，此处不再重复注册） */}
      </Routes>
    </>
  );
}
