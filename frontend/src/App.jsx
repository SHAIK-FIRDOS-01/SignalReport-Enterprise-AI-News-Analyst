import React, { useState, useEffect } from 'react';
import { AuthPosterLayout } from './components/auth/AuthPosterLayout.jsx';
import { LoginForm } from './components/auth/LoginForm.jsx';
import { RegisterForm } from './components/auth/RegisterForm.jsx';
import { DashboardPage } from './pages/DashboardPage.jsx';
import { SharePage } from './pages/SharePage.jsx';
import { NetworkBanner } from './components/ui/NetworkBanner.jsx';
import { SwissErrorBoundary } from './components/ui/SwissErrorBoundary.jsx';
import { api } from './lib/api.js';
import { API_ROUTES } from './lib/constants.js';

/**
 * Root Application Shell.
 * Conforms to Ponytail Ultra: native React hooks, browser-native routing, zero state machine / router libraries.
 * Hardened with isolated SwissErrorBoundary crash barriers across subsystems.
 */
export function App() {
  const [view, setView] = useState(() => {
    if (typeof window !== 'undefined') {
      const path = window.location.pathname;
      const hash = (window.location.hash || '').toLowerCase();
      const params = new URLSearchParams(window.location.search);
      const queryView = params.get('view')?.toUpperCase();
      if (queryView && ['LOGIN', 'REGISTER', 'DASHBOARD', 'SHARE'].includes(queryView)) {
        return queryView;
      }
      if (path.startsWith('/share/') || hash.startsWith('#share')) {
        return 'SHARE';
      }
      if (path.includes('dashboard') || hash.includes('dashboard')) {
        return 'DASHBOARD';
      }
      if (path.includes('register') || hash.includes('register')) {
        return 'REGISTER';
      }
    }
    return 'LOGIN';
  });
  const [currentUser, setCurrentUser] = useState(null);
  const [pendingEmail, setPendingEmail] = useState('');
  const [shareToken, setShareToken] = useState(() => {
    if (typeof window !== 'undefined' && window.location.pathname.startsWith('/share/')) {
      return window.location.pathname.replace('/share/', '');
    }
    return 'share-sample-01';
  });

  // Keep routing synced with browser history (back/forward and URL paths)
  useEffect(() => {
    function handlePopState() {
      const path = window.location.pathname;
      if (path.startsWith('/share/')) {
        setShareToken(path.replace('/share/', ''));
        setView('SHARE');
      } else if (path.includes('dashboard')) {
        setView('DASHBOARD');
      } else if (path.includes('register')) {
        setView('REGISTER');
      } else {
        setView('LOGIN');
      }
    }

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  // Restore authenticated session on initial mount / page refresh
  useEffect(() => {
    let isMounted = true;
    async function checkAuthSession() {
      try {
        const user = await api(API_ROUTES.AUTH.ME);
        if (isMounted && user && (user.id || user.email)) {
          setCurrentUser(user);
          const path = typeof window !== 'undefined' ? window.location.pathname : '';
          if (!path.startsWith('/share/') && !path.includes('register')) {
            setView('DASHBOARD');
            if (typeof window !== 'undefined' && !path.includes('dashboard')) {
              window.history.replaceState(null, '', '/dashboard');
            }
          }
        }
      } catch {
        if (isMounted) {
          const path = typeof window !== 'undefined' ? window.location.pathname : '';
          if (path.includes('dashboard')) {
            setView('LOGIN');
            if (typeof window !== 'undefined') {
              window.history.replaceState(null, '', '/');
            }
          }
        }
      }
    }

    checkAuthSession();
    return () => {
      isMounted = false;
    };
  }, []);

  function handleRegisterSuccess(email) {
    setPendingEmail(email);
    if (typeof window !== 'undefined') {
      window.history.pushState(null, '', '/');
    }
    setView('LOGIN');
  }

  function handleLoginSuccess(user) {
    setCurrentUser(user || { email: pendingEmail || 'analyst@signalreport.io' });
    if (typeof window !== 'undefined') {
      window.history.pushState(null, '', '/dashboard');
    }
    setView('DASHBOARD');
  }

  function handleLogout() {
    setCurrentUser(null);
    if (typeof window !== 'undefined') {
      window.history.pushState(null, '', '/');
    }
    setView('LOGIN');
  }

  function handleSelectShareToken(token) {
    setShareToken(token);
    if (typeof window !== 'undefined') {
      window.history.pushState(null, '', `/share/${token}`);
    }
    setView('SHARE');
  }

  function handleNavigateHome() {
    if (currentUser) {
      if (typeof window !== 'undefined') {
        window.history.pushState(null, '', '/dashboard');
      }
      setView('DASHBOARD');
    } else {
      if (typeof window !== 'undefined') {
        window.history.pushState(null, '', '/');
      }
      setView('LOGIN');
    }
  }

  return (
    <>
      <NetworkBanner />
      <SwissErrorBoundary moduleName="APPLICATION_ROOT">
        {view === 'SHARE' && (
          <SwissErrorBoundary moduleName="SHARE_DOSSIER">
            <SharePage shareToken={shareToken || 'share-sample-01'} onNavigateHome={handleNavigateHome} />
          </SwissErrorBoundary>
        )}

        {view === 'DASHBOARD' && (
          <SwissErrorBoundary moduleName="INTELLIGENCE_DASHBOARD">
            <DashboardPage
              user={currentUser || { email: 'analyst@signalreport.io' }}
              onLogout={handleLogout}
              onSelectShareToken={handleSelectShareToken}
            />
          </SwissErrorBoundary>
        )}

        {view !== 'SHARE' && view !== 'DASHBOARD' && (
          <SwissErrorBoundary moduleName="IDENTITY_GATEWAY">
            <main className="min-h-screen bg-swiss-white p-4 sm:p-8 flex items-center justify-center">
              <AuthPosterLayout>
                {view === 'LOGIN' && (
                  <LoginForm
                    onLoginSuccess={handleLoginSuccess}
                    onSwitchToRegister={() => setView('REGISTER')}
                  />
                )}

                {view === 'REGISTER' && (
                  <RegisterForm
                    onRegisterSuccess={handleRegisterSuccess}
                    onSwitchToLogin={() => setView('LOGIN')}
                  />
                )}

              </AuthPosterLayout>
            </main>
          </SwissErrorBoundary>
        )}
      </SwissErrorBoundary>
    </>
  );
}

export default App;
