import React, { useState } from 'react';
import { SwissInput } from '../ui/SwissInput.jsx';
import { SwissButton } from '../ui/SwissButton.jsx';
import { api } from '../../lib/api.js';
import { API_ROUTES } from '../../lib/constants.js';

const DISPOSABLE_DOMAINS = new Set([
  'mailinator.com',
  'tempmail.com',
  '10minutemail.com',
  'guerrillamail.com',
  'sharklasers.com',
  'yopmail.com',
  'trashmail.com',
  'temp-mail.org',
]);

/**
 * User Registration Form with Disposable Email Check.
 * Conforms to Ponytail Ultra: native React hooks, standard Web APIs, zero state machine bloat.
 *
 * @param {object} props
 * @param {(email: string) => void} props.onRegisterSuccess - Callback with registered email
 * @param {() => void} [props.onSwitchToLogin] - Optional switch to login tab callback
 */
export function RegisterForm({ onRegisterSuccess, onSwitchToLogin }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState({ email: '', password: '', general: '' });
  const [isSubmitting, setIsSubmitting] = useState(false);

  function validate() {
    const nextErrors = { email: '', password: '', general: '' };
    let isValid = true;

    const trimmedEmail = email.trim().toLowerCase();
    if (!trimmedEmail) {
      nextErrors.email = 'EMAIL ADDRESS IS REQUIRED';
      isValid = false;
    } else {
      const emailDomain = trimmedEmail.split('@')[1];
      if (emailDomain && (DISPOSABLE_DOMAINS.has(emailDomain) || DISPOSABLE_DOMAINS.has(emailDomain.replace(/^sub\./, '')))) {
        nextErrors.email = 'DISPOSABLE EMAIL DOMAINS ARE PROHIBITED';
        isValid = false;
      }
    }

    if (!password) {
      nextErrors.password = 'PASSWORD IS REQUIRED';
      isValid = false;
    } else if (password.length < 8) {
      nextErrors.password = 'PASSWORD MUST BE AT LEAST 8 CHARACTERS';
      isValid = false;
    }

    setErrors(nextErrors);
    return isValid;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!validate() || isSubmitting) return;

    setIsSubmitting(true);
    setErrors({ email: '', password: '', general: '' });

    try {
      await api(API_ROUTES.AUTH.REGISTER, {
        method: 'POST',
        body: {
          email: email.trim().toLowerCase(),
          password,
        },
      });

      if (typeof onRegisterSuccess === 'function') {
        onRegisterSuccess(email.trim().toLowerCase());
      }
    } catch (err) {
      setErrors((prev) => ({
        ...prev,
        general: err.detail || err.message || 'REGISTRATION FAILED',
      }));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col space-y-4" noValidate>
      <div className="border-b-2 border-swiss-black pb-3 mb-2">
        <h2 className="text-2xl font-black uppercase tracking-tight text-swiss-black">
          CREATE ANALYST ACCOUNT
        </h2>
        <p className="text-xs font-bold uppercase tracking-wider text-neutral-500">
          REGISTER FOR EDITORIAL ACCESS
        </p>
      </div>

      {errors.general && (
        <div
          data-testid="register-general-error"
          className="p-3 border-2 border-swiss-black bg-swiss-red text-swiss-white text-xs font-bold uppercase tracking-wider"
        >
          {errors.general}
        </div>
      )}

      <SwissInput
        id="register-email"
        label="01 / EMAIL ADDRESS"
        type="email"
        placeholder="analyst@signalreport.io"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        error={errors.email}
        disabled={isSubmitting}
        required
      />

      <SwissInput
        id="register-password"
        label="02 / PASSWORD"
        type="password"
        placeholder="••••••••••••••••"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        error={errors.password}
        disabled={isSubmitting}
        required
      />

      <div className="pt-2 flex flex-col gap-3">
        <SwissButton
          type="submit"
          variant="primary"
          disabled={isSubmitting}
          className="w-full h-12"
        >
          {isSubmitting ? 'CREATING ACCOUNT...' : 'CREATE ACCOUNT →'}
        </SwissButton>

        {onSwitchToLogin && (
          <button
            type="button"
            onClick={onSwitchToLogin}
            className="text-xs font-bold uppercase tracking-wider text-swiss-black hover:underline text-left select-none"
          >
            ALREADY REGISTERED? // SIGN IN →
          </button>
        )}
      </div>
    </form>
  );
}
