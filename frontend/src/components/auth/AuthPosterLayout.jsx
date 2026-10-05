import React, { useState, useEffect } from 'react';

/**
 * Swiss Auth Poster Split Frame.
 * Conforms to Ponytail Ultra: native React hooks, standard Web APIs, zero state machines.
 *
 * @param {object} props
 * @param {React.ReactNode} props.children - Auth form content slot
 * @param {string} [props.subtitle='GLOBAL NEWS & EDITORIAL ARCHIVE'] - Editorial subtitle
 * @param {string} [props.edition='EDITION 2026 // VOLUME 4.2'] - System edition identifier
 * @param {string} [props.className=''] - Custom root class overrides
 */
export function AuthPosterLayout({
  children,
  subtitle = 'GLOBAL NEWS & EDITORIAL ARCHIVE',
  edition = 'EDITION 2026 // VOLUME 4.2',
  className = '',
}) {
  const [istTime, setIstTime] = useState(() => getFormattedIstTime());

  useEffect(() => {
    const timer = setInterval(() => {
      setIstTime(getFormattedIstTime());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  function getFormattedIstTime() {
    try {
      const timeStr = new Intl.DateTimeFormat('en-GB', {
        timeZone: 'Asia/Kolkata',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
      }).format(new Date());
      return `${timeStr} IST`;
    } catch {
      return `${new Date().toLocaleTimeString()} IST`;
    }
  }

  return (
    <div
      className={`w-full max-w-6xl mx-auto border-2 border-swiss-black bg-swiss-white grid grid-cols-1 lg:grid-cols-12 rounded-none overflow-hidden ${className}`}
    >
      {/* Left Column: Editorial Brand Stack & Publication Context */}
      <div className="lg:col-span-6 p-8 lg:p-12 flex flex-col justify-between border-b-2 lg:border-b-0 lg:border-r-2 border-swiss-black bg-swiss-white select-none">
        <div>
          <div className="flex items-center gap-2 mb-6">
            <span className="w-3 h-3 bg-swiss-red inline-block" />
            <span className="text-xs font-mono font-bold uppercase tracking-widest text-swiss-black">
              EDITORIAL ANALYST PORTAL
            </span>
          </div>
          <h1 className="text-4xl lg:text-5xl font-black uppercase tracking-tighter text-swiss-black leading-none mb-3">
            SIGNAL / REPORT // INTELLIGENCE
          </h1>
          <p className="text-xs font-bold uppercase tracking-widest text-neutral-600 mb-6">
            {subtitle}
          </p>
          <div className="inline-block border border-swiss-black px-3 py-1 text-xs font-bold uppercase tracking-wider text-swiss-black bg-neutral-100">
            {edition}
          </div>
        </div>

        <div className="my-12">
          <div className="text-7xl lg:text-9xl font-black tracking-tighter leading-none bg-[linear-gradient(180deg,#C81E1E_0%,#000000_100%)] bg-clip-text text-transparent inline-block">
            24/7
          </div>
          <p className="text-xs font-mono text-neutral-500 uppercase tracking-widest mt-2">
            REAL-TIME SYNDICATION &amp; EDITORIAL WIRE
          </p>
        </div>

        <div className="pt-6 border-t-2 border-swiss-black flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
          <div>
            <span className="text-[10px] font-bold uppercase tracking-widest text-neutral-500 block">
              DESK TIME
            </span>
            <span
              data-testid="auth-poster-clock"
              className="text-xs font-mono font-bold uppercase tracking-widest text-swiss-black"
            >
              {istTime}
            </span>
          </div>
          <div className="sm:text-right">
            <span className="text-[10px] font-bold uppercase tracking-widest text-neutral-500 block">
              LOCATION
            </span>
            <span className="text-xs font-bold uppercase tracking-widest text-swiss-black">
              HYDERABAD, IN // NEWS DESK
            </span>
          </div>
        </div>
      </div>

      {/* Right Column: Dynamic Form Container Slot */}
      <div className="lg:col-span-6 p-8 lg:p-12 flex flex-col justify-center bg-swiss-white">
        {children}
      </div>
    </div>
  );
}
