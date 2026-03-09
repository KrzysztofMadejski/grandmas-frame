#!/usr/bin/env python3
"""
backfill.py — One-time backfill of historical WhatsApp group photos to Immich.

Reads config from .env. Connects to an Evolution API instance (the "service bot")
and fetches all imageMessage/videoMessage from the target group, uploading each
to Immich and adding to the configured album.

Usage:
    python backfill.py                # full backfill
    python backfill.py --dry-run      # count messages without uploading
    python backfill.py --list-groups  # list WhatsApp groups the bot is in, then exit
"""

import argparse
import base64
import logging
import os
import sys
from datetime import datetime, timezone

import httpx
from dotenv import load_dotenv  # type: ignore

load_dotenv()

EVOLUTION_API_URL = os.environ.get("EVOLUTION_API_URL", "").rstrip("/")
EVOLUTION_API_KEY = os.environ.get("EVOLUTION_API_KEY", "")
USER_BACKFILL_EVOLUTION_INSTANCE_NAME = os.environ.get("USER_BACKFILL_EVOLUTION_INSTANCE_NAME", "")
IMMICH_URL = os.environ.get("IMMICH_URL", "").rstrip("/")
IMMICH_API_KEY = os.environ.get("IMMICH_API_KEY", "")
IMMICH_ALBUM_ID = os.environ.get("IMMICH_ALBUM_ID", "")
WHATSAPP_GROUP_ID = os.environ.get("WHATSAPP_GROUP_ID", "")

PAGE_SIZE = 50

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s — %(message)s",
)
log = logging.getLogger(__name__)


def check_config(require_group: bool = True) -> None:
    missing = [
        v for v in ["EVOLUTION_API_URL", "EVOLUTION_API_KEY", "USER_BACKFILL_EVOLUTION_INSTANCE_NAME",
                    "IMMICH_URL", "IMMICH_API_KEY", "IMMICH_ALBUM_ID"]
        if not os.environ.get(v)
    ]
    if require_group and not WHATSAPP_GROUP_ID:
        missing.append("WHATSAPP_GROUP_ID")
    if missing:
        log.error("Missing required env vars: %s", ", ".join(missing))
        log.error("Set them in .env and re-run. See backfill.md for setup instructions.")
        sys.exit(1)


def list_groups(client: httpx.Client) -> list[dict]:
    """Return all groups the instance belongs to."""
    resp = client.get(
        f"{EVOLUTION_API_URL}/group/fetchAllGroups/{USER_BACKFILL_EVOLUTION_INSTANCE_NAME}",
        headers={"apikey": EVOLUTION_API_KEY},
        params={"getParticipants": "false"},
        timeout=120,
    )
    log.debug("fetchAllGroups %d: %s", resp.status_code, resp.text[:300])
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, list) else []


def fetch_messages(client: httpx.Client, message_type: str) -> list[dict]:
    """Fetch all messages of a given type from the target group, paginated."""
    messages: list[dict] = []
    seen_ids: set[str] = set()
    offset = 0
    consecutive_empty_pages = 0
    while True:
        resp = client.post(
            f"{EVOLUTION_API_URL}/chat/findMessages/{USER_BACKFILL_EVOLUTION_INSTANCE_NAME}",
            headers={"apikey": EVOLUTION_API_KEY},
            json={
                "where": {
                    "key": {"remoteJid": WHATSAPP_GROUP_ID},
                    "messageType": message_type,
                },
                "limit": PAGE_SIZE,
                "offset": offset,
            },
            timeout=300,
        )
        log.debug("findMessages %s offset=%d → %d: %s",
                  message_type, offset, resp.status_code, resp.text[:200])
        resp.raise_for_status()

        data = resp.json()
        # Handle both list response and nested {"messages": {"records": [...]}} structure
        if isinstance(data, list):
            raw_page = data
        elif isinstance(data, dict):
            inner = data.get("messages", data)
            if isinstance(inner, dict):
                raw_page = inner.get("records", [])
            elif isinstance(inner, list):
                raw_page = inner
            else:
                raw_page = []
        else:
            raw_page = []

        if not raw_page:
            break

        count_before = len(messages)
        for m in raw_page:
            msg_id = m.get("key", {}).get("id")
            if m.get("key", {}).get("remoteJid") == WHATSAPP_GROUP_ID and msg_id not in seen_ids:
                seen_ids.add(msg_id)
                messages.append(m)

        new_count = len(messages) - count_before
        log.info("findMessages offset=%d raw=%d new=%d total=%d",
                 offset, len(raw_page), new_count, len(messages))

        if len(raw_page) < PAGE_SIZE:
            # Normal end of results
            break

        if new_count == 0:
            # This page added nothing new — API may be cycling. Allow a few retries
            # in case it's a one-off glitch (e.g. offset=50 repeats but offset=100 is fresh).
            consecutive_empty_pages += 1
            if consecutive_empty_pages >= 3:
                log.warning("3 consecutive pages with no new messages at offset=%d — stopping", offset)
                break
        else:
            consecutive_empty_pages = 0

        offset += PAGE_SIZE

    return messages


