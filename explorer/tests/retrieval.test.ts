import { expect, test } from "bun:test";

import { KEYWORD_THRESHOLD, TOOL_RESULT_LIMIT } from "../src/lib/retrieval-config";
import type { Env } from "../worker/env";
import { searchSkills } from "../worker/retrieval";

const env = {} as Env;

test.each(["", "   ", "the and of", "...", "qzxvnonexistent"])(
  "keyword search returns no matches for %j",
  async (query) => {
    expect(await searchSkills(env, query, "keyword")).toEqual([]);
  },
);

test("keyword search ignores case and English stopwords", async () => {
  const expected = await searchSkills(env, "network security", "keyword");
  expect(expected.length).toBeGreaterThan(0);
  expect(await searchSkills(env, "NETWORK SECURITY", "keyword")).toEqual(expected);
  expect(await searchSkills(env, "the network and security", "keyword")).toEqual(expected);
});

test("keyword search supports Orama prefix matching", async () => {
  const hits = await searchSkills(env, "secur", "keyword");
  expect(hits.length).toBeGreaterThan(0);
  expect(hits.every((hit) => hit.text.toLowerCase().includes("secur"))).toBe(true);
});

test("keyword search accepts partial term matches and applies the score cutoff", async () => {
  const hits = await searchSkills(env, "ethical impact assessments qzxvnonexistent", "keyword");
  expect(hits.some((hit) => hit.code === "AIDE")).toBe(true);
  expect(hits.length).toBeLessThanOrEqual(TOOL_RESULT_LIMIT);
  expect(hits[0].score).toBe(1);
  for (let index = 0; index < hits.length; index += 1) {
    expect(hits[index].score).toBeGreaterThanOrEqual(KEYWORD_THRESHOLD);
    expect(hits[index].score).toBeLessThanOrEqual(index ? hits[index - 1].score : 1);
    expect(hits[index].text.length).toBeGreaterThan(0);
  }
});
