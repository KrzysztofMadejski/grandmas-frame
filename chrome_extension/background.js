/**
 * Background service worker.
 * Receives DOWNLOAD messages from the content script and triggers
 * chrome.downloads.download(), which content scripts cannot call directly.
 */
chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type !== 'DOWNLOAD') return;

  chrome.downloads.download({
    url: msg.dataUrl,
    filename: msg.filename,
    saveAs: false,
  });
});
