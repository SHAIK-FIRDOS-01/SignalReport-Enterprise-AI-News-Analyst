import React, { useState, useEffect } from 'react';
import { AuthPosterLayout } from './components/auth/AuthPosterLayout.jsx';
import { LoginForm } from './components/auth/LoginForm.jsx';
import { RegisterForm } from './components/auth/RegisterForm.jsx';
import { OtpVerification } from './components/auth/OtpVerification.jsx';
import { DashboardPage } from './pages/DashboardPage.jsx';
import { SharePage } from './pages/SharePage.jsx';
import { NetworkBanner } from './components/ui/NetworkBanner.jsx';
import { SwissErrorBoundary } from './components/ui/SwissErrorBoundary.jsx';

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
      if (queryView && ['LOGIN', 'REGISTER', 'OTP', 'DASHBOARD', 'SHARE'].includes(queryView)) {
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
      if (path.includes('otp') || hash.includes('otp')) {
        return 'OTP';
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

  useEffect(() => {
    function handlePopState() {
      if (window.location.pathname.startsWith('/share/')) {
        setShareToken(window.location.pathname.replace('/share/', ''));
        setView('SHARE');
      }
    }

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  function handleRegisterSuccess(email) {
    setPendingEmail(email);
    setView('OTP');
  }

  function handleOtpSuccess() {
    setView('LOGIN');
  }

  function handleLoginSuccess(user) {
    setCurrentUser(user || { email: pendingEmail || 'operator@signalreport.io' });
    setView('DASHBOARD');
  }

  function handleLogout() {
    setCurrentUser(null);
    setView('LOGIN');
  }

  function handleSelectShareToken(token) {
    setShareToken(token);
    window.history.pushState(null, '', `/share/${token}`);
    setView('SHARE');
  }

  function handleNavigateHome() {
    window.history.pushState(null, '', '/');
    if (currentUser) {
      setView('DASHBOARD');
    } else {
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
              user={currentUser || { email: 'operator@signalreport.io' }}
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

                {view === 'OTP' && (
                  <OtpVerification
                    email={pendingEmail || 'operator@signalreport.io'}
                    onVerifySuccess={handleOtpSuccess}
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
