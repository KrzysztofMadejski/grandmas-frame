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
2. Go to **Albums → Create Album** and name it anything you like (e.g. `Grandma's Frame`)
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

ImmichFrame runs as a web container (already in `docker-compose.yaml`) that connects to Immich and serves the slideshow. On a tablet, a thin Android app just wraps this web UI.

#### 7a. Create an API key for the frame

Create the key on the **frame-bot service account** (not your personal admin account). This means ImmichFrame can only see albums shared with the bot — natural scoping, no access to your personal library.

1. Log in as `frame-bot@local` (incognito window)
2. Account Settings → API Keys → New API Key
3. Enable: `asset.read`, `asset.view`, `asset.download`, `album.read`
4. Copy the key and add to `.env`:
   ```
   IMMICH_FRAME_API_KEY=<key>
   ```

#### 7b. Get the album UUID

ImmichFrame requires a UUID, not the album name. Find it in the Immich album URL:
```
http://localhost:2283/albums/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ this part
```

Or via the API (as the frame-bot account):
```bash
docker exec immich_server node -e "
fetch('http://localhost:2283/api/albums?shared=true',
  {headers:{'x-api-key':'<IMMICH_FRAME_API_KEY>'}})
  .then(r=>r.json()).then(d=>d.forEach(a=>console.log(a.id, a.albumName)))"
```

Add it to `.env`:
```
IMMICH_ALBUM_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

#### 7c. Restart and verify

```bash
docker compose restart immichframe
```

In local dev, open `http://localhost:8080` to verify the slideshow works.

#### 7c. Install the Android app on the tablet

