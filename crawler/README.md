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
2. Create the R2 bucket if it does not already exist:
   `npx wrangler r2 bucket create sfia-dataset`.
3. Create a Cloudflare API token scoped **Browser Rendering - Edit**
   (separate from the wrangler login OAuth token). Store it:
   `wrangler secret put CF_API_TOKEN`.
4. `npm install && npm run deploy`.

## Not yet done

- The checked-in dataset was produced by a completed live-site crawl.
  Deployment status is not recorded in this repository.
- `records[].markdown` and `records[].html` are raw per-page content,
  not parsed into a skills/levels structure — separate downstream step
  (`structured-extraction/`). The `html` field only exists in crawls
  made after the formats change to `["markdown", "html"]`.
