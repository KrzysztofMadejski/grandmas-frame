# Chrome Extension – Future Improvements

## Video download

Videos in the WhatsApp Web media library are not preloaded as blob URLs — only their
thumbnail is present in the DOM (as a `data:image/jpeg;base64,…` inline). The video blob
URL is only created by WhatsApp when the user clicks to play. The current DOM-scan approach
therefore finds no blob URLs for videos.

### Options

**Option 1 – Click-and-capture (automated)**
Programmatically click each video item, wait for WhatsApp to load it, grab the blob URL
from the newly created `<video src="blob:…">` element, then close the player before moving
to the next. Works without any user interaction, but is fragile (relies on timing/DOM
structure) and slow for large libraries.

**Option 2 – Intercept `URL.createObjectURL` (recommended)**
On page load, inject a small script into the real page JS context (via a `<script>` tag,
since content scripts run in an isolated world and can't intercept page globals). The
injected script wraps `URL.createObjectURL` and records every blob URL WhatsApp creates.
As the user plays videos normally in the media library, the interceptor silently harvests
the URLs. When the user then hits Scan, the extension already has them. More reliable than
click-and-capture; requires the user to play each video they want downloaded.

**Option 3 – Intercept fetch/XHR**
Similar injection approach, but wraps `fetch` (or `XMLHttpRequest`) to capture the raw
encrypted video chunks as WhatsApp downloads them. Requires also intercepting the
decryption step (WhatsApp decrypts in-browser using the Web Crypto API). Significantly
more complex than Option 2 with little practical advantage.

### Recommended path
Implement Option 2. The injected interceptor is small and passive; the UX is natural
(user plays videos, then clicks Download). Option 1 can be added later as a convenience
for users who don't want to manually play each video.
