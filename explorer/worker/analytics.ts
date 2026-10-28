import type { Env } from "./env";

type QueryEvent = {
  queryHash: string;
  text: string;
  source: "live";
  ok: boolean;
  matches: number;
  elapsedMs: number;
  model: string;
};

export function logQuery(env: Env, event: QueryEvent): void {
  try {
    env.QUERIES.writeDataPoint({
      indexes: [event.queryHash],
      blobs: [
        event.text.slice(0, 2000),
        event.source,
        event.ok ? "ok" : "error",
        event.model,
      ],
      doubles: [event.matches, event.elapsedMs],
    });
  } catch {
    // Analytics must never break a match request.
  }
}

export async function hashQuery(text: string): Promise<string> {
  const normalized = text.trim().replace(/\s+/g, " ").toLowerCase();
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(normalized));
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}
