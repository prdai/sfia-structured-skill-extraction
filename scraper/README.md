# scraper

Cloudflare Worker that crawls sfia-online.org with Browser Rendering and
stores the full skill dataset as JSON in R2.

Not deployed yet. `POST /scrape` crawls, `GET /dataset` returns the stored
JSON. Until it runs against the real site, `../data/sfia-dataset.json` is a
hand-written placeholder with the same shape.

The DOM selectors in `src/index.ts` are best-guess against the current SFIA
site layout and need verifying against the live pages before first deploy.
