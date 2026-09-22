import { useSyncExternalStore, useEffect, useRef } from 'react';

/**
 * Event listener subscriber function for browser online/offline status.
 *
 * @param {() => void} callback - Event listener subscriber
 * @returns {() => void} Cleanup function unbinding listeners
 */
function subscribeNetwork(callback) {
  if (typeof window === 'undefined') {
    return () => {};
  }
  window.addEventListener('online', callback);
  window.addEventListener('offline', callback);
  return () => {
    window.removeEventListener('online', callback);
    window.removeEventListener('offline', callback);
  };
}

/**
 * Snapshot getter extracting current navigator.onLine state.
 *
 * @returns {boolean} True if client is online, false otherwise
 */
function getNetworkSnapshot() {
  return typeof navigator !== 'undefined' ? navigator.onLine : true;
}

/**
 * Fallback server snapshot getter for SSR environments.
 *
 * @returns {boolean} True by default
 */
function getNetworkServerSnapshot() {
  return true;
}

/**
 * React 18 hook providing tear-free, reactive network connectivity status.
 * Leverages useSyncExternalStore with zero third-party state managers.
 *
 * @returns {boolean} Current online connectivity status
 */
export function useNetworkStatus() {
  return useSyncExternalStore(subscribeNetwork, getNetworkSnapshot, getNetworkServerSnapshot);
}

/**
 * Hook detecting document visibility changes to trigger data re-synchronization
 * when a user returns to a backgrounded or sleeping tab after exceeding staleTimeMs.
 *
 * @param {() => void} onWakeup - Callback invoked when returning to visible state
 * @param {number} [staleTimeMs=0] - Minimum background elapsed time in ms before invoking onWakeup
 */
export function useTabWakeup(onWakeup, staleTimeMs = 0) {
  const savedCallback = useRef(onWakeup);
  const lastHiddenTimeRef = useRef(null);

  useEffect(() => {
    savedCallback.current = onWakeup;
  }, [onWakeup]);

  useEffect(() => {
    if (typeof document === 'undefined') {
      return;
    }

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'hidden') {
        lastHiddenTimeRef.current = Date.now();
      } else if (document.visibilityState === 'visible') {
        const hiddenAt = lastHiddenTimeRef.current;
        const now = Date.now();
        if (hiddenAt !== null) {
          const elapsed = now - hiddenAt;
          if (elapsed >= staleTimeMs) {
            savedCallback.current?.();
          }
        }
        lastHiddenTimeRef.current = null;
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [staleTimeMs]);
}

/**
 * Unified network synchronization hook combining live connectivity tracking
 * with tab reactivation triggers.
 *
 * @param {() => void} [onWakeup] - Optional callback triggered when returning to stale tab
 * @param {number} [staleTimeMs=0] - Background duration threshold in milliseconds
 * @returns {{ isOnline: boolean }} Reactive connectivity object
 */
export function useNetworkSync(onWakeup, staleTimeMs = 0) {
  const isOnline = useNetworkStatus();
  useTabWakeup(onWakeup, staleTimeMs);
  return { isOnline };
}
