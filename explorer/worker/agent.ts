import {
  convertToModelMessages,
  hasToolCall,
  stepCountIs,
  streamText,
  tool,
  type UIMessage,
} from "ai";
import { createWorkersAI } from "workers-ai-provider";
import { z } from "zod";

import type { MatchResult } from "../src/lib/types";
import type { Env } from "./env";
import { searchSkills } from "./retrieval";
import { normalizeMatches } from "./skills";

const SYSTEM = `You map free text to SFIA 9 skills and responsibility levels.

The input may be a job advert, role profile, course outline, or resume excerpt.

Rules:
- Use both tools. Call semantic_skill_search for meaning-based matches and keyword_skill_search for jargon, acronyms, and exact terms.
- Query with the distinct responsibilities in the text. Call each search tool at most twice, then stop searching.
- Only include a skill-level pair when the retrieved description clearly supports it. Prefer specific skills over broad ones.
- Copy the code, skill name, and level exactly from tool results. Never invent a code or a level.
- Aim for the skills the text actually calls for. Five to fifteen pairs is typical; fewer is better than padding.
- Finish by calling submit_matches with the final list. Do not write a prose answer.`;

export type AgentHooks = {
  onFinal?: (result: MatchResult) => Promise<void> | void;
  onError?: (error: unknown) => void;
};

export async function runAgent(
  env: Env,
  messages: UIMessage[],
  startedAt: number,
  hooks: AgentHooks = {},
) {
  const workersai = createWorkersAI({ binding: env.AI });
  const model = workersai(env.MODEL, {
    chat_template_kwargs: { enable_thinking: false },
  });

  let final: MatchResult | undefined;
  let searches = 0;
  const SEARCH_LIMIT = 6;

  async function search(query: string, type: "vector" | "keyword") {
    searches += 1;
    if (searches > SEARCH_LIMIT) {
      return {
        results: [],
        note: "Search budget exhausted. Call submit_matches now with the best results so far.",
      };
    }
    return { results: await searchSkills(env, query, type) };
  }

  return streamText({
    model,
    system: SYSTEM,
    messages: await convertToModelMessages(messages),
    temperature: 0,
    maxOutputTokens: 1600,
    stopWhen: [stepCountIs(14), hasToolCall("submit_matches")],
    tools: {
      semantic_skill_search: tool({
        description:
          "Semantic search over SFIA skill-level descriptions. Finds skills whose descriptions are similar in meaning to the query, even without shared words. Returns JSON records with code, skill, level, text and source_url.",
        inputSchema: z.object({
          query: z
            .string()
            .min(3)
            .max(500)
            .describe("A responsibility, task, or capability from the input text."),
        }),
        execute: async ({ query }) => search(query, "vector"),
      }),
      keyword_skill_search: tool({
        description:
          "Keyword (BM25) search over SFIA skill-level descriptions. Finds skills whose descriptions share exact terms with the query; best for jargon, acronyms, product names and named technologies. Returns JSON records with code, skill, level, text and source_url.",
        inputSchema: z.object({
          query: z
            .string()
            .min(2)
            .max(500)
            .describe("Exact terms, tool names, or jargon from the input text."),
        }),
        execute: async ({ query }) => search(query, "keyword"),
      }),
      submit_matches: tool({
        description:
          "Submit the final SFIA matches. Call this exactly once, after searching. Every entry must come from a prior tool result.",
        inputSchema: z.object({
          matches: z
            .array(
              z.object({
                code: z.string().describe("SFIA skill code copied from a tool result, e.g. PROG."),
                skill: z.string().describe("SFIA skill name copied from a tool result."),
                level: z.number().int().min(1).max(7).describe("Responsibility level 1-7."),
              }),
            )
            .min(1)
            .max(20),
        }),
        execute: async ({ matches }) => {
          const normalized = normalizeMatches(matches);
          if (!normalized.length) {
            throw new Error(
              "No valid SFIA matches. Use codes, names and levels returned by the search tools.",
            );
          }
          final = {
            matches: normalized,
            meta: {
              model: env.MODEL,
              elapsedMs: Date.now() - startedAt,
              cached: false,
            },
          };
          return final;
        },
      }),
    },
    onEnd: async () => {
      if (final) await hooks.onFinal?.(final);
    },
    onError: (error) => {
      hooks.onError?.(error);
    },
  });
}