def download_media(client: httpx.Client, key: dict, message: dict) -> str:
    """Download media from Evolution API, return base64 string."""
    resp = client.post(
        f"{EVOLUTION_API_URL}/chat/getBase64FromMediaMessage/{USER_BACKFILL_EVOLUTION_INSTANCE_NAME}",
        headers={"apikey": EVOLUTION_API_KEY},
        json={"message": {"key": key, "message": message}, "convertToMp4": False},
        timeout=60,
    )
    log.debug("getBase64FromMediaMessage %d: %s", resp.status_code, resp.text[:200])
    resp.raise_for_status()
    media_b64 = resp.json().get("base64")
    if not media_b64:
        raise ValueError(f"No base64 in Evolution API response: {resp.text[:200]}")
    return media_b64


def upload_to_immich(
    client: httpx.Client,
    photo_data: bytes,
    filename: str,
    mimetype: str,
    created_at: str,
) -> dict:
    """Upload an asset to Immich. Returns the response dict with 'id' and 'status'."""
    resp = client.post(
        f"{IMMICH_URL}/api/assets",
        headers={"x-api-key": IMMICH_API_KEY},
        files={"assetData": (filename, photo_data, mimetype)},
        data={
            "deviceAssetId": filename,
            "deviceId": "backfill-script",
            "fileCreatedAt": created_at,
            "fileModifiedAt": created_at,
        },
        timeout=60,
    )
    log.debug("Immich upload %d: %s", resp.status_code, resp.text[:500])
    resp.raise_for_status()
    return resp.json()


def add_to_album(client: httpx.Client, asset_id: str) -> None:
    """Add an asset to the configured Immich album."""
    resp = client.put(
        f"{IMMICH_URL}/api/albums/{IMMICH_ALBUM_ID}/assets",
        headers={"x-api-key": IMMICH_API_KEY},
        json={"ids": [asset_id]},
    )
    log.debug("Album add %d: %s", resp.status_code, resp.text[:200])
    resp.raise_for_status()


