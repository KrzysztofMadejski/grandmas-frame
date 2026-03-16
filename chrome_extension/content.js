/**
 * WhatsApp Media Downloader – content script
 * Requires jszip.min.js to be loaded first (see manifest.json).
 *
 * Exposes:
 *   window.__waMdCount()             → { count }
 *   window.__waMdDownload(batchSize) → { count, batches }
 */

const BATCH_SIZE_DEFAULT = 100;

function collectBlobUrls() {
  const urls = new Set();

  // Strategy 1: <img src="blob:…"> inside photo/video buttons.
  const buttons = document.querySelectorAll(
    '[role="button"][aria-label*="Image from"], [role="button"][aria-label*="Video from"]'
  );
  for (const btn of buttons) {
    for (const img of btn.querySelectorAll('img[src^="blob:https://web.whatsapp.com/"]')) {
      urls.add(img.src);
    }
  }

  // Strategy 2: inline background-image blob URLs.
  // Matches: style="background-image: url("blob:https://web.whatsapp.com/…")"
  const bgEls = document.querySelectorAll(
    '[style*="background-image: url(\\"blob:https://web.whatsapp.com/"]'
  );
  for (const el of bgEls) {
    const match = el.style.backgroundImage.match(
      /url\("(blob:https:\/\/web\.whatsapp\.com\/[^"]+)"\)/
    );
    if (match) urls.add(match[1]);
  }

  // Strategy 3: fallback – any blob img not caught above.
  for (const img of document.querySelectorAll('img[src^="blob:https://web.whatsapp.com/"]')) {
    urls.add(img.src);
  }

  return [...urls];
}

function triggerZipDownload(zipBlob, filename) {
  const url = URL.createObjectURL(zipBlob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 10000);
}

window.__waMdCount = function () {
  return { count: collectBlobUrls().length };
};

window.__waMdDownload = async function (batchSize = BATCH_SIZE_DEFAULT) {
  const urls = collectBlobUrls();
  if (urls.length === 0) return { count: 0, batches: 0 };

  const totalBatches = Math.ceil(urls.length / batchSize);

  for (let b = 0; b < totalBatches; b++) {
    const slice = urls.slice(b * batchSize, (b + 1) * batchSize);
    const zip = new JSZip();

    for (let i = 0; i < slice.length; i++) {
      try {
        const res = await fetch(slice[i]);
        const blob = await res.blob();
        const ext = (blob.type || 'image/jpeg').split('/')[1].replace('jpeg', 'jpg');
        const globalIndex = b * batchSize + i + 1;
        zip.file(`whatsapp-${String(globalIndex).padStart(4, '0')}.${ext}`, blob.arrayBuffer());
      } catch (err) {
        console.warn('[waMD] Failed to fetch', slice[i], err);
      }
    }

    const zipBlob = await zip.generateAsync({ type: 'blob', compression: 'STORE' });
    const suffix = totalBatches > 1 ? `-part${b + 1}of${totalBatches}` : '';
    triggerZipDownload(zipBlob, `whatsapp-photos${suffix}.zip`);

    // Small pause between batches so the browser can breathe.
    if (b < totalBatches - 1) await new Promise(r => setTimeout(r, 500));
  }

  return { count: urls.length, batches: totalBatches };
};
