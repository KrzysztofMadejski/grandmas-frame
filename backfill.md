# Backfill Guide — Historical WhatsApp Group Photos to Immich

This guide walks you through backfilling historical photos from a WhatsApp group into your Immich album. It uses a **service bot** — a WhatsApp account that was already a member of the target group and therefore has access to its message history.

---

## Overview

```
Service bot phone  →  Evolution API (new temp instance)  →  backfill.py  →  Immich album
```

The production frame bot (used by the daemon) and the service bot are **separate WhatsApp accounts**. The service bot is only needed for the one-time backfill; you can disconnect it afterwards.

---

## Prerequisites

- Docker stack running: `docker compose up -d`
- Python deps installed on the host:
  ```bash
  pip install httpx python-dotenv
  ```
- `.env` present and filled in (run `bash setup.sh` or copy `.env.example`)

---

## Step 1 — Create a service bot Evolution API instance

You need to connect the service bot's phone number to a new Evolution API instance.

### 1a. Create the instance

```bash
curl -s -X POST http://localhost:8080/instance/create \
  -H "apikey: $(grep EVOLUTION_API_KEY .env | cut -d= -f2)" \
  -H "Content-Type: application/json" \
  -d '{"instanceName": "service-bot", "integration": "WHATSAPP-BAILEYS"}' \
  | python3 -m json.tool
```

Add the instance name to `.env`:

```
USER_BACKFILL_EVOLUTION_INSTANCE_NAME=service-bot
```

The instance name is used in Evolution API URL paths (e.g. `/chat/findMessages/service-bot`).
Authentication uses the existing global `EVOLUTION_API_KEY` — no per-instance key needed.

### 1b. Scan the QR code

**Option A — browser (easiest):**

Open http://localhost:8080/manager in a browser. Click on the **service-bot** instance,
then **Get QR Code**. Open WhatsApp on the service bot phone → Linked Devices → Link a device,
and scan the code.

**Option B — terminal:**

```bash
curl -s "http://localhost:8080/instance/connect/service-bot" \
  -H "apikey: $(grep EVOLUTION_API_KEY .env | cut -d= -f2)" \
  | python3 -m json.tool
```

The response includes a `base64` QR image or a `pairingCode`. If you get a pairing code,
enter it in WhatsApp → Settings → Linked Devices → Link a device → Link with phone number instead.

### 1c. Verify connection

```bash
curl -s "http://localhost:8080/instance/connectionState/service-bot" \
  -H "apikey: $(grep EVOLUTION_API_KEY .env | cut -d= -f2)"
```

Wait until `"state"` is `"open"` before continuing.

---

## Step 2 — Find the target WhatsApp group

List all groups the service bot is a member of:

```bash
python backfill.py --list-groups
```

Example output:
```
Found 3 group(s):

  120363123456789012@g.us  —  Babcia Ela 🌸
  120363987654321098@g.us  —  Rodzinka
  120363111222333444@g.us  —  Praca
```

Find the group you want to backfill. Copy its JID and add it to `.env`:

```
WHATSAPP_GROUP_ID=120363123456789012@g.us
```

---

## Step 3 — Run the backfill

### Dry run first (recommended)

```bash
python backfill.py --dry-run
```

This fetches all messages and counts them **without downloading or uploading** anything.
Check that the total count looks right before proceeding.

### Full backfill

```bash
python backfill.py
```

The script:
1. Fetches all `imageMessage` and `videoMessage` from the group (paginated)
2. Downloads each via `getBase64FromMediaMessage`
3. Uploads to Immich (`POST /api/assets`)
4. Adds to the configured album (`PUT /api/albums/{IMMICH_ALBUM_ID}/assets`)
5. Skips duplicates gracefully (Immich returns `status: "duplicate"` for already-uploaded assets)

**It is safe to re-run** — duplicates are detected and skipped automatically.

Example progress output:
```
2026-03-09 14:22:01 INFO — Fetching image messages from group…
2026-03-09 14:22:03 INFO — Fetched 50 imageMessage messages (running total: 50)
2026-03-09 14:22:04 INFO — Fetched 32 imageMessage messages (running total: 82)
...
2026-03-09 14:22:10 INFO — Found 82 images + 5 videos = 87 total
2026-03-09 14:22:11 INFO — [1/87] imageMessage 3EB0A1234567.jpg (sent 2025-12-01)
...

====================================================
  Backfill complete
  Total found:  87
  Uploaded:     79
  Duplicates:   6  (already in Immich)
  Errors:       2
====================================================
```

Errors are logged individually and do not abort the run. Common causes:
- Expired media (old messages whose media WhatsApp has purged)
- Network timeouts (re-run to retry — duplicates skip automatically)

---

## Step 4 — Cleanup (optional)

After the backfill is complete, disconnect and delete the service bot instance to free resources:

```bash
# Logout from WhatsApp (revokes the linked device on the phone)
curl -X DELETE "http://localhost:8080/instance/logout/service-bot" \
  -H "apikey: $(grep EVOLUTION_API_KEY .env | cut -d= -f2)"

# Delete the instance from Evolution API
curl -X DELETE "http://localhost:8080/instance/delete/service-bot" \
  -H "apikey: $(grep EVOLUTION_API_KEY .env | cut -d= -f2)"
```

You can also remove `USER_BACKFILL_EVOLUTION_INSTANCE_NAME` from `.env` (the daemon doesn't use it).

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `Missing required env vars: USER_BACKFILL_EVOLUTION_INSTANCE_NAME` | Add `USER_BACKFILL_EVOLUTION_INSTANCE_NAME=service-bot` (your instance name) to `.env` |
| `Missing required env vars: WHATSAPP_GROUP_ID` | Run `--list-groups`, pick a JID, add to `.env` |
| `--list-groups` returns empty | Instance not connected — redo Step 1b/1c |
| Download errors for old messages | Media expired on WhatsApp servers — nothing to do, errors are logged and skipped |
| `401 Unauthorized` from Evolution API | Check `EVOLUTION_API_KEY` in `.env` matches the one in `docker-compose.yaml` |
| `404` from Immich album | Check `IMMICH_ALBUM_ID` in `.env` — copy from Immich web UI → album URL |
