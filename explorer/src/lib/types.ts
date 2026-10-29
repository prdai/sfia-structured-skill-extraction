export type CorpusRecord = {
  code: string;
  level: number;
  text: string;
  sourceUrl: string;
};

export type Skill = {
  code: string;
  name: string;
  levels: number[];
  excerpt: string;
  sourceUrl: string;
};

export type Match = {
  code: string;
  skill: string;
  level: number;
  excerpt: string;
  sourceUrl: string;
  score?: number;
};

export type MatchResult = {
  matches: Match[];
  meta: {
    model: string;
    elapsedMs: number;
  };
};

export type AnalyzerError = {
  error: string;
  code: "turnstile_failed" | "invalid_input" | "agent_failed";
};
