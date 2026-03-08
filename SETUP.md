# Grandma's Frame — Setup Guide

Family sends a photo to a WhatsApp group → it appears on Grandma's photo frame.

**Stack:** Evolution API (WhatsApp) → photos_to_frame_daemon → Immich → ImmichFrame (Pi/tablet)

---

## Prerequisites

- Docker + Docker Compose v2
- `openssl` (for password generation in `setup.sh`)
- A dedicated WhatsApp number (not your main one — unofficial API carries a small ban risk)

---

## Local dev / testing

Use this when running on your own machine to test the pipeline before deploying.

### 1. Generate config

```bash
bash setup.sh
```

Accept all defaults. Photos will be stored in `./photos-local-dev/` inside the project directory.

### 2. Start services

```bash
docker compose up -d
```

`docker-compose.override.yaml` is applied automatically in dev — it exposes Postgres (5432), Redis (6379), and the daemon (3000) for local debugging tools.

### 3. Set up Immich

#### 3a. Create accounts

1. Open [http://localhost:2283](http://localhost:2283) and create your **personal admin account**
2. Go to **Administration → Users → Create user** and create a service account:
   - Email: `frame-bot@local` (never used, just needs to look valid)
   - Name: `Frame Bot`
   - No admin role needed

#### 3b. Get an API key for the service account

The daemon uploads photos as this service account. Immich does not allow admins to create API keys on behalf of other users, so you need to log in as the service account directly.

1. Open an **incognito window** and log in as `frame-bot@local`
2. Go to **Account Settings** (avatar, top right) → **API Keys → New API Key**
3. When prompted for permissions, enable at minimum:
   - `asset.read`, `asset.view`, `asset.edit`, `asset.share` — to upload photos
   - `album.read`, `album.update` — to look up the album
   - `albumAsset.create` — to add photos to the album
4. Copy the key and add it to `.env`:
   ```
   IMMICH_API_KEY=<key>
   ```
5. Restart the daemon:
   ```bash
   docker compose restart photos_to_frame_daemon
   ```

#### 3c. Create the album and share it with the service account

The daemon will not create the album — it expects to find one shared with it. You create and own it:

1. Log in as your **personal admin account**
2. Go to **Albums → Create Album** and name it exactly `Grandma's Frame` (or whatever `IMMICH_ALBUM_NAME` is set to in `.env`)
3. Open the album → **Share** → invite `frame-bot@local` with **Editor** role

The daemon checks both albums owned by the service account and albums shared with it, so it will find it automatically.

### 4. Set up Evolution API

#### 4a. Log in

1. Open [http://localhost:8080/manager](http://localhost:8080/manager)
2. Enter your `EVOLUTION_API_KEY` from `.env` as the API key

#### 4b. Create a WhatsApp instance

1. Click the green **Create instance** button (top right)
2. Fill in the form:
   - **Name** — anything you like, e.g. `Babcia Ela frame`
   - **Channel** — keep **Baileys** (open-source WhatsApp Web; correct for a personal number — do not use WhatsApp Cloud API which requires Meta approval)
   - **Token** — keep the prepopulated value; note it down, you'll need it for the webhook step
   - **Number** — leave **empty** (you'll pair via QR code)
3. Click **Save**

#### 4c. Scan the QR code

1. Click anywhere on the instance card (or the settings icon) to open it
2. Click the yellow **Get QR code** button
3. Open WhatsApp on your dedicated phone number → **Linked devices → Link a device** and scan the QR code

#### 4d. Configure the webhook

In the instance settings, open the **Webhook** tab and configure:

| Setting | Value |
|---|---|
| **Enabled** | on |
| **URL** | `http://photos_to_frame_daemon:3000/webhook` |
| **Webhook by Events** | off |
| **Webhook Base64** | **on** — media is embedded directly in the payload, no extra API call needed |
| **Events** | Click **Unmark All**, then enable only **`MESSAGES_UPSERT`** |

All other events are irrelevant and just generate noise.

#### 4e. Find your group JID

Send any message in the WhatsApp group — the group JID will appear in the Evolution API dashboard or daemon logs. Then update `.env`:
```
WHATSAPP_GROUP_ID=1234567890-1234567890@g.us
```
See `improvements.md` for a TODO to automate this step.

Restart the daemon to apply:
```bash
docker compose restart photos_to_frame_daemon
```

### 5. Test

Send a photo to the WhatsApp group. It should appear in Immich under the *Grandma's Frame* album within seconds.

---

## Production setup

Use this when deploying to a VPS or home server.

### 1. Prepare the server

```bash
sudo mkdir -p /var/lib/grandmas-frame/photos
sudo chown $USER:$USER /var/lib/grandmas-frame/photos
```

### 2. Generate config

```bash
bash setup.sh
```

When prompted for **Photo storage path**, enter:
```
/var/lib/grandmas-frame/photos
```

### 3. Start services

```bash
docker compose -f docker-compose.yaml -f docker-compose.prod.yaml up -d
```

This omits `docker-compose.override.yaml`, so Postgres and Redis ports stay closed.

### 4. Set up Immich and Evolution API

Follow steps 3–5 from the local setup above, replacing `localhost` with your server's IP or hostname.

### 5. Expose services (optional but recommended)

Put Immich and Evolution API behind a reverse proxy (Caddy or nginx) with HTTPS.
Only expose ports you need — the daemon (`3000`) should stay internal.

Example Caddyfile:
```
immich.yourdomain.com {
    reverse_proxy localhost:2283
}

evolution.yourdomain.com {
    reverse_proxy localhost:8080
}
```

If using a public URL for Evolution API webhooks, set the webhook to:
```
https://evolution.yourdomain.com/webhook/instance-name
```
And point the instance webhook back at the daemon's internal address:
```
http://photos_to_frame_daemon:3000/webhook
```

### 6. Backups

Photos are stored in `/var/lib/grandmas-frame/photos` — back this up with any standard tool (rsync, restic, etc.).

Postgres data is in the `grandmas-frame_postgres_data` Docker volume:
```bash
docker run --rm -v grandmas-frame_postgres_data:/data -v /backup:/backup \
  alpine tar czf /backup/postgres-$(date +%F).tar.gz /data
```

### 7. Set up ImmichFrame (the display)

On your Raspberry Pi, Android tablet, or Apple TV, install [ImmichFrame](https://github.com/immichFrame/ImmichFrame) and point it at:
- Immich URL: `http://<server>:2283` (or your HTTPS domain)
- Immich API key: create a **separate** key on your **personal admin account** (not frame-bot) with read-only permissions:
  - `asset.read`, `asset.view`, `asset.download`
  - `album.read`
- Album: the name you set in `IMMICH_ALBUM_NAME`

---

## Environment variables reference

| Variable | Description |
|---|---|
| `DB_ADMIN_PASSWORD` | Postgres superuser password (internal only) |
| `IMMICH_DB_PASSWORD` | Immich's postgres user password |
| `EVOLUTION_DB_PASSWORD` | Evolution API's postgres user password |
| `IMMICH_VERSION` | Immich image tag (`release` = latest stable) |
| `UPLOAD_LOCATION` | Host path where Immich stores photos |
| `IMMICH_API_KEY` | Set after first Immich login |
| `EVOLUTION_API_KEY` | Evolution API authentication key |
| `IMMICH_ALBUM_NAME` | Album name to add photos to (default: *Grandma's Frame*) |
| `WHATSAPP_GROUP_ID` | Group JID to filter — empty means accept from all chats |
