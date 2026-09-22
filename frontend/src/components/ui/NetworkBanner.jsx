import React from 'react';
import { useNetworkStatus } from '../../hooks/useNetworkSync.js';

/**
 * Stark Swiss-styled offline status notification banner.
 * Mounts whenever the network drops or connectivity is lost.
 *
 * @param {object} props
 * @param {boolean} [props.isOnline] - Optional controlled connectivity override
 * @param {string} [props.className] - Optional custom CSS classes
 * @returns {JSX.Element|null} Banner element or null when online
 */
export function NetworkBanner({ isOnline: controlledIsOnline, className = '' }) {
  const detectedOnline = useNetworkStatus();
  const isOnline = controlledIsOnline !== undefined ? controlledIsOnline : detectedOnline;

  if (isOnline) {
    return null;
  }

  return (
    <div
      role="alert"
      data-testid="network-banner"
      className={`w-full bg-black text-white font-mono text-xs uppercase tracking-widest px-4 py-2 flex items-center justify-between border-b-2 border-red-600 z-50 select-none ${className}`}
    >
      <div className="flex items-center space-x-2">
        <span
          data-testid="network-banner-indicator"
          className="inline-block w-2 h-2 bg-red-600 animate-pulse"
        />
        <span className="font-bold tracking-widest">
          SYSTEM STATUS: OFFLINE // DISPLAYING CACHED HEADLINES
        </span>
      </div>
      <div className="hidden sm:block text-[10px] text-zinc-400 tracking-wider">
        LOCAL CACHE ACTIVE
      </div>
    </div>
  );
}
