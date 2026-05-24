# Next steps

## Done

- [x] VPS setup — all services running with mikrus35 overlay
- [x] Evolution API — WhatsApp instance connected, webhook configured
- [x] Tailscale — server and tablet connected
- [x] End-to-end test — photo sent to WhatsApp group appears in Immich album
- [x] ImmichFrame — tablet showing photos via Tailscale
- [x] Tablet kiosk mode — battery protection, Wi-Fi reliability, DND, etc.
- [x] Night schedule — Samsung Routines, 1% brightness at night
- [x] Troubleshooting section — updated with issues found during setup
- [x] Daemon logging — Uvicorn --log-level info fix
- [x] Temp files cleaned — /tmp/babcia-upload removed from VPS

## TODO

- [ ] **Set up backups** — cron job for Postgres dumps and/or photo directory rsync
- [ ] **Commit and push** — SETUP.md, docker-compose.mikrus35.yaml, Dockerfile changes uncommitted locally
- [ ] **Update SETUP.md** — review single-admin-account docs for consistency
