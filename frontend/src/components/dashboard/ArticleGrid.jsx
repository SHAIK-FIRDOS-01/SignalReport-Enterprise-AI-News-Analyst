import React from 'react';
import { HeroArticle } from './HeroArticle.jsx';
import { ArticleCard } from './ArticleCard.jsx';
import { SwissButton } from '../ui/SwissButton.jsx';

/**
 * Asymmetric Editorial Article Feed Grid.
 * Conforms to Ponytail Ultra: zero state machine bloat, native responsive CSS Grid.
 *
 * @param {object} props
 * @param {Array<object>} props.articles - Array of article objects
 * @param {boolean} [props.isLoading=false] - Feed loading state flag
 * @param {boolean} [props.hasMore=false] - Keyset pagination availability flag
 * @param {() => void} [props.onLoadMore] - Pagination trigger callback
 * @param {(article: object) => void} [props.onToggleBookmark] - Bookmark callback
 * @param {(article: object) => void} [props.onToggleRead] - Read toggle callback
 * @param {(article: object) => void} [props.onShare] - Share trigger callback
 * @param {string} [props.className=''] - Custom container classes
 */
export function ArticleGrid({
  articles = [],
  isLoading = false,
  hasMore = false,
  onLoadMore,
  onToggleBookmark,
  onToggleRead,
  onShare,
  onAnalyze,
  className = '',
}) {
  const safeArticles = Array.isArray(articles) ? articles : (articles?.items || []);

  if (isLoading && safeArticles.length === 0) {
    return (
      <div className={`w-full p-12 border-2 border-swiss-black bg-swiss-white text-center select-none ${className}`}>
        <div className="flex items-center justify-center gap-3">
          <span className="w-3 h-3 bg-swiss-red animate-pulse inline-block" />
          <span className="text-sm font-mono font-bold uppercase tracking-widest text-swiss-black">
            SYNCHRONIZING FEED // EDITORIAL WIRE...
          </span>
        </div>
      </div>
    );
  }

  if (safeArticles.length === 0) {
    return (
      <div className={`w-full p-12 border-2 border-swiss-black bg-swiss-white text-center select-none ${className}`}>
        <p className="text-sm font-mono font-bold uppercase tracking-widest text-neutral-500">
          NO DISPATCHES FOUND FOR ACTIVE FILTER // FEED EMPTY
        </p>
      </div>
    );
  }

  const [leadStory, ...secondaryStories] = safeArticles;

  return (
    <div className={`w-full flex flex-col ${className}`}>
      {/* Primary Hero Lead Story */}
      <HeroArticle
        article={leadStory}
        onToggleBookmark={onToggleBookmark}
        onToggleRead={onToggleRead}
        onShare={onShare}
        onAnalyze={onAnalyze}
      />

      {/* Multi-Column Grid for Secondary Feed Dispatches */}
      {secondaryStories.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mt-6">
          {secondaryStories.map((article, index) => (
            <ArticleCard
              key={article.id || index}
              article={article}
              index={index + 2}
              onToggleBookmark={onToggleBookmark}
              onToggleRead={onToggleRead}
              onShare={onShare}
              onAnalyze={onAnalyze}
            />
          ))}
        </div>
      )}

      {/* Keyset Pagination Control */}
      {hasMore && (
        <div className="mt-8 flex justify-center">
          <SwissButton
            type="button"
            variant="primary"
            onClick={onLoadMore}
            className="w-full sm:w-auto px-12 h-12"
          >
            LOAD MORE HEADLINES ↓
          </SwissButton>
        </div>
      )}
    </div>
  );
}
