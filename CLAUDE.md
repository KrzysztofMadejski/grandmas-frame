# Claude Instructions

## setup.sh

`setup.sh` is an interactive terminal script. It cannot be run via Claude's Bash tool because Claude has no TTY.

When the user asks to run `setup.sh`, do **not** execute it. Instead:

1. Tell the user to run it themselves in a terminal:
   ```
   bash setup.sh
   ```

2. **Or**, offer to generate `.env` directly by replicating the same logic:
   - Copy `.env.example` to `.env`
   - Generate random passwords for `DB_ADMIN_PASSWORD`, `IMMICH_DB_PASSWORD`, `EVOLUTION_DB_PASSWORD`
   - Auto-generate `EVOLUTION_API_KEY`
   - Ask the user for `WHATSAPP_GROUP_ID` and `UPLOAD_LOCATION` (or use defaults)
   - Write the filled-in `.env` file

Ask the user which they prefer before proceeding.

## Evolution API

- **Use `evoapicloud/evolution-api`**, not `atendai/evolution-api`. The `atendai` image is abandoned and stuck at v2.2.3 which has a QR code reconnection loop bug (fixed in v2.3.7 on `evoapicloud`).
- Always use `EVOLUTION_INSTANCE_ID` from `.env` when making API calls — never the display name.
- After upgrading to v2.3.7 the instance status shows `close` on startup and requires manually clicking "Get QR Code" in the manager — this is correct behaviour (the reconnection loop is gone).

## Postgres

- `init-db.sh` must be executable (`chmod +x`) before the postgres container first starts, otherwise postgres skips it silently.

## Learnings

<!-- Added: 2026-04-10 -->
- When debugging missing daemon logs: Uvicorn suppresses app-level logs by default — Dockerfile CMD needs `--log-level info` to see both access logs and app logs.
- Mikrus VPS doesn't support swap (`swapon` fails with "Operation not permitted") — it's container-based hosting where the host controls swap.
