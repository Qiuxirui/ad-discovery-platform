import React, { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react';

/** @typedef {{id:number, message:string, level:'info'|'success'|'error'|'warning'}} ToastItem */

const ToastContext = createContext(null);

/**
 * 轻量 toast 队列。固定底部居中，最多同时展示 3 条，自动消失。
 * 所有页面（收藏/隐藏/举报/保存反馈）都通过 showToast 给反馈。
 */
export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState(/** @type {ToastItem[]} */ ([]));
  const seqRef = useRef(0);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((item) => item.id !== id));
  }, []);

  const showToast = useCallback(
    (message, level = 'info', duration = 2800) => {
      if (!message) return -1;
      seqRef.current += 1;
      const id = seqRef.current;
      setToasts((prev) => {
        const next = [...prev, { id, message, level }];
        return next.slice(-3);
      });
      window.setTimeout(() => removeToast(id), duration);
      return id;
    },
    [removeToast],
  );

  const value = useMemo(() => ({ toasts, showToast, removeToast }), [toasts, showToast, removeToast]);

  return <ToastContext.Provider value={value}>{children}</ToastContext.Provider>;
}

/**
 * @returns {{toasts: ToastItem[], showToast: (message:string, level?:string, duration?:number)=>number, removeToast:(id:number)=>void}}
 */
export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error('useToast 必须在 ToastProvider 内使用');
  }
  return ctx;
}

export default ToastContext;