Install [ImmichFrame](https://play.google.com/store/apps/details?id=com.immichframe.immichframe) from the Play Store (or sideload from [GitHub releases](https://github.com/immichFrame/ImmichFrame_Android/releases)).

On first launch, enter the ImmichFrame server URL:
- Local network: `http://<server-ip>:8080`
- Or via Tailscale: `http://<tailscale-ip>:8080` (see security section)

---

## Setting up ImmichFrame on Samsung Galaxy Tab (Kiosk Mode)

### 1. Kiosk mode — set ImmichFrame as the default Home launcher (recommended)

ImmichFrame declares itself a valid Home app, so:
- It starts automatically on every reboot — Android always launches the default Home app on startup
- The Home button returns to ImmichFrame instead of leaving it

```
Settings > Apps > Default apps > Home app > ImmichFrame
```

To undo: Settings > Apps > Default apps > Home app > One UI Home

**Optional — Screen Pinning** for extra lock-down (requires a PIN to exit):

1. Settings > Security and privacy > More security settings > App pinning > On
2. Open ImmichFrame, swipe up to Recents, tap the ImmichFrame app icon > Pin

### 2. Keep screen always on

```
Settings > About tablet > Software information > tap "Build number" 7 times  ← enables Developer Options
Settings > Developer options > Stay awake > On
```

This keeps the screen on while charging — exactly right for a plugged-in frame.

Also disable Samsung's built-in screensaver (it will interrupt the photo frame):
```
Settings > Display > Screen saver > Off
```

### 3. Display tweaks

| Setting | Path | Recommended value |
|---|---|---|
| Screen timeout | Settings > Display > Screen timeout | Maximum (10–30 min; "Stay awake" above overrides it anyway) |
| Adaptive brightness | Settings > Display > Brightness | Off — set a fixed level |
| Edge panels | Settings > Display > Edge panels | Off |
| Navigation bar | Settings > Display > Navigation bar | Swipe gestures (thinner bar) |
| Orientation | Pull down shade, tap rotation lock | Locked |

### 4. Power — safe long-term charging

Keeping a tablet plugged in 24/7 can swell the battery within 12–18 months. Samsung provides a built-in fix:

```
Settings > Battery > Battery protection > Basic   ← caps charging at 85%
```

Use a modest 5–10 W charger (not a fast charger) — lower heat = slower degradation.

### 5. Night schedule

ImmichFrame has no built-in sleep scheduler. Use one of:

- **Samsung Routines** (built-in): Settings > Modes and Routines > Routines — dim at 23:00, launch ImmichFrame at 08:00
- **ImmichFrame Remote Control API + server cron** — the Android app exposes a small HTTP server on port 53287:
  ```bash
  # Add to crontab on your server
  0 23 * * *  curl -s http://<tablet-ip>:53287/dim
  0 8  * * *  curl -s http://<tablet-ip>:53287/undim
  ```

### 6. Wi-Fi reliability

```
Settings > Apps > ImmichFrame > Battery > Battery optimization > Don't optimize
Settings > Connections > Wi-Fi > ⋮ > Advanced > Keep Wi-Fi on during sleep > Always
Settings > Connections > Wi-Fi > ⋮ > Advanced > Wi-Fi power saving mode > Off
```

### 7. Samsung One UI tips

```
Settings > Lock screen > Screen lock type > None          ← no lock screen on wake
Settings > Notifications > Do not disturb > On (24/7)
Settings > Advanced features > Motions and gestures > Double tap to turn on screen > Off
Settings > Advanced features > Motions and gestures > Lift to wake > Off
```

### 8. Quick checklist

- [ ] ImmichFrame set as default Home app
- [ ] Developer options: Stay awake — On
- [ ] Screen saver — Off
- [ ] Adaptive brightness — Off, fixed level set
- [ ] Edge panels — Off
- [ ] Battery Protection — Basic (85% cap)
- [ ] Battery optimisation for ImmichFrame — Off (Don't optimize)
- [ ] Wi-Fi: Keep on during sleep — Always
- [ ] Wi-Fi power saving mode — Off
- [ ] Lock screen — None
- [ ] Do Not Disturb — On
- [ ] Double-tap to wake / Lift to wake — Off
- [ ] Orientation locked
- [ ] Night schedule configured

---

## Securing the ImmichFrame display

ImmichFrame has no authentication by default. Since the server will be publicly accessible (or eventually will be), you need to restrict who can reach the slideshow.

### Option 1: Tailscale (recommended)

Tailscale creates an encrypted WireGuard overlay between your devices. ImmichFrame is never exposed publicly — the tablet connects through a private tunnel, and nothing is reachable from the internet or even the local network.

**Server:**
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
# Note the server's Tailscale IP (100.x.y.z) at https://login.tailscale.com/admin/machines
```

Bind ImmichFrame to localhost only so it is not reachable on the LAN. In `docker-compose.prod.yaml` add:
```yaml
services:
  immichframe:
    ports:
      - "127.0.0.1:8080:8080"
```

**Tablet:** Install the [Tailscale app](https://play.google.com/store/apps/details?id=com.tailscale.ipn), sign in with the same Tailscale account.

In the ImmichFrame app, set the server URL to the Tailscale IP: `http://100.x.y.z:8080`

No open ports on the router, no LAN exposure, encrypted in transit.

### Option 2: Reverse proxy with HTTP Basic Auth (Caddy)

Suitable if you already run a reverse proxy with a domain and TLS certificate.

```bash
caddy hash-password   # generates the hashed password
```

`/etc/caddy/Caddyfile`:
```
frame.yourdomain.com {
    basicauth {
        grandma $2a$14$<hash-from-above>
    }
    reverse_proxy localhost:8080
}
```

Bind ImmichFrame to localhost only (same `127.0.0.1:8080:8080` binding as above), then:
```bash
sudo systemctl reload caddy
```

The tablet browser will prompt for username/password once and remember it.

### Option 3: Host firewall — allow only the tablet's IP

```bash
# Set a DHCP reservation for the tablet's MAC in your router first
sudo ufw allow from 192.168.1.50 to any port 8080
sudo ufw deny 8080
sudo ufw reload
```

Breaks if the tablet gets a new IP — a DHCP reservation is essential.

---

## Bulk-uploading existing WhatsApp group media to Immich

Use this to backfill all historical photos from the group before the daemon was running.

### Recommended: Immich mobile app backup

On Android, the Immich mobile app can back up the WhatsApp Images and WhatsApp Video device albums to Immich:

1. Install the Immich mobile app on a group member's phone
2. Go to the backup screen → Select albums to back up
3. Enable "WhatsApp Images" and "WhatsApp Video"
4. Tap Start Backup (must be on the same network as the Immich server, or connected via Tailscale)

**Caveat:** This uploads all WhatsApp media saved on that device, from all chats — not just the family group. After the backup completes, go to Immich and move only the photos you want into the *Grandma's Frame* album. The rest can stay in the user's personal library or be deleted.

The Immich CLI deduplicates by content hash, so any photos later re-sent through the group and picked up by the daemon will not be duplicated.

> **Note:** A smarter approach — a script that connects as an existing group member account via Evolution API and downloads only group photos — is tracked in `improvements.md`.

---

## Environment variables reference

| Variable | Description |
|---|---|
| `DB_ADMIN_PASSWORD` | Postgres superuser password (internal only) |
| `IMMICH_DB_PASSWORD` | Immich's postgres user password |
| `EVOLUTION_DB_PASSWORD` | Evolution API's postgres user password |
| `IMMICH_VERSION` | Immich image tag (`release` = latest stable) |
| `UPLOAD_LOCATION` | Host path where Immich stores photos |
| `IMMICH_API_KEY` | API key for the frame-bot service account (upload) |
| `EVOLUTION_API_KEY` | Evolution API authentication key |
| `IMMICH_ALBUM_ID` | UUID of the album — used by both the daemon (to add photos) and ImmichFrame (to display). Copy from the Immich album URL. |
| `WHATSAPP_GROUP_ID` | Group JID to filter — empty means accept from all chats |
| `IMMICH_FRAME_API_KEY` | API key for ImmichFrame display — created on the frame-bot account for natural album scoping |
