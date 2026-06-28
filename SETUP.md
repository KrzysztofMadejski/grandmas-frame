# Grandma's Frame — Setup Guide

Family sends a photo to a WhatsApp group → it appears on Grandma's photo frame.

**Stack:** Evolution API (WhatsApp) → photos_to_frame_daemon → Immich → ImmichFrame (Pi/tablet)

---

## Prerequisites

- Docker + Docker Compose v2+ (tested with v5; v5 has stricter validation — the compose files are compatible)
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

#### 3a. Create admin account

1. Open [http://localhost:2283](http://localhost:2283) and create your **admin account**

#### 3b. Create two API keys

Both keys can live on your admin account — this is the simplest setup and perfectly fine for a family photo frame on a private network.

1. Go to **Account Settings** (avatar, top right) → **API Keys**
2. Create two keys:

| Key | Name | Permissions | `.env` variable |
|-----|------|-------------|-----------------|
| **Daemon key** | `daemon` | `asset.read`, `asset.view`, `asset.upload`, `asset.edit.create`, `asset.share`, `album.read`, `album.update`, `albumAsset.create`, `user.read` | `IMMICH_API_KEY` |
| **Frame key** | `frame` | `asset.read`, `asset.view`, `asset.download`, `album.read` | `IMMICH_FRAME_API_KEY` |

3. Add both keys to `.env` and restart:
   ```bash
   docker compose restart photos_to_frame_daemon immichframe
   ```

> **Want more isolation?** Create a separate `frame-bot@local` user, log in as them to create the frame API key, and share the album with them. This scopes the frame to only see shared albums. But for most setups the admin-key approach is simpler and sufficient.

#### 3c. Create the album

1. Go to **Albums → Create Album** and name it anything you like (e.g. `Grandma's Frame`)
2. Copy the **album UUID** from the URL:
   ```
   http://localhost:2283/albums/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
                                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ this part
   ```
3. Add it to `.env`:
   ```
   IMMICH_ALBUM_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   ```

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
chmod +x init-db.sh   # must be executable before postgres first starts, otherwise it's silently skipped
bash setup.sh
chmod 600 .env         # restrict credentials to the current user only
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

**Low-memory VPS (4 GB, e.g. Mikrus 3.5):** add the memory-tuned overlay:

```bash
docker compose -f docker-compose.yaml -f docker-compose.prod.yaml -f docker-compose.mikrus35.yaml up -d
```

This rebalances memory limits (Postgres 1 GB, Immich Server 1.5 GB, ML 1 GB, everything else 128–256 MB) and switches the face recognition model to the smaller `buffalo_s`.

### 4. Access the web UIs

If your VPS doesn't expose ports (common on budget VPS like Mikrus), use SSH tunnels:

```bash
# Tunnel Immich and Evolution API to your laptop
ssh -f -N -L 2283:localhost:2283 -L 8080:localhost:8080 root@your-vps -p <port>
```

Then open `http://localhost:2283` (Immich) and `http://localhost:8080` (Evolution API) as if they were local.

### 5. Set up Immich and Evolution API

Follow steps 3–5 from the local setup above — with the SSH tunnel, everything works on `localhost`.

### 6. Expose services (optional)

If you want persistent access without SSH tunnels, put services behind a reverse proxy (Caddy or nginx) with HTTPS:

```
immich.yourdomain.com {
    reverse_proxy localhost:2283
}

evolution.yourdomain.com {
    reverse_proxy localhost:8080
}
```

If using Tailscale (already in the prod compose), no reverse proxy is needed — access services via the Tailscale hostname directly.

### 6. Backups

Photos are stored in `/var/lib/grandmas-frame/photos` — back this up with any standard tool (rsync, restic, etc.).

Postgres data is in the `grandmas-frame_postgres_data` Docker volume:
```bash
docker run --rm -v grandmas-frame_postgres_data:/data -v /backup:/backup \
  alpine tar czf /backup/postgres-$(date +%F).tar.gz /data
```

### 7. Set up ImmichFrame (the display)

ImmichFrame runs as a web container (already in `docker-compose.yaml`) that connects to Immich and serves the slideshow. On a tablet, a thin Android app just wraps this web UI.

#### 7a. API key and album

If you followed step 3b, `IMMICH_FRAME_API_KEY` and `IMMICH_ALBUM_ID` are already in your `.env`. Verify the frame is working:

- **Local dev:** open `http://localhost:8080`
- **Production with Tailscale:** open `http://grandmas-frame:8080`

If the frame shows "No photos", check that the album has at least one photo.

#### 7b. Install the Android app on the tablet

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

### Exiting kiosk mode

**If Screen Pinning is active** (screen shows a lock icon when you swipe up):

1. Swipe up from the bottom and hold — this opens the Recents view
2. Tap the **pin icon** (or hold **Back + Recents** on older models)
3. Enter your PIN to unpin

**Once unpinned (or if Screen Pinning was never enabled):**

```
Settings > Apps > Default apps > Home app > One UI Home
```

This restores normal tablet behavior. To re-enter kiosk mode, reverse the steps in section 1 above.

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

Use **Samsung Routines** for night dimming:

```
Settings > Modes and Routines > Routines
```

Create two routines:
- **Night:** At 23:00 → set brightness to 1%
- **Morning:** At 08:00 → set brightness to your preferred level

For a full blackout, you can use ImmichFrame's built-in Dim Settings instead — but beware: once dimmed, the screen goes fully black with no obvious way to undim or access settings. Recovering requires clearing app data (Settings → Apps → ImmichFrame → Storage → Clear Data).

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

Tailscale runs as a Docker sidecar in `docker-compose.prod.yaml` — no host-level install needed. ImmichFrame shares Tailscale's network namespace and has no host port binding at all.

**Server:** Generate a pre-authorized, reusable (non-ephemeral) auth key at [tailscale.com/admin/settings/keys](https://login.tailscale.com/admin/settings/keys) and add it to `.env`:
```
TS_AUTHKEY=tskey-auth-...
```

The Tailscale container joins your tailnet automatically on first start. Find the device IP at [tailscale.com/admin/machines](https://login.tailscale.com/admin/machines).

**Tablet:** Install the [Tailscale app](https://play.google.com/store/apps/details?id=com.tailscale.ipn), sign in with the same Tailscale account.

In the ImmichFrame app, set the server URL using the machine name or Tailscale IP:
```
http://grandmas-frame:8080
```
or `http://100.x.y.z:8080` if MagicDNS is not enabled.

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

## Bulk-uploading existing photos to Immich

Use this to backfill historical photos before the daemon was running.

### Option 1: Immich CLI inside Docker (recommended for files on disk)

If you have photos on your computer (e.g. exported from WhatsApp Web):

1. **Deduplicate** by content hash (optional but recommended):
   ```bash
   mkdir -p deduplicated
   for file in source-folder/*; do
     hash=$(shasum -a 256 "$file" | cut -d' ' -f1)
     ext="${file##*.}"
     cp -n "$file" "deduplicated/${hash}.${ext}"
   done
   ```

2. **Copy to the server:**
   ```bash
   scp -P <port> deduplicated/* root@your-vps:/tmp/photos-upload/
   ```

3. **Upload via the Immich CLI** (it's bundled inside the Immich server image):
   ```bash
   docker run --rm --entrypoint '' \
     --network grandmas-frame_app \
     -v /tmp/photos-upload:/import:ro \
     -e IMMICH_INSTANCE_URL=http://immich-server:2283 \
     -e IMMICH_API_KEY=<your-api-key> \
     ghcr.io/immich-app/immich-server:release \
     /usr/src/app/server/bin/immich upload \
       --album-name 'Your Album Name' \
       --no-progress /import/
   ```

4. **Clean up** the temp files:
   ```bash
   rm -rf /tmp/photos-upload
   ```

The Immich CLI deduplicates by content hash, so re-uploading the same photos is safe.

### Option 2: Immich mobile app backup

On Android, the Immich mobile app can back up WhatsApp device albums:

1. Install the Immich mobile app on a group member's phone
2. Backup screen → Select albums → enable "WhatsApp Images" and "WhatsApp Video"
3. Start Backup (must be on the same network or connected via Tailscale)

**Caveat:** This uploads all WhatsApp media from all chats, not just the family group. After backup, move the relevant photos into the frame album manually.

> **Note:** A smarter approach — a script that connects as an existing group member via Evolution API and downloads only group photos — is tracked in `improvements.md`.

---

## Environment variables reference

| Variable | Description |
|---|---|
| `DB_ADMIN_PASSWORD` | Postgres superuser password (internal only) |
| `IMMICH_DB_PASSWORD` | Immich's postgres user password |
| `EVOLUTION_DB_PASSWORD` | Evolution API's postgres user password |
| `IMMICH_VERSION` | Immich image tag (`release` = latest stable) |
| `UPLOAD_LOCATION` | Host path where Immich stores photos |
| `IMMICH_API_KEY` | API key for uploading photos (daemon) |
| `EVOLUTION_API_KEY` | Evolution API authentication key |
| `IMMICH_ALBUM_ID` | UUID of the album — used by both the daemon (to add photos) and ImmichFrame (to display). Copy from the Immich album URL. |
| `WHATSAPP_GROUP_ID` | Group JID to filter — empty means accept from all chats |
| `IMMICH_FRAME_API_KEY` | API key for ImmichFrame display (can be same admin account or a separate frame-bot user) |

---

## Troubleshooting

### Postgres crashes with "Operation not permitted"

```
chmod: changing permissions of '/var/lib/postgresql/data': Operation not permitted
error: failed switching to "postgres": operation not permitted
```

The prod compose uses `cap_drop: ALL` for security. Postgres and Redis need capabilities added back to switch from root to their service user at startup. The prod yaml already includes the required `cap_add` entries (`SETUID`, `SETGID`, `CHOWN`, `FOWNER`, `DAC_OVERRIDE` for postgres; `SETUID`, `SETGID` for redis). If you see this error, make sure you're using the latest `docker-compose.prod.yaml`.

### Immich crashes with "CONNECTION_CLOSED" or "database system is not yet accepting connections"

Immich started before Postgres was fully ready. This can happen after a fresh deploy or restart when Postgres needs time to initialize (especially on low-memory VPS). Fix: wait for Postgres to become healthy (`docker ps` shows `(healthy)`), then restart Immich:

```bash
docker restart immich_server
```

### Postgres at 99% memory / OOM-killed

On a 4 GB VPS, Postgres needs at least 1 GB — the initial geodata import (reverse geocoding) consumes significant memory. If you see Postgres restart-looping after first deploy, increase its memory limit in the mikrus35 overlay.

### photos_to_frame_daemon keeps restarting

Check `docker logs grandmas_photos_to_frame_daemon`:

- **"Connection refused"** — Evolution API or Immich isn't ready yet. The daemon will recover on its own once they're up.
- **"401 Unauthorized"** — `IMMICH_API_KEY` is empty or invalid. Set it in `.env` and restart.
- **"403 Forbidden / Missing required permission"** — the API key is missing permissions. See the permissions table in step 3b.

### Thumbnails not showing after upload

Normal — Immich generates thumbnails in the background. Check progress in **Administration → Jobs**. On a low-memory VPS this can take a few minutes for a large batch.

### init-db.sh not running / databases not created

Postgres only runs scripts in `/docker-entrypoint-initdb.d/` on **first initialization** (when the data volume is empty). If `init-db.sh` wasn't executable at that point, Postgres silently skipped it. Fix:

```bash
docker compose down
docker volume rm grandmas-frame_postgres_data   # WARNING: deletes all DB data
chmod +x init-db.sh
docker compose up -d
```

### ImmichFrame shows black screen on tablet

Likely cause: ImmichFrame's built-in **Dim Settings** are active (screen goes fully black). The app has no obvious way to access settings from the dimmed state.

Fix: **Settings → Apps → ImmichFrame → Storage → Clear Data** to reset the app, then avoid using ImmichFrame's built-in dim/sleep feature. Use **Samsung Routines** for night scheduling instead — it's more reliable and easier to control (see the Night schedule section above).

### ImmichFrame not reachable via Tailscale

If the tablet can't connect to `http://grandmas-frame:8080`:

1. **Check Tailscale status:** `docker exec grandmas_tailscale tailscale status` — verify both the server and tablet appear as connected
2. **Use the Tailscale IP instead of hostname:** The MagicDNS hostname may differ from the Docker hostname. Check the actual name/IP in the [Tailscale admin console](https://login.tailscale.com/admin/machines) and use `http://100.x.y.z:8080`
3. **Check iptables errors:** If `tailscale status` shows iptables permission errors, Tailscale may not be routing traffic properly. Ensure the Tailscale container has `NET_ADMIN` and `SYS_MODULE` capabilities and access to `/dev/net/tun`
4. **Stale network namespace (port 8080 missing from `ss`, connection refused):** `network_mode: service:tailscale` joins ImmichFrame to Tailscale's network namespace at container *creation* time. If the Tailscale container was ever recreated, ImmichFrame ends up in a stale, isolated namespace — `docker inspect` still shows the right container ID but the namespaces no longer match.

   Diagnose:
   ```bash
   ls -la /proc/$(docker inspect -f '{{.State.Pid}}' grandmas_tailscale)/ns/net
   ls -la /proc/$(docker inspect -f '{{.State.Pid}}' immichframe)/ns/net
   # The inode numbers (e.g. net:[4026561809]) must be identical
   ```

   Fix — recreate ImmichFrame so it joins the current namespace:
   ```bash
   docker compose -f docker-compose.yaml -f docker-compose.prod.yaml up -d --force-recreate immichframe
   ```

   **Rule:** whenever you recreate the Tailscale container, always recreate ImmichFrame too. Docker does not cascade recreations automatically.

### Daemon logs not showing (only Uvicorn access lines)

If you only see `INFO: ... "POST /webhook HTTP/1.1" 200 OK` but no app-level logs (event names, group IDs, etc.), Uvicorn's default log level is suppressing them. The Dockerfile should include `--log-level info`:

```dockerfile
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "3000", "--log-level", "info"]
```

Rebuild and restart the daemon after changing.

### Evolution API manager has no login prompt

This is normal — the manager UI doesn't require authentication by default. The `EVOLUTION_API_KEY` is used for API calls, not the web dashboard. Keep the manager behind an SSH tunnel or firewall (never expose port 8080 publicly without additional auth).