def process_messages(messages: list[dict], dry_run: bool) -> tuple[int, int, int]:
    """
    Upload each message's media to Immich and add to album.
    Returns (uploaded, duplicates, errors).
    """
    uploaded = duplicates = errors = 0
    total = len(messages)

    with httpx.Client() as client:
        for i, msg in enumerate(messages, 1):
            key = msg.get("key", {})
            message = msg.get("message", {})
            msg_id = key.get("id", f"unknown_{i}")

            img = message.get("imageMessage")
            vid = message.get("videoMessage")
            if img:
                media_obj = img
            elif vid:
                media_obj = vid
            else:
                log.debug("[%d/%d] No media in message %s — skipping", i, total, msg_id)
                continue

            mimetype = media_obj.get("mimetype", "image/jpeg")
            ext = mimetype.split("/")[-1].split(";")[0]
            if ext == "jpeg":
                ext = "jpg"
            filename = f"{msg_id}.{ext}"

            ts = msg.get("messageTimestamp") or msg.get("timestamp")
            created_at = (
                datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()
                if ts else datetime.now(timezone.utc).isoformat()
            )

            log.info("[%d/%d] %s %s (sent %s)",
                     i, total, "imageMessage" if img else "videoMessage",
                     filename, created_at[:10])

            if dry_run:
                log.info("[%d/%d] DRY RUN — would upload %s", i, total, filename)
                uploaded += 1
                continue

            # Download
            try:
                media_b64 = download_media(client, key, message)
                photo_data = base64.b64decode(media_b64)
            except Exception as exc:
                log.warning("[%d/%d] Download failed for %s: %s", i, total, filename, exc)
                errors += 1
                continue

            # Upload to Immich
            try:
                result = upload_to_immich(client, photo_data, filename, mimetype, created_at)
                asset_id = result["id"]
                status = result.get("status", "created")
            except Exception as exc:
                log.warning("[%d/%d] Upload failed for %s: %s", i, total, filename, exc)
                errors += 1
                continue

            if status == "duplicate":
                log.info("[%d/%d] Already in Immich — skipping album add (%s)", i, total, filename)
                duplicates += 1
                continue

            # Add to album
            try:
                add_to_album(client, asset_id)
                log.info("[%d/%d] Done — %s → asset %s", i, total, filename, asset_id)
                uploaded += 1
            except Exception as exc:
                log.warning("[%d/%d] Uploaded but album add failed for %s: %s",
                            i, total, filename, exc)
                errors += 1

    return uploaded, duplicates, errors


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill historical WhatsApp group photos to Immich"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Fetch and count messages without downloading or uploading",
    )
    parser.add_argument(
        "--list-groups", action="store_true",
        help="List WhatsApp groups the bot is in and exit",
    )
    args = parser.parse_args()

    if args.list_groups:
        check_config(require_group=False)
        with httpx.Client() as client:
            groups = list_groups(client)
        if not groups:
            print("No groups found. Make sure the instance is connected to WhatsApp.")
            sys.exit(1)
        print(f"\nFound {len(groups)} group(s):\n")
        for g in groups:
            jid = g.get("id") or g.get("remoteJid") or g.get("groupJid", "?")
            name = g.get("subject") or g.get("name", "(no name)")
            print(f"  {jid}  —  {name}")
        print(f"\nSet WHATSAPP_GROUP_ID=<jid> in .env, then run: python backfill.py")
        return

    check_config(require_group=True)

    log.info(
        "Backfill starting — instance=%s group=%s album=%s%s",
        USER_BACKFILL_EVOLUTION_INSTANCE_NAME, WHATSAPP_GROUP_ID, IMMICH_ALBUM_ID,
        " [DRY RUN]" if args.dry_run else "",
    )

    with httpx.Client() as client:
        log.info("Fetching image messages from group…")
        image_msgs = fetch_messages(client, "imageMessage")
        log.info("Fetching video messages from group…")
        video_msgs = fetch_messages(client, "videoMessage")

    all_msgs = image_msgs + video_msgs
    log.info(
        "Found %d images + %d videos = %d total",
        len(image_msgs), len(video_msgs), len(all_msgs),
    )

    if not all_msgs:
        log.info("Nothing to process — exiting.")
        return

    uploaded, duplicates, errors = process_messages(all_msgs, dry_run=args.dry_run)

    print("\n" + "=" * 52)
    print(f"  Backfill {'(DRY RUN) ' if args.dry_run else ''}complete")
    print(f"  Total found:  {len(all_msgs)}")
    print(f"  Uploaded:     {uploaded}")
    print(f"  Duplicates:   {duplicates}  (already in Immich)")
    print(f"  Errors:       {errors}")
    print("=" * 52 + "\n")


if __name__ == "__main__":
    main()
