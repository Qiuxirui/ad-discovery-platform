import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import * as adminApi from '../api/admin.js';
import * as merchantApi from '../api/merchant.js';

const AuthContext = createContext(null);

/**
 * 登录态管理（商家 / 管理员双角色，无 redux）。
 * probe() 启动时按当前路径决定探测哪个角色；监听 adx:unauthorized 自动清状态。
 * 权限判定最终仍在服务端，前端只做展示层隐藏。
 */
export function AuthProvider({ children }) {
  const [role, setRole] = useState(null);
  const [me, setMe] = useState(null);
  const [loading, setLoading] = useState(true);

  // 供事件回调读取最新角色，避免在 setState 的 updater 里再触发其它 setState
  const roleRef = useRef(role);
  roleRef.current = role;

  const clear = useCallback(() => {
    setRole(null);
    setMe(null);
  }, []);

  const probe = useCallback(async () => {
    setLoading(true);
    const path = typeof window !== 'undefined' ? window.location.pathname : '';
    const preferAdmin = path.startsWith('/admin');
    try {
      if (preferAdmin) {
        try {
          const admin = await adminApi.getMe();
          setRole('admin');
          setMe(admin);
        } catch {
          clear();
        }
      } else {
        try {
          const merchant = await merchantApi.getMe();
          setRole('merchant');
          setMe(merchant);
        } catch {
          clear();
        }
      }
    } finally {
      setLoading(false);
    }
  }, [clear]);

  useEffect(() => {
    probe();
  }, [probe]);

  // 任意 API 返回 401 时清空对应角色状态，由 RequireAuth 触发跳登录
  useEffect(() => {
    const handler = (event) => {
      const scope = event && event.detail ? event.detail.scope : '';
      const current = roleRef.current;
      // 作用域不匹配（例如商家会话遇到管理端 401）时不清空当前角色
      if (scope && current && scope !== current) return;
      if (!current) return;
      setRole(null);
      setMe(null);
    };
    window.addEventListener('adx:unauthorized', handler);
    return () => window.removeEventListener('adx:unauthorized', handler);
  }, []);

  /**
   * 直接写入会话（注册成功后落状态用）。
   * @param {'merchant'|'admin'} nextRole
   * @param {object} payload
   */
  const applySession = useCallback((nextRole, payload) => {
    setRole(nextRole);
    setMe(payload || null);
  }, []);

  /** @param {{account:string, password:string}} credentials */
  const loginMerchant = useCallback(async (credentials) => {
    const res = await merchantApi.login(credentials);
    const merchant = (res && res.merchant) || res || null;
    setRole('merchant');
    setMe(merchant);
    return merchant;
  }, []);

  /** @param {{username:string, password:string}} credentials */
  const loginAdmin = useCallback(async (credentials) => {
    const res = await adminApi.login(credentials);
    const admin = (res && res.admin) || res || null;
    setRole('admin');
    setMe(admin);
    return admin;
  }, []);

  const logout = useCallback(async () => {
    const current = role;
    try {
      if (current === 'merchant') await merchantApi.logout();
      if (current === 'admin') await adminApi.logout();
    } catch {
      /* 登出失败也清本地状态 */
    } finally {
      clear();
    }
  }, [role, clear]);

  /** 管理员顶栏徽标等需要刷新 me 时使用 */
  const refreshMe = useCallback(async () => {
    try {
      if (role === 'merchant') setMe(await merchantApi.getMe());
      if (role === 'admin') setMe(await adminApi.getMe());
    } catch {
      clear();
    }
  }, [role, clear]);

  const value = useMemo(
    () => ({
      role,
      me,
      loading,
      probe,
      applySession,
      loginMerchant,
      loginAdmin,
      logout,
      refreshMe,
      isMerchant: role === 'merchant',
      isAdmin: role === 'admin',
    }),
    [role, me, loading, probe, applySession, loginMerchant, loginAdmin, logout, refreshMe],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth 必须在 AuthProvider 内使用');
  return ctx;
}

export default AuthContext;
