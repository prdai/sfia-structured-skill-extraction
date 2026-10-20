import type { Env } from "./env";

type QueryEvent = {
  queryHash: string;
  text: string;
  source: "live" | "cache";
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
