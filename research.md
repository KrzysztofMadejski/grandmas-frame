# Digital Photo Frame Research

## Goal

Buy or build a digital photo frame for elderly parents with:
- Remote photo upload (no action required from parents)
- WhatsApp as the sending mechanism
- Multiple family members able to send photos
- Video support (nice to have)

## Types of Digital Photo Frames

1. **Wi-Fi + app-based** — photos pushed via mobile app or email. Parents do nothing. Most popular category. Examples: Aura, Nixplay, Frameo, Pix-Star.
2. **LTE/SIM-based** — works without home Wi-Fi (like a phone). More expensive + monthly subscription. Examples: Familink (4G), some Pix-Star models.
3. **Smart display** (Amazon Echo Show, Google Nest Hub) — voice assistants with photo frame mode. Not purpose-built.
4. **USB/SD only** — no remote upload, irrelevant for this use case.

## Key Specs to Look For

| Parameter | Notes |
|---|---|
| Resolution | Min 1024x768, good is 1920x1080 (FHD) |
| Screen size | 8-15". 10" = diagonal (~22x13 cm). For poor eyesight consider 12-15" |
| Brightness | Min 250-400 nits if near a window |
| Internal storage | 4-32 GB |
| Connectivity | Wi-Fi 2.4/5 GHz |
| Controls | Touch, remote, app |
| Extras | Motion sensor (auto off), night mode |

## Price Ranges (Polish market, 2024-2025)

**Wi-Fi frames:**
- Budget (Frameo-based brands): 200-400 PLN
- Mid-range (Nixplay, Rollei): 400-700 PLN
- Premium (Aura): 800-1400 PLN

**LTE/SIM frames:**
- Hardware: 600-1000 PLN + 5-15 EUR/month subscription
- Not recommended if parents have home Wi-Fi

## Video Support

Most Wi-Fi frames support MP4 from ~300 PLN. No significant extra cost. Watch out for:
- Clip length limits (some cap at 15-30 sec)
- Audio quality (cheap frames have poor or no speaker)

## WhatsApp Integration — Market Findings

**Key finding: WhatsApp Business API does not allow adding business numbers to group chats.**

### Familink
- Only commercial frame brand with **native WhatsApp support** (+ Messenger, Telegram, email)
- Photos sent 1-on-1 to the frame's WhatsApp number (not via group)
- Multiple frames: each frame has its own number, must send separately
- Available in Poland, Wi-Fi and 4G versions, ~600-800 PLN + optional subscription
- Source: https://www.familinkframe.com/en/

### Aura "Text to Frame" (launched Dec 2025)
- Send photos via SMS to a unique frame number, no app needed
- **Limitation: US phone numbers only (+1 country code)**
- Does not work from Poland
- Source: https://help.auraframes.com/hc/en-us/articles/36558577656599

### Nixplay / Frameo / Skylight
- No native WhatsApp support
- Workaround: save photo from WhatsApp, upload via app — extra step

### Conclusion
**Familink is the only realistic option for Polish users requiring WhatsApp.**
But: you cannot use it in a family group chat, and one photo does not automatically go to multiple frames.

## DIY / Open Source Stack

For full WhatsApp group chat support and multi-frame delivery, a DIY approach is needed.

### Recommended Stack

```
Family sends photo to WhatsApp (personal number or group)
        |
  WhatsApp gateway (WAHA or Evolution API)
  listens for incoming media, triggers webhook
        |
  Glue script (Python or Node.js, ~50-100 lines)
  downloads photo, calls Immich API
        |
  Immich (self-hosted photo server)
  stores photo in "frame" album
        |
  ImmichFrame on Raspberry Pi / old tablet / Android
  displays slideshow from the album
```

### Component Details

| Component | Project | Language | Notes |
|---|---|---|---|
| WhatsApp gateway | WAHA | Go + Node.js | Recommended — clean, Docker, free for 1 session |
| WhatsApp gateway (alt) | Evolution API | Node.js/NestJS | Richer ecosystem, messier codebase |
| WhatsApp library (DIY) | whatsapp-web.js | Node.js | Library only, no REST API out of box |
| Photo storage | Immich | Node.js + Python | Best self-hosted photo server, very active |
| Frame display | ImmichFrame | C# / ASP.NET + Svelte | Runs on Pi, tablet, Android, Apple TV |

## WhatsApp Gateway Comparison

| | whatsapp-web.js | Evolution API | WAHA | WPPConnect | Venom Bot |
|---|---|---|---|---|---|
| Type | Library | API server | API server | Library/server | Library |
| Language | Node.js/TS | Node.js/TS | Go + Node.js | Node.js/TS | Node.js |
| GitHub stars | ~21k | ~13k | ~6k | ~12k | ~9k |
| WA engine | Puppeteer | Baileys | WEBJS / Baileys / Go | Puppeteer | Puppeteer |
| REST API ready | No | Yes | Yes | Yes | No |
| Docker | No | Yes | Yes | Yes | No |
| Multi-session | Manual | Yes | Plus (paid) | Yes | Manual |
| Session persistence | Manual | Yes | Yes | Yes | Manual |
| Webhooks | Manual | Yes | Yes | Yes | No |
| Dashboard UI | No | Yes | Yes | Yes | No |
| Rich integrations | No | Yes (Chatwoot, OpenAI…) | No | No | No |
| Official WA Cloud API | No | Yes (fallback) | No | No | No |
| Code quality | Good | Messy | Clean | Good | Fair |
| Community language | EN | Mostly PT (Brazilian) | EN | EN/PT | EN |
| Free tier | Full | Full | Core (1 session) | Full | Full |
| Activity | Active | Active | Very active | Slower | Slower |

## Baileys vs Evolution API

**Baileys** is the underlying library Evolution API builds on. It connects to WhatsApp via WebSocket (no browser needed) — lightweight and fast.

**Evolution API adds on top of Baileys:**
- Ready-made REST API and webhooks
- Multi-session management
- Session persistence across restarts (no QR re-scan)
- Dashboard UI
- Event streaming (RabbitMQ, Kafka, SQS)
- Integrations with Chatwoot, Typebot, OpenAI, Dify
- Optional fallback to official WhatsApp Cloud API
- Docker Compose deployment

**Using Baileys directly makes sense when:**
- You need 1 session only
- You want to write the integration code yourself
- You want minimal infrastructure footprint

## Ban Risk (All Unofficial APIs)

All unofficial WhatsApp libraries (whatsapp-web.js, Baileys, WAHA, Evolution API) violate WhatsApp ToS.
Meta can ban the account at any time.

**Best practice:** use a dedicated secondary number (SIM or eSIM), not your main number.
Evolution API and WAHA have slightly better track records due to large user bases and fast protocol updates.

## Recommendation for This Use Case

**Commercial route (simplest):** Familink Wi-Fi version — native WhatsApp, no server needed. Limitation: no group chat, one number per frame.

**DIY route (full control):** WAHA Core (free) + Immich + ImmichFrame on Raspberry Pi or old tablet. Requires a VPS or home server and ~a few hours of setup. Glue code is ~50-100 lines of Python or Node.js.

## Open Questions / To Explore

- [ ] Exact Familink Wi-Fi pricing and model availability in Poland
- [ ] WAHA Core limitations vs Plus in detail
- [ ] Immich + ImmichFrame setup guide
- [ ] Whether WhatsApp personal number bot (via WAHA) risks ban for low-volume family use
- [ ] Hardware: Raspberry Pi vs old Android tablet for ImmichFrame
