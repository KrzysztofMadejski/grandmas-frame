# Improvements / TODOs

## WhatsApp history backfill

- **Script to backfill media from an existing user account via Evolution API**
  Rather than connecting as the bot account (which has no message history), build a
  backfill script that authenticates as an existing group member's account, iterates
  through all messages in the group via `findMessages` + pagination, downloads each
  media item using `getBase64FromMediaMessage`, and uploads directly to Immich via
  the API or CLI. This is preferable to the mobile app backup approach because it
  only picks up group photos (not all WhatsApp media from all chats) and is
  fully automated. The instance would be a temporary one connected on a member's
  number just for the backfill, then disconnected.

## Setup UX

- **Guide user through setting WHATSAPP_GROUP_ID**
  After the user sets up a WhatsApp instance in Evolution API and scans the QR code,
  the setup flow should help them find their group JID and write it into `.env`.
  The JID is visible in the Evolution API dashboard when a message is received, or
  via the `/chat/findChats/{instance}` endpoint. The setup script (or a follow-up
  prompt) should explain this and offer to update `.env` automatically.
