import React, { useState, useEffect, useRef } from 'react';

/**
 * Cache-Aside Search Input with Slash Hotkey and 300ms Debounce.
 * Conforms to Ponytail Ultra: native React hooks, standard Web APIs, zero state machine bloat.
 *
 * @param {object} props
 * @param {(query: string) => void} props.onSearch - Debounced search callback
 * @param {string} [props.origin] - Cache origin tag ('LOCAL CACHE' | 'UPSTREAM FETCH')
 * @param {string} [props.placeholder='SEARCH INTEL DISPATCHES (PRESS / TO FOCUS)'] - Placeholder
 * @param {string} [props.className=''] - Additional wrapper classes
 */
export function SearchBar({
  onSearch,
  origin,
  placeholder = 'SEARCH INTEL DISPATCHES (PRESS / TO FOCUS)',
  className = '',
}) {
  const [query, setQuery] = useState('');
  const inputRef = useRef(null);
  const debounceTimerRef = useRef(null);

  useEffect(() => {
    function handleGlobalKeyDown(e) {
      if (e.key === '/') {
        const activeTag = document.activeElement?.tagName?.toLowerCase();
        if (activeTag === 'input' || activeTag === 'textarea' || document.activeElement?.isContentEditable) {
          return;
        }
        e.preventDefault();
        inputRef.current?.focus();
      }
    }

    document.addEventListener('keydown', handleGlobalKeyDown);
    return () => {
      document.removeEventListener('keydown', handleGlobalKeyDown);
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  function handleInputChange(e) {
    const rawVal = e.target.value;
    setQuery(rawVal);

    // Security Gate: Sanitize HTML tags from query
    const sanitized = rawVal.replace(/<[^>]*>?/gm, '');

    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    debounceTimerRef.current = setTimeout(() => {
      if (typeof onSearch === 'function') {
        onSearch(sanitized);
      }
    }, 300);
  }

  function handleInputKeyDown(e) {
    if (e.key === 'Escape') {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
      setQuery('');
      inputRef.current?.blur();
      if (typeof onSearch === 'function') {
        onSearch('');
      }
    }
  }

  function handleClear() {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    setQuery('');
    inputRef.current?.focus();
    if (typeof onSearch === 'function') {
      onSearch('');
    }
  }

  return (
    <div
      className={`w-full border-2 border-swiss-black bg-swiss-white px-3 py-2 flex items-center gap-3 focus-within:ring-2 focus-within:ring-swiss-black transition-all ${className}`}
    >
      <label
        htmlFor="swiss-search-input"
        className="text-xs font-mono font-bold uppercase tracking-wider text-swiss-black select-none whitespace-nowrap"
      >
        SEARCH //
      </label>

      <input
        ref={inputRef}
        id="swiss-search-input"
        type="text"
        value={query}
        onChange={handleInputChange}
        onKeyDown={handleInputKeyDown}
        placeholder={placeholder}
        aria-label="Search"
        className="flex-1 bg-transparent border-0 outline-none text-sm text-swiss-black font-mono placeholder:text-neutral-400 focus:outline-none focus:ring-0"
      />

      {query && (
        <button
          type="button"
          onClick={handleClear}
          aria-label="Clear search"
          className="text-xs font-mono font-bold text-neutral-500 hover:text-swiss-red uppercase px-1 cursor-pointer select-none"
        >
          [CLEAR ✕]
        </button>
      )}

      {origin && (
        <span
          data-testid="search-origin-badge"
          className="text-[10px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 border border-swiss-black bg-neutral-100 text-swiss-black select-none whitespace-nowrap"
        >
          {origin}
        </span>
      )}
    </div>
  );
}
