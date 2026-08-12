# crawler

Cloudflare Worker that crawls `sfia-online.org/en/sfia-9` via Cloudflare's
Browser Rendering `/crawl` REST endpoint and stores the result as one JSON
object in R2.

## Endpoints

- `POST /crawl` — starts a crawl job.
- `GET /crawl/:jobId` — polls a job; on completion, writes the combined
  dataset to R2 as `sfia-crawl.json`.
- `GET /dataset` — returns the stored dataset.

## Setup

1. `wrangler login`.
2. Create a Cloudflare API token scoped **Browser Rendering - Edit**
   (separate from the wrangler login OAuth token). Store it:
   `wrangler secret put CF_API_TOKEN`.
3. `npm install && npm run deploy`.

## Not yet done

- Not deployed, not run against the live site yet.
- `records[].markdown` is raw per-page markdown, not parsed into a
  skills/levels structure — separate downstream step.
