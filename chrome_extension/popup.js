const scanBtn     = document.getElementById('scanBtn');
const downloadBtn = document.getElementById('downloadBtn');
const status      = document.getElementById('status');

function setStatus(msg, type = 'info') {
  status.textContent = msg;
  status.className = type;
}

async function getTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab.url?.startsWith('https://web.whatsapp.com')) {
    setStatus('Open web.whatsapp.com first.', 'error');
    return null;
  }
  return tab;
}

async function execInPage(tab, func, args = []) {
  try {
    const [res] = await chrome.scripting.executeScript({ target: { tabId: tab.id }, func, args });
    return res?.result ?? null;
  } catch (e) {
    setStatus('Could not reach the page: ' + e.message, 'error');
    return null;
  }
}

scanBtn.addEventListener('click', async () => {
  scanBtn.disabled = true;
  downloadBtn.style.display = 'none';
  setStatus('Scanning…');

  const tab = await getTab();
  if (!tab) { scanBtn.disabled = false; return; }

  const result = await execInPage(tab, () => window.__waMdCount?.());
  if (!result) {
    setStatus('Content script not ready — reload the WhatsApp tab and try again.', 'error');
    scanBtn.disabled = false;
    return;
  }

  if (result.count === 0) {
    setStatus('No images found. Make sure the Media tab is open and images are visible.', 'warn');
  } else {
    const batches = Math.ceil(result.count / 100);
    const batchNote = batches > 1 ? ` (${batches} ZIP files)` : ' (1 ZIP file)';
    setStatus(`Found ${result.count} image(s)${batchNote}. Ready to download.`);
    downloadBtn.textContent = `Download ${result.count} image(s) as ZIP`;
    downloadBtn.style.display = 'block';
  }

  scanBtn.disabled = false;
});

downloadBtn.addEventListener('click', async () => {
  downloadBtn.disabled = true;
  scanBtn.disabled = true;
  setStatus('Building ZIP… this may take a moment.');

  const tab = await getTab();
  if (!tab) { downloadBtn.disabled = false; scanBtn.disabled = false; return; }

  const result = await execInPage(tab, () => window.__waMdDownload?.());

  if (!result) {
    setStatus('Download failed — reload the WhatsApp tab and try again.', 'error');
  } else {
    const zipWord = result.batches === 1 ? 'ZIP' : `${result.batches} ZIPs`;
    setStatus(`Done — ${result.count} image(s) packed into ${zipWord}.`);
    downloadBtn.style.display = 'none';
  }

  downloadBtn.disabled = false;
  scanBtn.disabled = false;
});
