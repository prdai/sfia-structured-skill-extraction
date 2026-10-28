export interface Env {
  AI: Ai;
  VECTORIZE: VectorizeIndex;
  ASSETS: Fetcher;
  APP_ORIGIN: string;
  MODEL: string;
  AI_GATEWAY_ID: string;
  TURNSTILE_SECRET?: string;
}
