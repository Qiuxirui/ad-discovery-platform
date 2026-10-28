import React from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import theme from './theme.js';
import './styles/global.css';
import App from './App.jsx';
import { ToastProvider } from './context/ToastContext.jsx';
import { VisitorProvider } from './context/VisitorContext.jsx';
import { CategoriesProvider } from './context/CategoriesContext.jsx';
import { AuthProvider } from './context/AuthContext.jsx';
import Toast from './components/Toast.jsx';

const container = document.getElementById('root');
if (!container) {
  throw new Error('缺少 #root 挂载点');
}

createRoot(container).render(
  <React.StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <ToastProvider>
          <VisitorProvider>
            <CategoriesProvider>
              <AuthProvider>
                <App />
                <Toast />
              </AuthProvider>
            </CategoriesProvider>
          </VisitorProvider>
        </ToastProvider>
      </BrowserRouter>
    </ThemeProvider>
  </React.StrictMode>,
);
