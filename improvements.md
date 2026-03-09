# Improvements / TODOs

## WhatsApp history backfill

- ✅ **Script to backfill media from an existing user account via Evolution API** — done (`backfill.py`)

## Chrome extension backfill

- **Chrome extension that downloads media from web.whatsapp.com directly to Immich**
  WhatsApp Web already decrypts and renders full-resolution media in the browser, so a
  Chrome extension can grab blob URLs as WhatsApp renders them (via `MutationObserver`
  on the media panel or by intercepting fetch/XHR) — no auth, no QR, no expiry issues.
  It would upload each blob to Immich (`POST /api/assets`) and add to the album
  (`PUT /api/albums/{id}/assets`), with Immich URL and API key configurable in the
  extension's options page. Would recover media that the Evolution API backfill misses
  due to expired CDN links.

## Setup UX

- **Guide user through setting WHATSAPP_GROUP_ID**
  After the user sets up a WhatsApp instance in Evolution API and scans the QR code,
  the setup flow should help them find their group JID and write it into `.env`.
  The JID is visible in the Evolution API dashboard when a message is received, or
  via the `/chat/findChats/{instance}` endpoint. The setup script (or a follow-up
  prompt) should explain this and offer to update `.env` automatically.
