import type { UIMessage } from "ai";

import { runAgent } from "./agent";
import type { Env } from "./env";
import { verifyTurnstile } from "./turnstile";

type MatchBody = {
  messages?: UIMessage[];
  text?: string;
  turnstileToken?: string;
};

const MAX_INPUT = 6000;
const MIN_INPUT = 20;

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
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

    if (!(await verifyTurnstile(env, body.turnstileToken, ip))) {
      return errorResponse(403, "turnstile_failed", "Verification failed. Reload the page and try again.");
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
        onError: (error) => console.error("agent error", error),
      });

      return result.toUIMessageStreamResponse();
    } catch (error) {
      console.error("match failed", error);
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
