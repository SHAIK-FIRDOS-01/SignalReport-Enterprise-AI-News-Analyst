import React, { useState, useEffect } from 'react';
import { api } from '../../lib/api.js';
import { sanitizeUrl } from '../../lib/constants.js';

/**
 * Saved Articles (Bookmarks) Slide-Over Drawer.
 * Conforms to Ponytail Ultra: native React hooks, standard Web APIs, zero state machine bloat.
 *
 * @param {object} props
 * @param {boolean} props.isOpen - Drawer open/closed visibility flag
 * @param {() => void} props.onClose - Close trigger callback
 * @param {Array<object>} [props.bookmarks=[]] - Array of bookmarked article objects
 * @param {(id: string|number) => void} [props.onRemoveBookmark] - Removal callback
 */
export function BookmarksDrawer({
  isOpen,
  onClose,
  bookmarks = [],
  onRemoveBookmark,
}) {
  const [items, setItems] = useState(bookmarks);

  useEffect(() => {
    setItems(bookmarks);
  }, [bookmarks]);

  useEffect(() => {
    if (!isOpen) return;

    function handleKeyDown(e) {
      if (e.key === 'Escape') {
        onClose();
      }
    }

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  async function handleRemove(id) {
    // Optimistic UI removal
    const previousItems = [...items];
    setItems((prev) => prev.filter((item) => item.id !== id));

    if (typeof onRemoveBookmark === 'function') {
      onRemoveBookmark(id);
    }

    try {
      await api(`/api/v1/news/bookmarks/${id}`, { method: 'DELETE' });
    } catch {
      // Revert if API fails
      setItems(previousItems);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/40 select-none">
      {/* Click-away backdrop overlay */}
      <div className="flex-1 cursor-pointer" onClick={onClose} />

      {/* Slide-over Drawer Panel with 2px Solid Black Left Boundary */}
      <aside className="w-full max-w-md h-full bg-swiss-white border-l-2 border-swiss-black flex flex-col shadow-2xl">
        {/* Drawer Header */}
        <div className="p-6 border-b-2 border-swiss-black flex items-center justify-between">
          <div>
            <h2 className="text-xl font-black uppercase tracking-tight text-swiss-black">
              SAVED DISPATCHES // ARCHIVE
            </h2>
            <p className="text-xs font-mono font-bold uppercase tracking-wider text-neutral-500">
              RETAINED INTELLIGENCE DOSSIERS ({items.length})
            </p>
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Close Bookmarks Drawer"
            className="text-xs font-mono font-bold uppercase tracking-wider px-2 py-1 border border-swiss-black hover:bg-swiss-black hover:text-swiss-white transition-colors cursor-pointer"
          >
            [CLOSE ✕]
          </button>
        </div>

        {/* Drawer Body / Article List */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {items.length === 0 ? (
            <div className="p-8 border border-neutral-200 text-center text-xs font-mono font-bold uppercase tracking-widest text-neutral-500">
              NO SAVED ARTICLES // ARCHIVE EMPTY
            </div>
          ) : (
            items.map((article, idx) => {
              const safeUrl = sanitizeUrl(article.url) || '#';
              const prefix = String(idx + 1).padStart(2, '0');

              return (
                <div
                  key={article.id || idx}
                  className="p-4 border border-swiss-black bg-swiss-white flex flex-col justify-between gap-3"
                >
                  <div>
                    <div className="flex items-center justify-between text-[11px] font-mono text-neutral-500 uppercase mb-1">
                      <span>{prefix} // DOSSIER</span>
                      <span>{article.source || 'WIRE'}</span>
                    </div>

                    <h3 className="text-sm font-bold uppercase text-swiss-black hover:underline leading-snug">
                      <a
                        href={safeUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="no-underline text-inherit"
                      >
                        {article.title}
                      </a>
                    </h3>
                  </div>

                  <div className="flex items-center justify-between pt-2 border-t border-neutral-200">
                    <span className="text-[10px] font-mono text-neutral-500">
                      {article.published_at || 'ARCHIVED'}
                    </span>

                    <button
                      type="button"
                      onClick={() => handleRemove(article.id)}
                      aria-label="Remove Bookmark"
                      className="text-[11px] font-bold uppercase tracking-wider text-swiss-red hover:underline cursor-pointer"
                    >
                      REMOVE [✕]
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </aside>
    </div>
  );
}
