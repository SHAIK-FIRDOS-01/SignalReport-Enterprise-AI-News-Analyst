import React, { useState, useEffect } from 'react';
import { SwissInput } from '../ui/SwissInput.jsx';
import { SwissButton } from '../ui/SwissButton.jsx';
import { api } from '../../lib/api.js';
import { API_ROUTES } from '../../lib/constants.js';

/**
 * Swiss Poster Login Form with 429 Rate-Limit Lockout Display.
 * Conforms to Ponytail Ultra: native React hooks, standard Web APIs, zero state machine bloat.
 *
 * @param {object} props
 * @param {() => void} props.onLoginSuccess - Callback invoked on successful authentication
 * @param {() => void} [props.onSwitchToRegister] - Callback to toggle registration view
 */
export function LoginForm({ onLoginSuccess, onSwitchToRegister }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [lockoutSeconds, setLockoutSeconds] = useState(0);

  useEffect(() => {
    if (lockoutSeconds <= 0) return;
    const interval = setInterval(() => {
      setLockoutSeconds((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(interval);
  }, [lockoutSeconds]);

  async function handleSubmit(e) {
    e.preventDefault();
    if (isSubmitting || lockoutSeconds > 0) return;

    if (!email.trim() || !password) {
      setError('PLEASE ENTER BOTH EMAIL AND PASSWORD');
      return;
    }

    setIsSubmitting(true);
    setError('');

    try {
      const data = await api(API_ROUTES.AUTH.LOGIN, {
        method: 'POST',
        body: {
          email: email.trim().toLowerCase(),
          password,
        },
      });

      if (typeof onLoginSuccess === 'function') {
        onLoginSuccess(data?.user || { email: email.trim().toLowerCase() });
      }
    } catch (err) {
      if (err.status === 429) {
        const retry = typeof err.retryAfter === 'number' && err.retryAfter > 0 ? err.retryAfter : 900;
        setLockoutSeconds(retry);
        setError('RATE LIMIT EXCEEDED. TEMPORARY ACCOUNT LOCKOUT.');
      } else {
        setError(err.detail || err.message || 'AUTHENTICATION FAILED');
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  const lockoutMinutes = Math.floor(lockoutSeconds / 60);
  const lockoutSecs = lockoutSeconds % 60;
  const formattedLockout = `${String(lockoutMinutes).padStart(2, '0')}:${String(lockoutSecs).padStart(2, '0')}`;

  return (
    <form onSubmit={handleSubmit} className="flex flex-col space-y-4" noValidate>
      <div className="border-b-2 border-swiss-black pb-3 mb-2">
        <h2 className="text-2xl font-black uppercase tracking-tight text-swiss-black">
          ANALYST SIGN IN
        </h2>
        <p className="text-xs font-bold uppercase tracking-wider text-neutral-500">
          ENTER YOUR CREDENTIALS
        </p>
      </div>

      {error && (
        <div
          data-testid="login-error"
          className="p-3 border-2 border-swiss-black bg-swiss-red text-swiss-white text-xs font-bold uppercase tracking-wider"
        >
          {error}
        </div>
      )}

      {lockoutSeconds > 0 && (
        <div
          data-testid="lockout-banner"
          className="p-3 border-2 border-swiss-black bg-swiss-black text-swiss-white text-xs font-mono font-bold uppercase tracking-widest flex items-center justify-between"
        >
          <span className="flex items-center gap-2">
            <span className="w-2 h-2 bg-swiss-red animate-pulse" />
            LOCKED: {formattedLockout} REMAINING
          </span>
          <span className="text-[10px] text-neutral-400">HTTP 429 BACKOFF</span>
        </div>
      )}

      <SwissInput
        id="login-email"
        label="01 / EMAIL ADDRESS"
        type="email"
        placeholder="analyst@signalreport.io"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        disabled={isSubmitting || lockoutSeconds > 0}
        required
      />

      <SwissInput
        id="login-password"
        label="02 / PASSWORD"
        type="password"
        placeholder="••••••••••••••••"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        disabled={isSubmitting || lockoutSeconds > 0}
        required
      />

      <div className="pt-2 flex flex-col gap-3">
        <SwissButton
          type="submit"
          variant="primary"
          disabled={isSubmitting || lockoutSeconds > 0}
          className="w-full h-12"
        >
          {lockoutSeconds > 0
            ? `LOCKED (${formattedLockout})`
            : isSubmitting
            ? 'AUTHENTICATING...'
            : 'SIGN IN →'}
        </SwissButton>

        {onSwitchToRegister && (
          <button
            type="button"
            onClick={onSwitchToRegister}
            className="text-xs font-bold uppercase tracking-wider text-swiss-black hover:underline text-left select-none"
          >
            NO ACCOUNT YET? // REGISTER →
          </button>
        )}
      </div>
    </form>
  );
}
