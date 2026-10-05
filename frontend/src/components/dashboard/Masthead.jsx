import React, { useState, useEffect } from 'react';
import { SwissBadge } from '../ui/SwissBadge.jsx';
import { SwissButton } from '../ui/SwissButton.jsx';
import { api } from '../../lib/api.js';
import { API_ROUTES } from '../../lib/constants.js';

/**
 * Editorial Masthead & Dynamic Edition Bar.
 * Conforms to Ponytail Ultra: native React hooks, standard Web APIs, zero state machine bloat.
 *
 * @param {object} props
 * @param {object|string} [props.user] - Authenticated operator details
 * @param {() => void} [props.onLogout] - Logout completion callback
 * @param {() => void} [props.onOpenBookmarks] - Optional trigger for bookmarks drawer
 * @param {number} [props.bookmarkCount=0] - Number of saved bookmarks
 */
export function Masthead({
  user,
  onLogout,
  onOpenBookmarks,
  bookmarkCount = 0,
}) {
  const [currentDateString, setCurrentDateString] = useState(() => getFormattedIstDate());
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const userEmail = typeof user === 'string' ? user : user?.email || 'analyst@signalreport.io';

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentDateString(getFormattedIstDate());
    }, 60000);
    return () => clearInterval(timer);
  }, []);

  function getFormattedIstDate() {
    try {
      const now = new Date();
      const day = new Intl.DateTimeFormat('en-GB', { day: '2-digit', timeZone: 'Asia/Kolkata' }).format(now);
      const month = new Intl.DateTimeFormat('en-GB', { month: 'long', timeZone: 'Asia/Kolkata' }).format(now).toUpperCase();
      const year = new Intl.DateTimeFormat('en-GB', { year: 'numeric', timeZone: 'Asia/Kolkata' }).format(now);
      return `${day} ${month} ${year} // HYDERABAD, IN`;
    } catch {
      return '19 SEPTEMBER 2026 // HYDERABAD, IN';
    }
  }

  async function handleLogoutClick() {
    if (isLoggingOut) return;
    setIsLoggingOut(true);
    try {
      await api(API_ROUTES.AUTH.LOGOUT, { method: 'POST' });
    } catch {
      // Proceed with client logout even if network request fails
    } finally {
      setIsLoggingOut(false);
      if (typeof onLogout === 'function') {
        onLogout();
      }
    }
  }

  return (
    <header className="w-full border-b-2 border-swiss-black bg-swiss-white select-none">
      {/* Top Editorial Ribbon */}
      <div className="max-w-7xl mx-auto px-4 py-3 flex flex-wrap items-center justify-between gap-4 border-b border-neutral-200">
        <div className="flex items-center gap-3">
          <span className="w-3 h-3 bg-swiss-red inline-block" />
          <span className="text-xs font-mono font-bold tracking-widest uppercase text-swiss-black">
            EDITORIAL WIRE · SIGNALREPORT / HYDERABAD
          </span>
        </div>

        <div className="flex items-center gap-4 text-xs font-mono">
          <span className="font-bold uppercase tracking-wider text-swiss-black">
            {userEmail.toUpperCase()}
          </span>

          {onOpenBookmarks && (
            <button
              type="button"
              onClick={onOpenBookmarks}
              className="flex items-center gap-1.5 px-2 py-1 border border-swiss-black hover:bg-swiss-black hover:text-swiss-white transition-colors cursor-pointer font-bold uppercase tracking-wider"
            >
              <span>SAVED BOOKMARKS</span>
              <span className="bg-swiss-red text-swiss-white px-1 text-[10px]">
                {bookmarkCount}
              </span>
            </button>
          )}

          <button
            type="button"
            onClick={handleLogoutClick}
            disabled={isLoggingOut}
            className="font-bold uppercase tracking-wider text-neutral-600 hover:text-swiss-red hover:underline transition-colors cursor-pointer disabled:opacity-50"
          >
            {isLoggingOut ? 'EXITING...' : 'LOG OUT'}
          </button>
        </div>
      </div>

      {/* Monumental Headline Bar */}
      <div className="max-w-7xl mx-auto px-4 py-6 flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-5xl sm:text-6xl lg:text-7xl font-black uppercase tracking-tighter text-swiss-black leading-none">
            SIGNAL REPORT<span className="text-swiss-red">.</span>
          </h1>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-neutral-500 mt-2">
            ENTERPRISE AI NEWS INTELLIGENCE &amp; ANALYTICAL REPORTS
          </p>
        </div>

        <div className="flex flex-col md:items-end gap-1">
          <div className="flex items-center gap-2">
            <SwissBadge live variant="default">
              FEED ACTIVE
            </SwissBadge>
            <SwissBadge variant="inverted">
              EDITION 42.09
            </SwissBadge>
          </div>
          <span className="text-xs font-mono font-bold uppercase tracking-widest text-swiss-black mt-1">
            {currentDateString}
          </span>
        </div>
      </div>
    </header>
  );
}
