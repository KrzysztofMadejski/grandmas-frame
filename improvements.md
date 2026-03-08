# Improvements / TODOs

## Setup UX

- **Guide user through setting WHATSAPP_GROUP_ID**
  After the user sets up a WhatsApp instance in Evolution API and scans the QR code,
  the setup flow should help them find their group JID and write it into `.env`.
  The JID is visible in the Evolution API dashboard when a message is received, or
  via the `/chat/findChats/{instance}` endpoint. The setup script (or a follow-up
  prompt) should explain this and offer to update `.env` automatically.
