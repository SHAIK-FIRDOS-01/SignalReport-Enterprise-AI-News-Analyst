import { useState, useEffect, useCallback } from 'react';
import { api } from '../lib/api.js';
import { API_ROUTES } from '../lib/constants.js';

/**
 * Executes a GET request with 2-stage exponential backoff retry for transient network errors.
 * Respects AbortSignal to immediately cancel sleep timers and in-flight retries when aborted.
 *
 * @param {() => Promise<any>} fetchFn - Fetch execution factory
 * @param {AbortSignal} signal - Cancellation signal
 * @param {number} [maxRetries=2] - Number of retry attempts after initial failure
 * @param {number} [baseDelayMs=200] - Base exponential backoff delay in milliseconds
 * @returns {Promise<any>}
 */
async function fetchWithBackoff(fetchFn, signal, maxRetries = 2, baseDelayMs = 200) {
  let attempt = 0;
  while (true) {
    if (signal.aborted) {
      const abortError = new Error('The user aborted a request.');
      abortError.name = 'AbortError';
      throw abortError;
    }

    try {
      return await fetchFn();
    } catch (err) {
      // Never retry on explicit cancellations or known offline states
      if (signal.aborted || err.name === 'AbortError' || err.code === 'CLIENT_OFFLINE') {
        throw err;
      }

      if (attempt < maxRetries) {
        attempt++;
        const delay = baseDelayMs * Math.pow(2, attempt - 1);
        await new Promise((resolve, reject) => {
          const timeoutId = setTimeout(resolve, delay);
          signal.addEventListener(
            'abort',
            () => {
              clearTimeout(timeoutId);
              const abortError = new Error('The user aborted a request.');
              abortError.name = 'AbortError';
              reject(abortError);
            },
            { once: true }
          );
        });
      } else {
        throw err;
      }
    }
  }
}

/**
 * Race-condition-free news feed and query search hook.
 * Strictly conforms to Ponytail Ultra: native React 18 hooks, AbortController lifecycle,
 * zero external state library dependencies.
 *
 * @param {object} [options={}]
 * @param {string} [options.category='ALL'] - Filter category
 * @param {string} [options.query=''] - Full-text search query string
 * @param {number} [options.limit=10] - Page size
 * @param {number} [options.retryBaseDelay=200] - Base delay for exponential backoff retries
 * @returns {object} Feed state, setters, and pagination controller
 */
export function useNewsFeed({
  category = 'ALL',
  query = '',
  limit = 10,
  retryBaseDelay = 200,
} = {}) {
  const [articles, setArticles] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [error, setError] = useState(null);
  const [hasMore, setHasMore] = useState(false);
  const [cursor, setCursor] = useState(null);
  const [searchOrigin, setSearchOrigin] = useState(null);
  const [refreshCounter, setRefreshCounter] = useState(0);

  const refetch = useCallback(() => {
    setRefreshCounter((c) => c + 1);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    let isCancelled = false;

    async function executeQuery() {
      setIsLoading(true);
      setError(null);

      const isSearch = Boolean(query && query.trim());
      const endpoint = isSearch
        ? `${API_ROUTES.NEWS.SEARCH}?q=${encodeURIComponent(query.trim())}&limit=${limit}`
        : `${API_ROUTES.NEWS.FEED}?limit=${limit}${category === 'ALL' ? '' : `&category=${category.toLowerCase()}`}`;

      try {
        const data = await fetchWithBackoff(
          () => api(endpoint, { signal: controller.signal }),
          controller.signal,
          2,
          retryBaseDelay
        );

        if (!isCancelled && !controller.signal.aborted) {
          const fetchedArticles = data?.items || data?.articles || (Array.isArray(data) ? data : []);
          setArticles(fetchedArticles);
          setHasMore(Boolean(data?.has_more));
          setCursor(data?.next_cursor || null);
          setSearchOrigin(data?.origin || null);
          setIsLoading(false);
        }
      } catch (err) {
        // Silently ignore aborted requests to prevent memory leaks / false error toasts
        if (controller.signal.aborted || err?.name === 'AbortError' || isCancelled) {
          return;
        }

        setArticles([]);
        setError(err);
        setHasMore(false);
        setCursor(null);
        setSearchOrigin(null);
        setIsLoading(false);
      }
    }

    executeQuery();

    return () => {
      isCancelled = true;
      controller.abort();
    };
  }, [category, query, limit, retryBaseDelay, refreshCounter]);

  const loadMore = useCallback(async () => {
    if (!cursor || isLoading || isLoadingMore) {
      return;
    }

    setIsLoadingMore(true);
    try {
      const categoryParam = category === 'ALL' ? '' : `&category=${category.toLowerCase()}`;
      const endpoint = `${API_ROUTES.NEWS.FEED}?limit=${limit}&cursor=${cursor}${categoryParam}`;
      const data = await api(endpoint);

      const nextArticles = data?.items || data?.articles || (Array.isArray(data) ? data : []);
      setArticles((prev) => [...prev, ...nextArticles]);
      setHasMore(Boolean(data?.has_more));
      setCursor(data?.next_cursor || null);
    } catch (err) {
      setError(err);
    } finally {
      setIsLoadingMore(false);
    }
  }, [cursor, isLoading, isLoadingMore, category, limit]);

  return {
    articles,
    setArticles,
    isLoading,
    isLoadingMore,
    error,
    hasMore,
    cursor,
    searchOrigin,
    loadMore,
    refetch,
  };
}
