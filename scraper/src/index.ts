import puppeteer from "@cloudflare/puppeteer";

interface Env {
  BROWSER: Fetcher;
  DATASET: R2Bucket;
}

interface SkillRecord {
  code: string;
  name: string;
  category: string;
  description: string;
  levels: Record<string, string>;
}

const SFIA_BASE = "https://sfia-online.org/en/sfia-9";
const SKILLS_INDEX = `${SFIA_BASE}/all-skills-a-z`;
const DATASET_KEY = "sfia-dataset.json";

// Crawls the SFIA skills index, then each skill page, and stores the full
// dataset as one JSON object in R2. Triggered manually via HTTP for now.
export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/dataset") {
      const obj = await env.DATASET.get(DATASET_KEY);
      if (!obj) return new Response("dataset not scraped yet", { status: 404 });
      return new Response(obj.body, {
        headers: { "content-type": "application/json" },
      });
    }

    if (url.pathname !== "/scrape") {
      return new Response("POST /scrape to crawl, GET /dataset to read", {
        status: 404,
      });
    }

    const browser = await puppeteer.launch(env.BROWSER);
    try {
      const page = await browser.newPage();
      await page.goto(SKILLS_INDEX, { waitUntil: "networkidle0" });

      // Skill pages are linked from the A-Z index.
      const skillLinks: string[] = await page.$$eval(
        "a[href*='/skills/']",
        (as) => [...new Set(as.map((a) => (a as HTMLAnchorElement).href))]
      );

      const skills: SkillRecord[] = [];
      for (const link of skillLinks) {
        await page.goto(link, { waitUntil: "networkidle0" });
        const record = await page.evaluate(() => {
          const text = (sel: string) =>
            document.querySelector(sel)?.textContent?.trim() ?? "";
          // Level descriptions are rendered as one block per level, with the
          // numeric level in a heading.
          const levels: Record<string, string> = {};
          for (const block of document.querySelectorAll("[class*='level']")) {
            const heading = block.querySelector("h1,h2,h3,h4")?.textContent ?? "";
            const match = heading.match(/\b([1-7])\b/);
            const body = block.querySelector("p")?.textContent?.trim() ?? "";
            if (match && body) levels[match[1]] = body;
          }
          return {
            code: text("[class*='skill-code'], .code"),
            name: text("h1"),
            category: text("[class*='category']"),
            description: text("[class*='overall-description'], .description p"),
            levels,
          };
        });
        if (record.name) skills.push(record);
      }

      const dataset = {
        source: SFIA_BASE,
        version: "sfia-9",
        scrapedAt: new Date().toISOString(),
        skills,
      };
      await env.DATASET.put(DATASET_KEY, JSON.stringify(dataset, null, 2), {
        httpMetadata: { contentType: "application/json" },
      });

      return Response.json({ scraped: skills.length });
    } finally {
      await browser.close();
    }
  },
} satisfies ExportedHandler<Env>;
