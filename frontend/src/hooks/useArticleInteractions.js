import { useState, useRef, useCallback } from 'react';
import { api } from '../lib/api.js';
import { API_ROUTES } from '../lib/constants.js';

export const SWISS_ERROR_TOAST = 'ACTION ABORTED // UNABLE TO REACH SERVER';

/**
 * Hook for optimistic bookmarking and read toggling with guaranteed snapshot rollback
 * and in-flight click debouncing across lagging sockets.
 * Strictly conforms to Ponytail Ultra: native React 18 hooks, zero heavy state libraries.
 *
 * @param {object} [options={}]
 * @param {Array<object>} [options.initialArticles=[]] - Initial articles for internal state
 * @param {Array<object>} [options.articles] - External articles array (integration mode)
 * @param {(updater: any) => void} [options.setArticles] - External articles setter
 * @returns {object} Interaction handlers, article state, and error toast
 */
export function useArticleInteractions({
  initialArticles = [],
  articles: externalArticles,
  setArticles: externalSetArticles,
} = {}) {
  const isControlled = externalSetArticles !== undefined;
  const [internalArticles, setInternalArticles] = useState(initialArticles);
  const [errorToast, setErrorToast] = useState(null);
  const inFlightMutationsRef = useRef(new Set());

  const currentArticles = isControlled ? externalArticles : internalArticles;
  const setArticlesState = isControlled ? externalSetArticles : setInternalArticles;

  // Fresh reference to current articles for snapshotting
  const articlesRef = useRef(currentArticles);
  articlesRef.current = currentArticles;

  const clearToast = useCallback(() => {
    setErrorToast(null);
  }, []);

  const toggleBookmark = useCallback(
    async (articleOrId) => {
      const articleId =
        typeof articleOrId === 'object' && articleOrId !== null
          ? articleOrId.id
          : articleOrId;
      const mutationKey = `bookmark-${articleId}`;

      // Invariant 5: Debounce / lock rapid sequential clicks on the same entity
      if (inFlightMutationsRef.current.has(mutationKey)) {
        return;
      }
      inFlightMutationsRef.current.add(mutationKey);

      // Invariant 2: Snapshot pre-mutation state array
      const snapshot = (articlesRef.current || []).map((item) => ({ ...item }));
      const targetArticle = snapshot.find((a) => String(a.id) === String(articleId));

      if (!targetArticle) {
        inFlightMutationsRef.current.delete(mutationKey);
        return;
      }

      const wasBookmarked = Boolean(targetArticle.is_bookmarked);
      const nextBookmarked = !wasBookmarked;

      // Invariant 3: Optimistically update local article state
      setArticlesState((prevArticles) =>
        prevArticles.map((item) =>
          String(item.id) === String(articleId)
            ? { ...item, is_bookmarked: nextBookmarked }
            : item
        )
      );

      try {
        if (wasBookmarked) {
          await api(`${API_ROUTES.NEWS.BOOKMARKS}/${articleId}`, {
            method: 'DELETE',
          });
        } else {
          await api(API_ROUTES.NEWS.BOOKMARKS, {
            method: 'POST',
            body: { article_id: articleId },
          });
        }
      } catch (err) {
        // Invariant 4: Roll back state to pre-mutation snapshot on network/API failure
        setArticlesState(snapshot);
        setErrorToast(SWISS_ERROR_TOAST);
        throw err;
      } finally {
        inFlightMutationsRef.current.delete(mutationKey);
      }
    },
    [setArticlesState]
  );

  const toggleRead = useCallback(
    async (articleOrId) => {
      const articleId =
        typeof articleOrId === 'object' && articleOrId !== null
          ? articleOrId.id
          : articleOrId;
      const mutationKey = `read-${articleId}`;

      if (inFlightMutationsRef.current.has(mutationKey)) {
        return;
      }
      inFlightMutationsRef.current.add(mutationKey);

      const snapshot = (articlesRef.current || []).map((item) => ({ ...item }));
      const targetArticle = snapshot.find((a) => String(a.id) === String(articleId));

      if (!targetArticle) {
        inFlightMutationsRef.current.delete(mutationKey);
        return;
      }

      const wasRead = Boolean(targetArticle.is_read);
      const nextRead = !wasRead;

      setArticlesState((prevArticles) =>
        prevArticles.map((item) =>
          String(item.id) === String(articleId) ? { ...item, is_read: nextRead } : item
        )
      );

      try {
        if (wasRead) {
          await api(`${API_ROUTES.NEWS.READS}/${articleId}`, { method: 'DELETE' });
        } else {
          await api(API_ROUTES.NEWS.READS, {
            method: 'POST',
            body: { article_id: articleId },
          });
        }
      } catch (err) {
        setArticlesState(snapshot);
        setErrorToast(SWISS_ERROR_TOAST);
        throw err;
      } finally {
        inFlightMutationsRef.current.delete(mutationKey);
      }
    },
    [setArticlesState]
  );

  return {
    articles: currentArticles,
    setArticles: setArticlesState,
    toggleBookmark,
    toggleRead,
    errorToast,
    setErrorToast,
    clearToast,
    inFlightMutations: inFlightMutationsRef.current,
  };
}
