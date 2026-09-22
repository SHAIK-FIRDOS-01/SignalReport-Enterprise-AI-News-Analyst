import React, { useState, useEffect, useRef } from 'react';
import { SwissButton } from '../ui/SwissButton.jsx';
import { api } from '../../lib/api.js';
import { API_ROUTES } from '../../lib/constants.js';

/**
 * 6-Digit Segmented OTP Verification Component.
 * Conforms to Ponytail Ultra: native React hooks, standard Web APIs, zero state machine bloat.
 *
 * @param {object} props
 * @param {string} props.email - User email address awaiting verification
 * @param {() => void} props.onVerifySuccess - Callback upon successful verification
 * @param {() => void} [props.onResend] - Optional resend OTP handler
 * @param {number} [props.initialSeconds=600] - Expiry countdown duration in seconds (10 mins)
 */
export function OtpVerification({
  email,
  onVerifySuccess,
  onResend,
  initialSeconds = 600,
}) {
  const [digits, setDigits] = useState(['', '', '', '', '', '']);
  const [timeLeft, setTimeLeft] = useState(initialSeconds);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const inputRefs = useRef([]);

  useEffect(() => {
    if (timeLeft <= 0) return;
    const interval = setInterval(() => {
      setTimeLeft((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(interval);
  }, [timeLeft]);

  function handleChange(index, value) {
    const cleanValue = value.replace(/\D/g, '').slice(-1);
    const nextDigits = [...digits];
    nextDigits[index] = cleanValue;
    setDigits(nextDigits);
    setError('');

    if (cleanValue && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  }

  function handleKeyDown(index, e) {
    if (e.key === 'Backspace' && !digits[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  }

  function handlePaste(e) {
    e.preventDefault();
    const pastedText = e.clipboardData.getData('text') || '';
    const numericChars = pastedText.replace(/\D/g, '').slice(0, 6).split('');
    if (!numericChars.length) return;

    const nextDigits = [...digits];
    numericChars.forEach((char, i) => {
      if (i < 6) nextDigits[i] = char;
    });
    setDigits(nextDigits);
    setError('');

    const nextFocusIndex = Math.min(numericChars.length, 5);
    inputRefs.current[nextFocusIndex]?.focus();
  }

  async function handleSubmit(e) {
    if (e) e.preventDefault();
    const code = digits.join('');
    if (code.length !== 6) {
      setError('PLEASE ENTER ALL 6 DIGITS');
      return;
    }

    if (timeLeft <= 0) {
      setError('OTP CODE HAS EXPIRED. PLEASE REQUEST A NEW CODE.');
      return;
    }

    setIsSubmitting(true);
    setError('');

    try {
      await api(API_ROUTES.AUTH.VERIFY_OTP, {
        method: 'POST',
        body: { email, code },
      });

      if (typeof onVerifySuccess === 'function') {
        onVerifySuccess();
      }
    } catch (err) {
      setError(err.detail || err.message || 'VERIFICATION FAILED');
    } finally {
      setIsSubmitting(false);
    }
  }

  const minutes = Math.floor(timeLeft / 60);
  const seconds = timeLeft % 60;
  const formattedTime = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;

  return (
    <div className="flex flex-col space-y-6">
      <div className="border-b-2 border-swiss-black pb-3">
        <h2 className="text-2xl font-black uppercase tracking-tight text-swiss-black">
          SECURITY VERIFICATION
        </h2>
        <p className="text-xs font-bold uppercase tracking-wider text-neutral-500 mt-1">
          ENTER 6-DIGIT CODE TRANSMITTED TO: <span className="text-swiss-black">{email}</span>
        </p>
      </div>

      {error && (
        <div
          data-testid="otp-error"
          className="p-3 border-2 border-swiss-black bg-swiss-red text-swiss-white text-xs font-bold uppercase tracking-wider"
        >
          {error}
        </div>
      )}

      {/* 6-Digit Segmented Box Matrix */}
      <div className="flex justify-between gap-2" onPaste={handlePaste}>
        {digits.map((digit, idx) => (
          <input
            key={idx}
            ref={(el) => (inputRefs.current[idx] = el)}
            type="text"
            inputMode="numeric"
            pattern="[0-9]*"
            maxLength={1}
            value={digit}
            onChange={(e) => handleChange(idx, e.target.value)}
            onKeyDown={(e) => handleKeyDown(idx, e)}
            disabled={isSubmitting || timeLeft <= 0}
            aria-label={`Digit ${idx + 1}`}
            className="w-11 h-14 sm:w-14 sm:h-16 text-center text-xl sm:text-2xl font-mono font-bold uppercase rounded-none border-2 border-swiss-black bg-swiss-white focus:outline-none focus:ring-2 focus:ring-swiss-black focus:ring-offset-2 transition-all select-none"
          />
        ))}
      </div>

      {/* Expiry Countdown & Resend Option */}
      <div className="flex items-center justify-between border-t-2 border-b-2 border-swiss-black py-2 text-xs font-mono font-bold uppercase tracking-wider">
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 ${timeLeft > 0 ? 'bg-swiss-black' : 'bg-swiss-red'}`} />
          <span>
            {timeLeft > 0 ? `EXPIRATION: ${formattedTime}` : 'CODE EXPIRED'}
          </span>
        </div>

        {onResend && (
          <button
            type="button"
            onClick={onResend}
            disabled={isSubmitting}
            className="hover:underline hover:text-swiss-red transition-colors cursor-pointer disabled:opacity-50"
          >
            RESEND CODE ↺
          </button>
        )}
      </div>

      <SwissButton
        type="button"
        variant="primary"
        onClick={handleSubmit}
        disabled={isSubmitting || digits.join('').length !== 6 || timeLeft <= 0}
        className="w-full h-12"
      >
        {isSubmitting ? 'VERIFYING CODE...' : 'VERIFY & COMPLETE AUTHENTICATION →'}
      </SwissButton>
    </div>
  );
}
