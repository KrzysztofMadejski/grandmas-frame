import base64
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, HTTPException, Request

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
log = logging.getLogger(__name__)

EVOLUTION_API_URL = os.environ["EVOLUTION_API_URL"]
EVOLUTION_API_KEY = os.environ["EVOLUTION_API_KEY"]
IMMICH_URL = os.environ["IMMICH_URL"]
IMMICH_API_KEY = os.environ["IMMICH_API_KEY"]
IMMICH_ALBUM_ID = os.environ["IMMICH_ALBUM_ID"]
WHATSAPP_GROUP_ID = os.environ.get("WHATSAPP_GROUP_ID", "")

log.info("Daemon starting — IMMICH_URL=%s ALBUM_ID=%r GROUP_FILTER=%r", IMMICH_URL, IMMICH_ALBUM_ID, WHATSAPP_GROUP_ID or "(any)")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{IMMICH_URL}/api/albums/{IMMICH_ALBUM_ID}",
            headers={"x-api-key": IMMICH_API_KEY},
        )
        if resp.status_code == 404:
            log.error("Album ID %r not found. Check IMMICH_ALBUM_ID in .env.", IMMICH_ALBUM_ID)
            sys.exit(1)
        resp.raise_for_status()
        log.info("Album %r found — ready.", resp.json().get("albumName"))
    yield


app = FastAPI(lifespan=lifespan)


async def download_media(client: httpx.AsyncClient, instance: str, key: dict, message: dict) -> str:
    """Fetch media from Evolution API as base64."""
    log.info("Downloading media via Evolution API — instance=%s", instance)
    resp = await client.post(
        f"{EVOLUTION_API_URL}/chat/getBase64FromMediaMessage/{instance}",
        headers={"apikey": EVOLUTION_API_KEY},
        json={"message": {"key": key, "message": message}, "convertToMp4": False},
        timeout=60,
    )
    log.debug("Evolution API download response %d: %s", resp.status_code, resp.text[:200])
    resp.raise_for_status()
    media_b64 = resp.json().get("base64")
    if not media_b64:
        raise HTTPException(500, f"Evolution API returned no base64 data. Response: {resp.text[:200]}")
    log.info("Media downloaded — base64 length=%d chars", len(media_b64))
    return media_b64



async def upload_to_immich(
    client: httpx.AsyncClient, photo_data: bytes, filename: str, mimetype: str
) -> str:
    now = datetime.now(timezone.utc).isoformat()
    log.info("Uploading to Immich — filename=%s mimetype=%s size=%d bytes", filename, mimetype, len(photo_data))
    resp = await client.post(
        f"{IMMICH_URL}/api/assets",
        headers={"x-api-key": IMMICH_API_KEY},
        files={"assetData": (filename, photo_data, mimetype)},
        data={
            "deviceAssetId": filename,
            "deviceId": "photos-to-frame-daemon",
            "fileCreatedAt": now,
            "fileModifiedAt": now,
        },
        timeout=60,
    )
    log.debug("Immich upload response %d: %s", resp.status_code, resp.text[:500])
    resp.raise_for_status()
    result = resp.json()
    log.info("Immich upload OK — asset_id=%s status=%s", result.get("id"), result.get("status"))
    return result["id"]


@app.post("/webhook")
async def webhook(request: Request):
    payload = await request.json()

    log.debug("Raw webhook payload:\n%s", json.dumps(payload, indent=2))

    event = payload.get("event")
    log.info("Webhook received — event=%s instance=%s", event, payload.get("instance"))

    if event != "messages.upsert":
        log.info("Ignoring event=%s", event)
        return {"status": "ignored", "reason": f"event={event}"}

    data = payload.get("data", {})
    key = data.get("key", {})
    message = data.get("message", {})

    remote_jid = key.get("remoteJid", "")
    media_id = key.get("id", "unknown")
    message_types = list(message.keys())
    log.info("Message from=%s id=%s types=%s", remote_jid, media_id, message_types)

    if WHATSAPP_GROUP_ID and remote_jid != WHATSAPP_GROUP_ID:
        log.info("Ignoring — remoteJid=%s does not match WHATSAPP_GROUP_ID=%s", remote_jid, WHATSAPP_GROUP_ID)
        return {"status": "ignored", "reason": "not target group"}

    image_msg = message.get("imageMessage")
    if not image_msg:
        log.info("Ignoring — no imageMessage in payload (got: %s)", message_types)
        return {"status": "ignored", "reason": "no image"}

    log.info("Image message found — mimetype=%s caption=%r", image_msg.get("mimetype"), image_msg.get("caption", ""))

    instance = payload.get("instance")
    mimetype = image_msg.get("mimetype", "image/jpeg")
    ext = mimetype.split("/")[-1]
    filename = f"{media_id}.{ext}"

    async with httpx.AsyncClient() as client:
        media_b64 = await download_media(client, instance, key, message)
        photo_data = base64.b64decode(media_b64)

        asset_id = await upload_to_immich(client, photo_data, filename, mimetype)

        log.info("Adding asset %s to album %s", asset_id, IMMICH_ALBUM_ID)

        resp = await client.put(
            f"{IMMICH_URL}/api/albums/{IMMICH_ALBUM_ID}/assets",
            headers={"x-api-key": IMMICH_API_KEY},
            json={"ids": [asset_id]},
        )
        log.debug("Album add response %d: %s", resp.status_code, resp.text[:500])
        resp.raise_for_status()
        log.info("Done — asset %s added to album %s", asset_id, IMMICH_ALBUM_ID)

    return {"status": "ok", "asset_id": asset_id}


@app.get("/health")
async def health():
    return {"status": "ok"}
