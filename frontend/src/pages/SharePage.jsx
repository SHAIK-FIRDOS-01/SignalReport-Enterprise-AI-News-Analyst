import React, { useState, useEffect } from 'react';
import { api } from '../lib/api.js';
import { sanitizeUrl } from '../lib/constants.js';

/**
 * Public Shareable Article Landing Page.
 * Conforms to Ponytail Ultra: native React hooks, standard Web APIs, zero state machine bloat.
 *
 * @param {object} props
 * @param {string} props.shareToken - Public unauthenticated share token
 * @param {() => void} [props.onNavigateHome] - Optional return navigation handler
 */
export function SharePage({ shareToken, onNavigateHome }) {
  const [article, setArticle] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!shareToken) {
      setError('MISSING SHARE TOKEN IDENTIFIER');
      setIsLoading(false);
      return;
    }

    let isMounted = true;
    setIsLoading(true);

    api(`/api/v1/news/share/${shareToken}`)
      .then((data) => {
        if (!isMounted) return;
        setArticle(data);
        if (data?.title) {
          document.title = `${data.title} — SIGNAL REPORT`;
        }
      })
      .catch((err) => {
        if (!isMounted) return;
        setError(err.detail || '404 // REPORT NOT FOUND OR EXPIRED');
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [shareToken]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-swiss-white p-8 flex items-center justify-center select-none">
        <div className="p-8 border-2 border-swiss-black bg-swiss-white max-w-md w-full text-center">
          <div className="flex items-center justify-center gap-2 mb-2">
            <span className="w-2.5 h-2.5 bg-swiss-red animate-pulse" />
            <span className="text-xs font-mono font-bold uppercase tracking-widest text-swiss-black">
              RETRIEVING DISPATCH DOSSIER...
            </span>
          </div>
          <p className="text-[10px] font-mono text-neutral-400 uppercase">
            TOKEN: {shareToken}
          </p>
        </div>
      </div>
    );
  }

  if (error || !article) {
    return (
      <div className="min-h-screen bg-swiss-white p-8 flex items-center justify-center select-none">
        <div className="p-8 border-2 border-swiss-black bg-swiss-white max-w-lg w-full">
          <div className="flex items-center gap-2 mb-4">
            <span className="w-3 h-3 bg-swiss-red" />
            <h1 className="text-xl font-black uppercase tracking-tight text-swiss-black">
              404 // DOSSIER NOT FOUND
            </h1>
          </div>
          <p className="text-xs font-mono text-neutral-600 mb-6 uppercase">
            {error || 'THE REQUESTED REPORT TOKEN IS INVALID OR HAS BEEN REVOKED.'}
          </p>
          {onNavigateHome && (
            <button
              type="button"
              onClick={onNavigateHome}
              className="px-6 py-2 border-2 border-swiss-black bg-swiss-black text-swiss-white text-xs font-bold uppercase tracking-wider hover:bg-swiss-white hover:text-swiss-black transition-colors cursor-pointer"
            >
              ← RETURN TO NEWS FEED
            </button>
          )}
        </div>
      </div>
    );
  }

  const safeUrl = sanitizeUrl(article.url) || '#';
  const safeImageUrl = sanitizeUrl(article.image_url);

  return (
    <div className="min-h-screen bg-swiss-white flex flex-col justify-between">
      {/* Editorial Header */}
      <header className="border-b-2 border-swiss-black bg-swiss-white p-6">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div className="flex items-baseline gap-3">
            <span className="text-2xl font-black tracking-tighter text-swiss-black">
              SIGNAL REPORT<span className="text-swiss-red">.</span>
            </span>
            <span className="text-xs font-mono font-bold uppercase tracking-widest text-neutral-500 hidden sm:inline">
              // PUBLIC ARTICLE BRIEF
            </span>
          </div>

          {onNavigateHome && (
            <button
              type="button"
              onClick={onNavigateHome}
              className="text-xs font-bold uppercase tracking-wider border border-swiss-black px-3 py-1 hover:bg-swiss-black hover:text-swiss-white transition-colors cursor-pointer"
            >
              MAIN NEWS DESK →
            </button>
          )}
        </div>
      </header>

      {/* Main Article Document */}
      <main className="flex-1 max-w-5xl w-full mx-auto p-6 sm:p-12">
        <div className="border-2 border-swiss-black p-8 sm:p-12 bg-swiss-white flex flex-col space-y-8">
          {/* Metadata Ribbon */}
          <div className="flex flex-wrap items-center justify-between gap-4 border-b-2 border-swiss-black pb-4 text-xs font-mono font-bold uppercase tracking-wider">
            <div className="flex items-center gap-3">
              <span className="bg-swiss-black text-swiss-white px-2 py-0.5">
                {article.category || 'INTELLIGENCE'}
              </span>
              <span className="text-neutral-500">
                DISPATCHED: {article.published_at || 'RECENT'}
              </span>
            </div>
            <div className="text-neutral-600">
              SOURCE: <span className="text-swiss-black">{article.source_name || article.source || 'WIRE'}</span>
            </div>
          </div>

          {/* Headline */}
          <h1 className="text-3xl sm:text-5xl font-black uppercase tracking-tight text-swiss-black leading-tight">
            {article.title}
          </h1>

          {/* Abstract */}
          {article.description && (
            <p className="text-lg sm:text-xl font-bold text-neutral-800 leading-relaxed font-sans border-l-4 border-swiss-black pl-4">
              {article.description}
            </p>
          )}

          {/* Visual Image */}
          {safeImageUrl && (
            <div className="w-full aspect-[21/9] overflow-hidden border-2 border-swiss-black bg-neutral-100">
              <img
                src={safeImageUrl}
                alt={article.title}
                className="w-full h-full object-cover grayscale contrast-125"
              />
            </div>
          )}

          {/* Full Content Body */}
          {article.content && (
            <div className="text-sm sm:text-base text-neutral-800 leading-relaxed font-sans pt-4 space-y-4">
              <p>{article.content}</p>
            </div>
          )}

          {/* Outbound Link Footer */}
          <div className="pt-8 border-t-2 border-swiss-black flex flex-wrap items-center justify-between gap-4">
            <a
              href={safeUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-6 py-3 border-2 border-swiss-black bg-swiss-black text-swiss-white text-xs font-bold uppercase tracking-wider hover:bg-swiss-white hover:text-swiss-black transition-colors no-underline"
            >
              <span>READ ORIGINAL SOURCE</span>
              <span>→</span>
            </a>

            <span className="text-[10px] font-mono text-neutral-400 uppercase">
              SECURITY VERIFIED · PROTOCOL HTTPS ENFORCED
            </span>
          </div>
        </div>
      </main>

      {/* Editorial Footer */}
      <footer className="border-t-2 border-swiss-black p-6 bg-swiss-white text-center text-xs font-mono font-bold uppercase tracking-widest text-neutral-500 select-none">
        SIGNAL REPORT // INTELLIGENCE REGISTRY // STRICT ZERO TOKEN RETENTION
      </footer>
    </div>
  );
}
