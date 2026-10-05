import React, { useState, useEffect } from 'react';
import { api } from '../../lib/api.js';
import { API_ROUTES } from '../../lib/constants.js';

/**
 * AI Intelligence Analysis Modal.
 * Conforms to Ponytail Ultra: native React hooks, zero external state libraries.
 * Conforms to Security-Audit: strict JSON parsing, pure text DOM nodes, safe bounds.
 *
 * @param {object} props
 * @param {object|null} props.article - Selected article to analyze
 * @param {() => void} props.onClose - Close callback
 */
export function AiAnalysisModal({ article, onClose }) {
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!article) {
      setAnalysis(null);
      setError(null);
      return;
    }

    let isMounted = true;
    async function runAnalysis() {
      setLoading(true);
      setError(null);
      setAnalysis(null);

      try {
        const payload = {
          article_id: typeof article.id === 'number' ? article.id : null,
          title: article.title || '',
          description: article.description || '',
          content: article.content || article.description || '',
          source_name: article.source || '',
          category: article.category || 'GENERAL',
        };

        const result = await api(API_ROUTES.NEWS.ANALYZE, {
          method: 'POST',
          body: payload,
        });

        if (isMounted) {
          setAnalysis(result);
        }
      } catch (err) {
        if (isMounted) {
          setError(err?.message || 'Failed to generate intelligence brief from LLM service.');
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    runAnalysis();

    return () => {
      isMounted = false;
    };
  }, [article]);

  useEffect(() => {
    if (!article) return;

    function handleKeyDown(e) {
      if (e.key === 'Escape') {
        onClose();
      }
    }

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [article, onClose]);

  if (!article) return null;

  function handleCopy() {
    if (!analysis) return;
    const summaryText = [
      `SIGNALREPORT AI INTELLIGENCE BRIEF: ${article.title}`,
      `POSTURE: ${analysis.sentiment || 'NEUTRAL'} (${analysis.sentiment_rationale || ''})`,
      '',
      'EXECUTIVE TAKEAWAYS:',
      ...(analysis.executive_takeaways || []).map((t, idx) => `${idx + 1}. ${t}`),
      '',
      `STRATEGIC IMPACT: ${analysis.strategic_impact || 'N/A'}`,
      `ENTITIES: ${(analysis.key_entities || []).join(', ')}`,
      `MODEL: ${analysis.model || 'Groq LPU'}`,
    ].join('\n');

    if (navigator.clipboard) {
      navigator.clipboard.writeText(summaryText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    }
  }

  // Sentiment styling helper
  const sentiment = analysis?.sentiment?.toUpperCase() || 'NEUTRAL';
  let sentimentBadgeStyle = 'bg-neutral-200 text-neutral-800 border-neutral-400';
  if (sentiment === 'BULLISH') {
    sentimentBadgeStyle = 'bg-emerald-100 text-emerald-900 border-emerald-600';
  } else if (sentiment === 'BEARISH') {
    sentimentBadgeStyle = 'bg-rose-100 text-rose-900 border-rose-600';
  } else if (sentiment === 'VOLATILE') {
    sentimentBadgeStyle = 'bg-amber-100 text-amber-900 border-amber-600';
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 sm:p-6 select-none backdrop-blur-xs">
      {/* Click-away backdrop */}
      <div className="absolute inset-0" onClick={onClose} />

      {/* Modal Dialog Card */}
      <div className="relative w-full max-w-2xl max-h-[90vh] bg-swiss-white border-2 border-swiss-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] flex flex-col z-10 overflow-hidden">
        {/* Header */}
        <div className="p-5 border-b-2 border-swiss-black flex items-center justify-between bg-swiss-white">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 bg-swiss-red" />
            <h2 className="text-sm sm:text-base font-black uppercase tracking-tight text-swiss-black font-mono">
              AI INTELLIGENCE BRIEF // SIGNALREPORT AI ANALYST
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close Analysis Modal"
            className="text-xs font-mono font-bold uppercase tracking-wider px-2 py-1 border border-swiss-black hover:bg-swiss-black hover:text-swiss-white transition-colors cursor-pointer"
          >
            [CLOSE ✕]
          </button>
        </div>

        {/* Scrollable Content Body */}
        <div className="flex-1 overflow-y-auto p-5 sm:p-6 space-y-5">
          {/* Article Context Header */}
          <div className="border-b border-neutral-300 pb-4">
            <div className="text-[11px] font-mono font-bold uppercase tracking-wider text-neutral-500 mb-1">
              SOURCE: {article.source || 'WIRE'} · CATEGORY: {article.category || 'GENERAL'}
            </div>
            <h3 className="text-base sm:text-lg font-black uppercase tracking-tight text-swiss-black leading-snug">
              {article.title}
            </h3>
          </div>

          {/* Loading Indicator */}
          {loading && (
            <div className="py-12 flex flex-col items-center justify-center space-y-4 text-center">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 bg-swiss-black animate-ping" />
                <span className="w-3 h-3 bg-swiss-red animate-pulse" />
                <span className="w-3 h-3 bg-swiss-black animate-ping" />
              </div>
              <p className="text-xs font-mono font-bold uppercase tracking-widest text-swiss-black">
                SYNCHRONIZING WITH GROQ LPU ENGINE // GENERATING SIGNAL REPORT...
              </p>
              <p className="text-[11px] font-mono text-neutral-500">
                Direct in-context synthesis — Zero vector latency
              </p>
            </div>
          )}

          {/* Error State */}
          {error && !loading && (
            <div className="p-4 border-2 border-swiss-red bg-rose-50 text-rose-900 space-y-2">
              <div className="text-xs font-mono font-bold uppercase tracking-wider flex items-center gap-1.5 text-swiss-red">
                <span>⚠</span> ANALYSIS SERVICE NOTICE
              </div>
              <p className="text-xs font-mono">{error}</p>
            </div>
          )}

          {/* Analysis Results Display */}
          {analysis && !loading && (
            <div className="space-y-5">
              {/* Sentiment & Posture Banner */}
              <div className="p-4 border border-swiss-black bg-neutral-50 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-neutral-500 block mb-1">
                    MARKET SENTIMENT POSTURE
                  </span>
                  <p className="text-xs text-neutral-700 font-sans italic">
                    "{analysis.sentiment_rationale}"
                  </p>
                </div>
                <div
                  className={`px-3 py-1 text-xs font-mono font-black uppercase tracking-widest border shrink-0 text-center ${sentimentBadgeStyle}`}
                >
                  {sentiment}
                </div>
              </div>

              {/* Executive Takeaways */}
              <div>
                <h4 className="text-xs font-mono font-black uppercase tracking-wider text-swiss-black mb-2 flex items-center gap-1.5">
                  <span className="text-swiss-red">■</span> EXECUTIVE TAKEAWAYS
                </h4>
                <ul className="space-y-2">
                  {(analysis.executive_takeaways || []).map((takeaway, idx) => (
                    <li
                      key={idx}
                      className="p-3 border border-neutral-300 bg-swiss-white flex items-start gap-2.5 text-xs sm:text-sm text-neutral-800 leading-relaxed font-sans"
                    >
                      <span className="font-mono font-bold text-swiss-black shrink-0">
                        {String(idx + 1).padStart(2, '0')}.
                      </span>
                      <span>{takeaway}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Strategic Impact Callout */}
              {analysis.strategic_impact && (
                <div className="p-4 border-l-4 border-l-swiss-black border border-neutral-300 bg-neutral-50">
                  <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-neutral-600 block mb-1">
                    STRATEGIC & MACRO IMPACT
                  </span>
                  <p className="text-xs sm:text-sm text-swiss-black font-semibold leading-relaxed">
                    {analysis.strategic_impact}
                  </p>
                </div>
              )}

              {/* Key Entities Detected */}
              {Array.isArray(analysis.key_entities) && analysis.key_entities.length > 0 && (
                <div>
                  <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-neutral-500 block mb-2">
                    IDENTIFIED ENTITIES & ORGS
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {analysis.key_entities.map((entity, idx) => (
                      <span
                        key={idx}
                        className="px-2 py-0.5 text-[11px] font-mono font-bold uppercase tracking-wider bg-swiss-white border border-neutral-400 text-neutral-800"
                      >
                        {entity}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="p-4 border-t-2 border-swiss-black bg-neutral-50 flex flex-wrap items-center justify-between gap-3">
          <div className="text-[10px] font-mono text-neutral-500 uppercase tracking-wider flex items-center gap-2">
            <span>MODEL: <strong className="text-swiss-black">{analysis?.model || 'GROQ LPU'}</strong></span>
            {analysis?.requests_remaining !== undefined && (
              <span className="px-1.5 py-0.5 border border-neutral-400 bg-swiss-white text-swiss-black font-bold">
                QUOTA: {analysis.requests_used}/{analysis.quota_limit} ({analysis.requests_remaining} LEFT)
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            {analysis && (
              <button
                type="button"
                onClick={handleCopy}
                className="px-3 py-1 text-xs font-mono font-bold uppercase tracking-wider border border-swiss-black bg-swiss-white hover:bg-neutral-100 transition-colors cursor-pointer"
              >
                {copied ? '✓ COPIED BRIEF' : 'COPY REPORT BRIEF'}
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1 text-xs font-mono font-bold uppercase tracking-wider border border-swiss-black bg-swiss-black text-swiss-white hover:bg-neutral-800 transition-colors cursor-pointer"
            >
              DONE
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
