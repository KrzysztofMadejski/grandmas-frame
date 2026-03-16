# Improvements / TODOs

## WhatsApp history backfill

- ✅ **Script to backfill media from an existing user account via Evolution API** — done (`backfill.py`)

## Chrome extension backfill

- ✅ **Chrome extension that downloads media from web.whatsapp.com** — done (`chrom_extension/`)
  Scans blob URLs from the Media tab (rendered images + background-image elements),
  packs them into ZIP files in-memory (batches of 100), and triggers a single download
  per batch. Recovers more images than `backfill.py` because it bypasses CDN link expiry —
  WhatsApp Web has already decrypted and rendered the images, so expiry is irrelevant.

- **Upload directly to Immich from the extension** (next step)
  Instead of downloading a ZIP and manually importing, the extension could POST each blob
  directly to Immich (`POST /api/assets`) and add to the album (`PUT /api/albums/{id}/assets`),
  with Immich URL and API key configurable in the extension's options page.

## Setup UX

- **Guide user through setting WHATSAPP_GROUP_ID**
  After the user sets up a WhatsApp instance in Evolution API and scans the QR code,
  the setup flow should help them find their group JID and write it into `.env`.
  The JID is visible in the Evolution API dashboard when a message is received, or
  via the `/chat/findChats/{instance}` endpoint. The setup script (or a follow-up
  prompt) should explain this and offer to update `.env` automatically.
