import React from 'react';
import { sanitizeUrl } from '../../lib/constants.js';

/**
 * Standard Swiss Grid Article Card.
 * Conforms to Ponytail Ultra: zero state machine, pure functional props, standard HTML/CSS.
 *
 * @param {object} props
 * @param {object} props.article - Article data object
 * @param {number} [props.index=2] - Visual numeral index
 * @param {(article: object) => void} [props.onToggleBookmark] - Bookmark toggle callback
 * @param {(article: object) => void} [props.onToggleRead] - Read status toggle callback
 * @param {(article: object) => void} [props.onShare] - Share link callback
 * @param {string} [props.className=''] - Custom container classes
 */
export function ArticleCard({
  article,
  index = 2,
  onToggleBookmark,
  onToggleRead,
  onShare,
  className = '',
}) {
  if (!article) return null;

  const safeUrl = sanitizeUrl(article.url) || '#';
  const safeImageUrl = sanitizeUrl(article.image_url);
  const formattedIndex = String(index).padStart(2, '0');

  return (
    <article
      className={`border-2 border-swiss-black bg-swiss-white p-5 sm:p-6 flex flex-col justify-between select-none ${
        article.is_read ? 'bg-neutral-50' : ''
      } ${className}`}
    >
      <div>
        {/* Card Header & Numeral Index */}
        <div className="flex items-baseline justify-between border-b border-neutral-200 pb-2 mb-3">
          <span className="text-2xl sm:text-3xl font-black font-mono tracking-tighter text-swiss-black">
            {formattedIndex}
          </span>
          <div className="flex items-center gap-2">
            {article.is_bookmarked && (
              <span className="bg-swiss-black text-swiss-white text-[10px] font-mono font-bold uppercase px-1.5 py-0.5">
                ★ BOOKMARKED
              </span>
            )}
            {article.is_read && (
              <span className="bg-neutral-200 text-neutral-600 text-[10px] font-mono font-bold uppercase px-1.5 py-0.5">
                [READ]
              </span>
            )}
          </div>
        </div>

        {/* Optional Image Preview */}
        {safeImageUrl && (
          <div className="w-full aspect-[16/10] overflow-hidden border border-swiss-black bg-neutral-100 mb-4">
            <img
              src={safeImageUrl}
              alt={article.title || 'Story visual'}
              className="w-full h-full object-cover grayscale contrast-125 hover:grayscale-0 transition-all duration-200"
            />
          </div>
        )}

        {/* Headline Link */}
        <h3
          className={`text-lg sm:text-xl font-black uppercase tracking-tight leading-snug mb-3 hover:underline underline-offset-2 ${
            article.is_read ? 'text-neutral-400' : 'text-swiss-black'
          }`}
        >
          <a
            href={safeUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="no-underline text-inherit"
          >
            {article.title}
          </a>
        </h3>

        {/* Abstract */}
        {article.description && (
          <p className="text-xs text-neutral-600 line-clamp-3 leading-relaxed mb-4">
            {article.description}
          </p>
        )}
      </div>

      {/* Card Footer: Metadata and Action Controls */}
      <div className="pt-3 border-t border-neutral-300 flex flex-wrap items-center justify-between gap-2 mt-auto">
        <div className="text-[11px] font-mono font-bold uppercase tracking-wider text-neutral-500">
          {article.source || 'WIRE'} · {article.published_at || 'DISPATCH'}
        </div>

        <div className="flex items-center gap-1.5">
          {onToggleBookmark && (
            <button
              type="button"
              onClick={() => onToggleBookmark(article)}
              aria-label={article.is_bookmarked ? 'Remove Bookmark' : 'Bookmark Article'}
              className={`px-2 py-1 text-[11px] font-bold uppercase tracking-wider border border-swiss-black transition-colors cursor-pointer ${
                article.is_bookmarked
                  ? 'bg-swiss-black text-swiss-white'
                  : 'bg-swiss-white text-swiss-black hover:bg-neutral-100'
              }`}
            >
              {article.is_bookmarked ? 'SAVED' : 'SAVE'}
            </button>
          )}

          {onToggleRead && (
            <button
              type="button"
              onClick={() => onToggleRead(article)}
              aria-label={article.is_read ? 'Mark as Unread' : 'Mark as Read'}
              className={`px-2 py-1 text-[11px] font-bold uppercase tracking-wider border border-swiss-black transition-colors cursor-pointer ${
                article.is_read
                  ? 'bg-neutral-200 text-neutral-500'
                  : 'bg-swiss-white text-swiss-black hover:bg-neutral-100'
              }`}
            >
              {article.is_read ? 'READ ✓' : 'MARK READ'}
            </button>
          )}

          {onShare && (
            <button
              type="button"
              onClick={() => onShare(article)}
              aria-label="Share Article"
              className="px-2 py-1 text-[11px] font-bold uppercase tracking-wider border border-swiss-black bg-swiss-white text-swiss-black hover:bg-swiss-black hover:text-swiss-white transition-colors cursor-pointer"
            >
              ↗
            </button>
          )}
        </div>
      </div>
    </article>
  );
}
