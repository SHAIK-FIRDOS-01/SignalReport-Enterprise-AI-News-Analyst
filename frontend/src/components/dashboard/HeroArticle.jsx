import React from 'react';
import { sanitizeUrl } from '../../lib/constants.js';

/**
 * Swiss Brutalist Hero Lead Article Component.
 * Conforms to Ponytail Ultra: zero state machine, pure functional props, standard HTML/CSS.
 *
 * @param {object} props
 * @param {object} props.article - Article data object
 * @param {(article: object) => void} [props.onToggleBookmark] - Bookmark action callback
 * @param {(article: object) => void} [props.onToggleRead] - Read status toggle callback
 * @param {(article: object) => void} [props.onShare] - Share link copy/modal callback
 * @param {string} [props.className=''] - Custom styling classes
 */
export function HeroArticle({
  article,
  onToggleBookmark,
  onToggleRead,
  onShare,
  onAnalyze,
  className = '',
}) {
  if (!article) return null;

  const safeImageUrl = sanitizeUrl(article.image_url);
  const safeOutboundUrl = sanitizeUrl(article.url) || '#';

  return (
    <article
      className={`border-2 border-swiss-black bg-swiss-white p-6 sm:p-8 flex flex-col justify-between select-none ${
        article.is_read ? 'opacity-80' : ''
      } ${className}`}
    >
      <div>
        {/* Editorial Index & Category Meta */}
        <div className="flex items-baseline justify-between border-b border-neutral-200 pb-3 mb-4">
          <span className="text-4xl sm:text-5xl font-black font-mono tracking-tighter text-swiss-black leading-none">
            01 // LEAD
          </span>
          <div className="flex items-center gap-2 text-xs font-mono font-bold uppercase tracking-wider text-neutral-500">
            <span>{article.category || 'INTELLIGENCE'}</span>
            <span>·</span>
            <span>{article.published_at || 'RECENT'}</span>
          </div>
        </div>

        {/* Hero Visual Media Box */}
        <div className="w-full aspect-[16/9] sm:aspect-[21/9] overflow-hidden border-2 border-swiss-black bg-neutral-100 mb-6 flex items-center justify-center">
          {safeImageUrl ? (
            <img
              src={safeImageUrl}
              alt={article.title || 'Lead story illustration'}
              className="w-full h-full object-cover grayscale contrast-125 hover:grayscale-0 transition-all duration-300"
            />
          ) : (
            <div
              data-testid="hero-image-placeholder"
              className="w-full h-full flex flex-col items-center justify-center bg-neutral-200 text-neutral-600 font-mono text-xs font-bold uppercase tracking-widest p-4 text-center"
            >
              <span>[NO VISUAL REPORT ARCHIVED]</span>
              <span className="text-[10px] text-neutral-400 mt-1">
                REF: {article.id || 'SEC-01'}
              </span>
            </div>
          )}
        </div>

        {/* Lead Headline */}
        <h2 className="text-2xl sm:text-4xl lg:text-5xl font-black uppercase tracking-tight text-swiss-black leading-tight mb-4 hover:underline underline-offset-4">
          <a
            href={safeOutboundUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-swiss-black no-underline hover:text-neutral-800"
          >
            {article.title}
          </a>
        </h2>

        {/* Lead Description Abstract */}
        {article.description && (
          <p className="text-sm sm:text-base text-neutral-700 leading-relaxed font-sans max-w-3xl mb-6">
            {article.description}
          </p>
        )}
      </div>

      {/* Footer Meta & Quick Action Triggers */}
      <div className="pt-4 border-t-2 border-swiss-black flex flex-wrap items-center justify-between gap-4">
        <div className="text-xs font-mono font-bold uppercase tracking-wider text-neutral-600">
          SOURCE: <span className="text-swiss-black">{article.source || 'WIRE SERVICE'}</span>
        </div>

        <div className="flex items-center gap-2">
          {onAnalyze && (
            <button
              type="button"
              onClick={() => onAnalyze(article)}
              aria-label="AI Intelligence Brief"
              className="px-3 py-1.5 text-xs font-bold uppercase tracking-wider border-2 border-swiss-black bg-swiss-black text-swiss-white hover:bg-neutral-800 transition-colors cursor-pointer flex items-center gap-1.5"
            >
              <span>⚡</span> AI BRIEF
            </button>
          )}

          {onToggleBookmark && (
            <button
              type="button"
              onClick={() => onToggleBookmark(article)}
              aria-label={article.is_bookmarked ? 'Remove Bookmark' : 'Bookmark Article'}
              className={`px-3 py-1.5 text-xs font-bold uppercase tracking-wider border-2 border-swiss-black transition-colors cursor-pointer ${
                article.is_bookmarked
                  ? 'bg-swiss-black text-swiss-white'
                  : 'bg-swiss-white text-swiss-black hover:bg-neutral-100'
              }`}
            >
              {article.is_bookmarked ? '✓ BOOKMARKED' : '+ BOOKMARK'}
            </button>
          )}

          {onToggleRead && (
            <button
              type="button"
              onClick={() => onToggleRead(article)}
              aria-label={article.is_read ? 'Mark as Unread' : 'Mark as Read'}
              className={`px-3 py-1.5 text-xs font-bold uppercase tracking-wider border-2 border-swiss-black transition-colors cursor-pointer ${
                article.is_read
                  ? 'bg-neutral-200 text-neutral-600'
                  : 'bg-swiss-white text-swiss-black hover:bg-neutral-100'
              }`}
            >
              {article.is_read ? '✓ READ' : 'MARK READ'}
            </button>
          )}

          {onShare && (
            <button
              type="button"
              onClick={() => onShare(article)}
              aria-label="Share Article"
              className="px-3 py-1.5 text-xs font-bold uppercase tracking-wider border-2 border-swiss-black bg-swiss-white text-swiss-black hover:bg-swiss-black hover:text-swiss-white transition-colors cursor-pointer"
            >
              SHARE ↗
            </button>
          )}
        </div>
      </div>
    </article>
  );
}
