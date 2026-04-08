import { useEffect } from 'react';

/**
 * Custom hook to set the document title.
 * @param {string} title - The title to set for the document.
 * @param {boolean} [addSuffix=true] - Whether to add the app name suffix.
 */
function useDocumentTitle(title, addSuffix = true) {
  useEffect(() => {
    if (title) {
      const suffix = addSuffix ? ' - WowRussian' : '';
      document.title = `${title}${suffix}`;
    } else {
      document.title = 'WowRussian';
    }
  }, [title, addSuffix]);
}

export default useDocumentTitle;
