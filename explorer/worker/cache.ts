import type { MatchResult } from "../src/lib/types";
import type { Env } from "./env";

const PREFIX = "match:v1:";
const TTL_SECONDS = 60 * 60 * 24 * 30;

export function normalizeQuery(text: string): string {
  return text.trim().replace(/\s+/g, " ").toLowerCase();
}

export async function hashText(text: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

export async function getCached(env: Env, key: string): Promise<MatchResult | null> {
  const raw = await env.MATCH_CACHE.get(`${PREFIX}${key}`);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as MatchResult;
  } catch {
    return null;
  }
}

export async function putCached(env: Env, key: string, result: MatchResult): Promise<void> {
  await env.MATCH_CACHE.put(`${PREFIX}${key}`, JSON.stringify(result), {
    expirationTtl: TTL_SECONDS,
  });
}
