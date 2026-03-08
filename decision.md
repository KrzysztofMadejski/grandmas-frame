# Decision: DIY Stack

## Chosen Architecture

```
Family sends photo to WhatsApp group
        |
  Evolution API (WhatsApp gateway)
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

## Components

| Component | Choice |
|---|---|
| WhatsApp gateway | Evolution API |
| Photo storage | Immich |
| Frame display | ImmichFrame |
| Glue | Custom script (Python or Node.js) |

## Rationale

- **Commercial route rejected**: Familink lacks group chat support — each family member must send to the frame's number individually, and each frame needs a separate send.
- **Evolution API over WAHA**: Evolution API has richer ecosystem, multi-session support, built-in REST API, webhooks, and session persistence. WAHA Core (free tier) is limited to 1 session but Evolution API is fully free.
- **Immich**: Best self-hosted photo server, very active development, has a well-documented API for programmatic photo upload.
- **ImmichFrame**: Purpose-built slideshow display for Immich albums, runs on Raspberry Pi, Android tablet, and Apple TV.

## Trade-offs

- Requires a VPS or home server to run Evolution API + Immich
- WhatsApp unofficial API carries ban risk — use a dedicated secondary number, not the main family number
- Setup effort: estimated a few hours
