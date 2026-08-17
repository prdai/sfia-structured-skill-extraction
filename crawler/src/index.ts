interface Env {
  DATASET: R2Bucket;
  CF_ACCOUNT_ID: string;
  CF_API_TOKEN: string;
}

const SFIA_ROOT = "https://sfia-online.org/en/sfia-9";
const DATASET_KEY = "sfia-crawl.json";

async function cfFetch(env: Env, path: string, init?: RequestInit): Promise<any> {
  const res = await fetch(
    `https://api.cloudflare.com/client/v4/accounts/${env.CF_ACCOUNT_ID}/browser-rendering/crawl${path}`,
    {
      ...init,
      headers: {
        Authorization: `Bearer ${env.CF_API_TOKEN}`,
        "Content-Type": "application/json",
      },
    }
  );
  return { status: res.status, body: await res.json() };
}

async function startCrawl(env: Env): Promise<Response> {
  const { status, body } = await cfFetch(env, "", {
    method: "POST",
    body: JSON.stringify({
      url: SFIA_ROOT,
      limit: 100000,
      depth: 100000,
      formats: ["markdown", "html"],
      source: "all",
      options: {
        includePatterns: [`${SFIA_ROOT}/**`],
        includeSubdomains: false,
        includeExternalLinks: false,
      },
    }),
  });
  return Response.json(body, { status });
}

async function collectCrawl(env: Env, jobId: string): Promise<Response> {
  const { body: statusBody } = await cfFetch(env, `/${jobId}`);
  const status = statusBody.result?.status;

  if (status !== "completed") {
    return Response.json({ jobId, status });
  }

  const records: unknown[] = [];
  let cursor: string | undefined;
  do {
    const { body } = await cfFetch(
      env,
      `/${jobId}${cursor ? `?cursor=${cursor}` : ""}`
    );
    records.push(...(body.result?.records ?? []));
    cursor = body.result?.cursor;
  } while (cursor);

  const dataset = {
    source: SFIA_ROOT,
    version: "sfia-9",
    jobId,
    crawledAt: new Date().toISOString(),
    pageCount: records.length,
    records,
  };
  await env.DATASET.put(DATASET_KEY, JSON.stringify(dataset, null, 2), {
    httpMetadata: { contentType: "application/json" },
  });

  return Response.json({ jobId, status, pageCount: records.length });
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const collectMatch = url.pathname.match(/^\/crawl\/(.+)$/);

    switch (true) {
      case url.pathname === "/crawl" && request.method === "POST":
        return startCrawl(env);

      case !!collectMatch:
        return collectCrawl(env, collectMatch![1]);

      case url.pathname === "/dataset": {
        const obj = await env.DATASET.get(DATASET_KEY);
        if (!obj) return new Response("dataset not crawled yet", { status: 404 });
        return new Response(obj.body, {
          headers: { "content-type": "application/json" },
        });
      }

      default:
        return new Response(
          "POST /crawl to start a job, GET /crawl/:jobId to poll/collect, GET /dataset to read",
          { status: 404 }
        );
    }
  },
} satisfies ExportedHandler<Env>;
