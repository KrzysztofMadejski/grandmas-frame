#!/bin/bash
# First-time setup: generates secrets and creates .env from the template.
# Run this once before `docker compose up`.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Helpers ────────────────────────────────────────────────────────────────

gen_password() {
    openssl rand -base64 32 | tr -d '=+/\n' | cut -c1-32
}

# Portable in-place sed (handles both macOS/BSD and Linux/GNU sed)
replace_in_env() {
    local key="$1"
    local value="$2"
    # Escape any / in the value so sed doesn't break
    local escaped_value
    escaped_value=$(printf '%s\n' "$value" | sed 's/[\/&]/\\&/g')
    sed "s|^${key}=.*|${key}=${escaped_value}|" .env > .env.tmp && mv .env.tmp .env
}

# ── Guard ──────────────────────────────────────────────────────────────────

if [ -f .env ]; then
    echo "⚠️  .env already exists."
    read -rp "   Overwrite it? [y/N] " confirm || true
    [[ "$confirm" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }
fi

# ── Copy template ──────────────────────────────────────────────────────────

cp .env.example .env
echo "✔  Copied .env.example → .env"

# ── Generate database passwords ────────────────────────────────────────────

echo ""
echo "Generating database passwords…"
replace_in_env "DB_ADMIN_PASSWORD"    "$(gen_password)"
replace_in_env "IMMICH_DB_PASSWORD"   "$(gen_password)"
replace_in_env "EVOLUTION_DB_PASSWORD" "$(gen_password)"
echo "✔  DB_ADMIN_PASSWORD, IMMICH_DB_PASSWORD, EVOLUTION_DB_PASSWORD set"

# ── Evolution API key ──────────────────────────────────────────────────────

echo ""
read -rp "Evolution API key (press Enter to auto-generate): " EVOLUTION_API_KEY || true
if [ -z "$EVOLUTION_API_KEY" ]; then
    EVOLUTION_API_KEY="$(gen_password)"
    echo "   → Generated: $EVOLUTION_API_KEY"
fi
replace_in_env "EVOLUTION_API_KEY" "$EVOLUTION_API_KEY"
echo "✔  EVOLUTION_API_KEY set"

# ── WhatsApp group JID ─────────────────────────────────────────────────────

echo ""
echo "WhatsApp group JID restricts which group's photos are forwarded to the frame."
echo "Format: 1234567890-1234567890@g.us  (visible in Evolution API dashboard after setup)"
read -rp "Group JID (leave empty to accept from all chats): " WHATSAPP_GROUP_ID || true
if [ -n "$WHATSAPP_GROUP_ID" ]; then
    replace_in_env "WHATSAPP_GROUP_ID" "$WHATSAPP_GROUP_ID"
    echo "✔  WHATSAPP_GROUP_ID set"
else
    echo "   Skipped — accepting photos from all chats"
fi

# ── Photo upload location ──────────────────────────────────────────────────

echo ""
read -rp "Photo storage path on this server [./photos-local-dev]: " UPLOAD_LOCATION || true
if [ -n "$UPLOAD_LOCATION" ]; then
    replace_in_env "UPLOAD_LOCATION" "$UPLOAD_LOCATION"
    echo "✔  UPLOAD_LOCATION set to $UPLOAD_LOCATION"
else
    echo "   Using default: ./photos-local-dev"
fi

# ── Done ───────────────────────────────────────────────────────────────────

echo ""
echo "────────────────────────────────────────────────"
echo "✅  .env is ready. Next steps:"
echo ""
echo "  1.  docker compose up -d"
echo ""
echo "  2.  Open Immich at http://<server>:2283"
echo "      Create an admin account, then:"
echo "      Settings → API Keys → create a key"
echo "      Paste it into .env as IMMICH_API_KEY=<key>"
echo "      docker compose restart photos_to_frame_daemon"
echo ""
echo "  3.  Open Evolution API at http://<server>:8080"
echo "      Create a WhatsApp instance and scan the QR code."
echo "      Set the instance webhook URL to:"
echo "      http://photos_to_frame_daemon:3000/webhook"
echo "      (or http://<server>:3000/webhook if configuring externally)"
echo "────────────────────────────────────────────────"
