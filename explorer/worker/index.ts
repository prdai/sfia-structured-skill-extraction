import {
  createUIMessageStream,
  createUIMessageStreamResponse,
  type UIMessage,
} from "ai";

import type { MatchResult } from "../src/lib/types";
import { runAgent } from "./agent";
import { logQuery } from "./analytics";
import { getCached, hashText, normalizeQuery, putCached } from "./cache";
import type { Env } from "./env";
import { verifyTurnstile } from "./turnstile";

export { Budget } from "./budget";

type MatchBody = {
  messages?: UIMessage[];
  text?: string;
  turnstileToken?: string;
};

type BudgetDecision = {
  ok: boolean;
  reason?: "budget_exhausted" | "ip_limited";
  remaining?: { month: number; day: number };
};

const MAX_INPUT = 6000;
const MIN_INPUT = 20;
const PER_IP_DAILY = 3;

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/api/health") {
      return Response.json({ ok: true });
    }

    if (url.pathname !== "/api/match") {
      return env.ASSETS.fetch(request);
    }

    if (request.method !== "POST") {
      return new Response("Method not allowed", { status: 405 });
    }

    if (!originAllowed(request, env)) {
      return errorResponse(403, "origin_rejected", "This endpoint only accepts requests from sfia.prdai.dev.");
    }

    const contentLength = Number(request.headers.get("content-length") ?? "0");
    if (contentLength > 32_000) {
      return errorResponse(413, "invalid_input", "That description is too large. Keep it under 6,000 characters.");
    }

    let body: MatchBody;
    try {
      body = (await request.json()) as MatchBody;
    } catch {
      return errorResponse(400, "invalid_input", "Invalid request body.");
    }

    const text = (body.text ?? extractText(body.messages)).trim();
    if (text.length < MIN_INPUT) {
      return errorResponse(400, "invalid_input", "Add a little more detail before analyzing.");
    }
    if (text.length > MAX_INPUT) {
      return errorResponse(413, "invalid_input", "That description is too long. Keep it under 6,000 characters.");
    }

    const ip = request.headers.get("CF-Connecting-IP") ?? "unknown";
    const ipHash = await hashText(ip);
    const queryHash = await hashText(normalizeQuery(text));

    if (!(await verifyTurnstile(env, body.turnstileToken, ip))) {
      return errorResponse(403, "turnstile_failed", "Verification failed. Reload the page and try again.");
    }

    const cached = await getCached(env, queryHash);
    if (cached) {
      const result: MatchResult = { ...cached, meta: { ...cached.meta, cached: true } };
      logQuery(env, {
        queryHash,
        text,
        source: "cache",
        ok: true,
        matches: result.matches.length,
        elapsedMs: 0,
        model: result.meta.model,
      });
      return cachedResponse(result);
    }

    const budget = env.BUDGET.get(env.BUDGET.idFromName("global"));
    const reservation = await reserve(budget, {
      ipHash,
      limitPerIp: PER_IP_DAILY,
      globalLimit: Number(env.MONTHLY_MATCH_BUDGET) || 500,
    });

    if (!reservation.ok) {
      const message =
        reservation.reason === "budget_exhausted"
          ? "This month's demo budget is exhausted. Try again next month."
          : `Daily limit reached (${PER_IP_DAILY} analyses per person). Try again tomorrow.`;
      return errorResponse(429, reservation.reason ?? "rate_limited", message);
    }

    const startedAt = Date.now();
    const agentMessages: UIMessage[] = body.text
      ? [
          {
            id: crypto.randomUUID(),
            role: "user",
            parts: [{ type: "text", text }],
          },
        ]
      : (body.messages ?? []);

    try {
      const result = await runAgent(env, agentMessages, startedAt, {
        onFinal: async (final) => {
          await putCached(env, queryHash, final);
          logQuery(env, {
            queryHash,
            text,
            source: "live",
            ok: true,
            matches: final.matches.length,
            elapsedMs: final.meta.elapsedMs,
            model: final.meta.model,
          });
        },
        onError: (error) => {
          console.error("agent error", error);
          void refund(budget, ipHash);
          logQuery(env, {
            queryHash,
            text,
            source: "live",
            ok: false,
            matches: 0,
            elapsedMs: Date.now() - startedAt,
            model: env.MODEL,
          });
        },
      });

      return result.toUIMessageStreamResponse();
    } catch (error) {
      console.error("match failed", error);
      await refund(budget, ipHash);
      logQuery(env, {
        queryHash,
        text,
        source: "live",
        ok: false,
        matches: 0,
        elapsedMs: Date.now() - startedAt,
        model: env.MODEL,
      });
      return errorResponse(500, "agent_failed", "The matcher failed. Try again in a moment.");
    }
  },
} satisfies ExportedHandler<Env>;

function extractText(messages: UIMessage[] | undefined): string {
  if (!messages?.length) return "";
  const lastUser = [...messages].reverse().find((message) => message.role === "user");
  if (!lastUser) return "";
  return lastUser.parts
    .filter((part): part is Extract<typeof part, { type: "text" }> => part.type === "text")
    .map((part) => part.text)
    .join("\n");
}

function originAllowed(request: Request, env: Env): boolean {
  const origin = request.headers.get("Origin");
  if (!origin) return true;
  if (origin === env.APP_ORIGIN) return true;
  return /^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(origin);
}

function errorResponse(status: number, code: string, message: string): Response {
  return new Response(JSON.stringify({ error: message, code }), {
    status,
    statusText: message,
    headers: { "content-type": "application/json", "cache-control": "no-store" },
  });
}

async function reserve(
  stub: DurableObjectStub,
  payload: { ipHash: string; limitPerIp: number; globalLimit: number },
): Promise<BudgetDecision> {
  const response = await stub.fetch("https://budget/reserve", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return (await response.json()) as BudgetDecision;
}

async function refund(stub: DurableObjectStub, ipHash: string): Promise<void> {
  try {
    await stub.fetch("https://budget/refund", {
      method: "POST",
      body: JSON.stringify({ ipHash }),
    });
  } catch (error) {
    console.error("refund failed", error);
  }
}

function cachedResponse(result: MatchResult): Response {
  const stream = createUIMessageStream({
    execute({ writer }) {
      const toolCallId = crypto.randomUUID();
      writer.write({ type: "start" });
      writer.write({ type: "start-step" });
      writer.write({
        type: "tool-input-available",
        toolCallId,
        toolName: "submit_matches",
        input: { matches: result.matches },
      });
      writer.write({ type: "tool-output-available", toolCallId, output: result });
      writer.write({ type: "finish-step" });
      writer.write({ type: "finish" });
    },
  });
  return createUIMessageStreamResponse({ stream });
}
