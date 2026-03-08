# Python vs Node.js for photos_to_frame_daemon

## Decision: Python

The daemon is ~50–100 lines of pure I/O glue: receive a webhook, download media via HTTP, upload to Immich via HTTP. Either runtime is equally capable here.

**Python was chosen** because the primary maintainer prefers it.

## Why Node.js would also be a valid choice

- Evolution API (the WhatsApp gateway) is Node.js — same runtime across the whole stack
- The Evolution API JS client/types are available natively
- `node:alpine` base image is marginally smaller
- Consistent mental model when debugging the full pipeline

## When to consider rewriting to Node.js

- If the maintainer changes and the new owner is more comfortable with Node
- If you need to use Evolution API's JS SDK directly (e.g. for advanced session management)
- If you want to consolidate Docker base images for size/security reasons
