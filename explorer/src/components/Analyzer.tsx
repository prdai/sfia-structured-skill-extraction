import { useChat } from "@ai-sdk/react";
import { Turnstile, type TurnstileInstance } from "@marsidev/react-turnstile";
import {
  DefaultChatTransport,
  getToolName,
  isToolUIPart,
  type UIMessage,
} from "ai";
import { ArrowUpIcon, Check, Loader2, RotateCcw, SquareIcon } from "lucide-react";
import * as React from "react";

import { MatchCard } from "@/components/MatchCard";
import { Suggestions } from "@/components/Suggestions";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from "@/components/ui/empty";
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupText,
  InputGroupTextarea,
} from "@/components/ui/input-group";
import type { MatchResult } from "@/lib/types";

const ARXIV = "https://arxiv.org/abs/2609.35806";
const GITHUB = "https://github.com/prdai/sfia-structured-skill-extraction";
const MAX_CHARS = 6000;

export function Analyzer({ siteKey }: { siteKey?: string }) {
  const transport = React.useMemo(
    () => new DefaultChatTransport({ api: "/api/match" }),
    [],
  );
  const {
    messages,
    sendMessage,
    setMessages,
    status,
    stop,
    error,
  } = useChat({ transport });

  const [input, setInput] = React.useState("");
  const [submittedText, setSubmittedText] = React.useState("");
  const [turnstileError, setTurnstileError] = React.useState<string | null>(null);
  const pending = React.useRef<string | null>(null);
  const turnstile = React.useRef<TurnstileInstance>(undefined);

  const busy = status === "submitted" || status === "streaming";
  const result = React.useMemo(() => findResult(messages), [messages]);
  const started = messages.length > 0 || busy;

  function send(text: string, turnstileToken?: string) {
    setMessages([]);
    setSubmittedText(text);
    void sendMessage({ text }, { body: { text, turnstileToken } });
  }

  function submit(text: string) {
    const trimmed = text.trim();
    if (!trimmed || busy) return;
    setInput("");
    setTurnstileError(null);

    if (siteKey) {
      pending.current = trimmed;
      turnstile.current?.execute();
      return;
    }

    send(trimmed);
  }

  function onTurnstileSuccess(nextToken: string) {
    const text = pending.current;
    pending.current = null;
    if (text) send(text, nextToken);
    window.setTimeout(() => turnstile.current?.reset(), 1000);
  }

  function reset() {
    stop();
    setMessages([]);
    setSubmittedText("");
    setInput("");
    setTurnstileError(null);
    pending.current = null;
    turnstile.current?.reset();
  }

  return (
    <div className="mx-auto flex min-h-0 w-full max-w-3xl flex-1 flex-col px-5">
      {started ? (
        <div className="flex flex-1 flex-col gap-5 py-6">
          <div className="flex justify-end">
            <div className="line-clamp-3 max-w-[85%] rounded-2xl bg-muted px-4 py-2.5 text-sm leading-relaxed text-muted-foreground">
              {submittedText}
            </div>
          </div>

          {error && (
            <Alert variant="destructive">
              <AlertTitle>Request failed</AlertTitle>
              <AlertDescription>{error.message || "Something went wrong. Try again."}</AlertDescription>
            </Alert>
          )}

          {turnstileError && (
            <Alert variant="destructive">
              <AlertTitle>Verification failed</AlertTitle>
              <AlertDescription>{turnstileError}</AlertDescription>
            </Alert>
          )}

          {busy && !result && <Working messages={messages} />}

          {result && <Results result={result} onReset={reset} />}

          {!busy && !result && !error && (
            <Alert>
              <AlertTitle>No matches returned</AlertTitle>
              <AlertDescription>
                The agent finished without a match list. Try a longer description with
                concrete responsibilities.
              </AlertDescription>
            </Alert>
          )}
        </div>
      ) : (
        <div className="flex flex-1 items-center justify-center py-10">
          <Empty className="border-0 p-0">
            <EmptyHeader className="max-w-2xl">
              <span className="mb-2 inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs text-muted-foreground">
                Agentic RAG over SFIA 9
              </span>
              <EmptyTitle className="text-balance text-3xl font-medium tracking-tight sm:text-4xl">
                Map any role to SFIA skills and levels.
              </EmptyTitle>
              <EmptyDescription className="max-w-xl text-pretty text-sm leading-relaxed">
                Paste a job description, course outline, or role profile. The agent
                retrieves SFIA skill-level descriptions, then returns the skills and
                responsibility levels the text supports.
              </EmptyDescription>
            </EmptyHeader>
            <EmptyContent className="max-w-none">
              <Suggestions onSelect={submit} />
              <p className="text-xs text-muted-foreground">
                147 skills · 7 levels · 669 descriptions
              </p>
            </EmptyContent>
          </Empty>
        </div>
      )}

      <div className="sticky bottom-0 z-10 -mx-5 mt-auto bg-gradient-to-t from-background via-background to-background/0 px-5 pb-5 pt-6">
        <form
          onSubmit={(event) => {
            event.preventDefault();
            submit(input);
          }}
        >
          <InputGroup className="min-h-24 rounded-2xl border bg-background shadow-xs">
            <InputGroupTextarea
              placeholder="Paste a job description or role profile…"
              className="min-h-20 p-3.5 text-sm"
              value={input}
              maxLength={MAX_CHARS}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (
                  event.key === "Enter" &&
                  !event.shiftKey &&
                  !event.nativeEvent.isComposing
                ) {
                  event.preventDefault();
                  submit(input);
                }
              }}
            />
            <InputGroupAddon align="block-end">
              <InputGroupText className="px-1 text-xs">
                {input.length > MAX_CHARS - 500
                  ? `${input.length} / ${MAX_CHARS}`
                  : "Semantic + keyword retrieval"}
              </InputGroupText>
              {busy ? (
                <InputGroupButton
                  type="button"
                  size="icon-sm"
                  variant="outline"
                  aria-label="Stop"
                  className="ml-auto"
                  onClick={() => stop()}
                >
                  <SquareIcon />
                </InputGroupButton>
              ) : (
                <InputGroupButton
                  type="submit"
                  size="icon-sm"
                  variant="default"
                  aria-label="Analyze"
                  className="ml-auto"
                  disabled={!input.trim()}
                >
                  <ArrowUpIcon />
                </InputGroupButton>
              )}
            </InputGroupAddon>
          </InputGroup>
        </form>
        <p className="mt-2 text-center text-[11px] text-muted-foreground">
          Free demo, limited to 3 analyses per person per day. Queries are logged
          anonymously for research.{" "}
          <a className="underline underline-offset-4 hover:text-foreground" href="/method/">
            How it works
          </a>
        </p>
      </div>

      {siteKey && (
        <Turnstile
          ref={turnstile}
          siteKey={siteKey}
          options={{
            size: "invisible",
            execution: "execute",
            appearance: "execute",
            theme: "auto",
          }}
          onSuccess={onTurnstileSuccess}
          onError={() =>
            setTurnstileError("Cloudflare could not verify this browser. Reload and try again.")
          }
        />
      )}
    </div>
  );
}

function Working({ messages }: { messages: UIMessage[] }) {
  const searches = messages
    .flatMap((message) => message.parts)
    .filter(isToolUIPart)
    .filter((part) => {
      const name = getToolName(part);
      return name === "semantic_skill_search" || name === "keyword_skill_search";
    });

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-1 rounded-2xl border bg-card p-2">
        {searches.length === 0 ? (
          <StatusRow label="Planning retrieval…" running />
        ) : (
          searches.map((part) => {
            const name = getToolName(part);
            const semantic = name === "semantic_skill_search";
            return (
              <StatusRow
                key={part.toolCallId}
                label={`${semantic ? "Semantic" : "Keyword"} search`}
                detail={queryOf(part)}
                running={part.state !== "output-available"}
              />
            );
          })
        )}
        {searches.length > 0 && (
          <StatusRow label="Matching skills and responsibility levels…" running />
        )}
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {[0, 1, 2, 3].map((index) => (
          <div
            key={index}
            className="h-36 animate-pulse rounded-2xl border bg-muted/40"
            style={{ animationDelay: `${index * 120}ms` }}
          />
        ))}
      </div>
    </div>
  );
}

function StatusRow({
  label,
  detail,
  running = false,
}: {
  label: string;
  detail?: string;
  running?: boolean;
}) {
  return (
    <div className="flex items-center gap-2 rounded-xl px-2 py-1.5 text-xs text-muted-foreground">
      {running ? (
        <Loader2 className="size-3.5 shrink-0 animate-spin" />
      ) : (
        <Check className="size-3.5 shrink-0 text-foreground" />
      )}
      <span className="shrink-0 font-medium text-foreground/80">{label}</span>
      {detail && <span className="truncate">“{detail}”</span>}
    </div>
  );
}

function queryOf(part: UIMessage["parts"][number]): string | undefined {
  const input = (part as { input?: unknown }).input;
  if (!input || typeof input !== "object" || !("query" in input)) return undefined;
  const query = (input as { query?: unknown }).query;
  return typeof query === "string" ? query : undefined;
}

function Results({ result, onReset }: { result: MatchResult; onReset: () => void }) {
  const levels = result.matches.map((match) => match.level);
  const min = Math.min(...levels);
  const max = Math.max(...levels);

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-lg font-medium tracking-tight">
            {result.matches.length} {result.matches.length === 1 ? "skill" : "skills"} identified
          </h2>
          <p className="text-sm text-muted-foreground">
            Levels {min}–{max} · {(result.meta.elapsedMs / 1000).toFixed(1)}s
            {result.meta.cached ? " · cached" : ""}
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={onReset}>
          <RotateCcw />
          New analysis
        </Button>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        {result.matches.map((match) => (
          <MatchCard key={`${match.code}-${match.level}`} match={match} />
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t pt-4 text-xs text-muted-foreground">
        <a className="hover:text-foreground" href="/method/">
          How the matcher works
        </a>
        <a className="hover:text-foreground" href={ARXIV}>
          Read the paper
        </a>
        <a className="hover:text-foreground" href={GITHUB}>
          Star the repo
        </a>
      </div>
    </div>
  );
}

function findResult(messages: UIMessage[]): MatchResult | undefined {
  for (const message of [...messages].reverse()) {
    for (const part of message.parts) {
      if (
        isToolUIPart(part) &&
        getToolName(part) === "submit_matches" &&
        part.state === "output-available"
      ) {
        return part.output as MatchResult;
      }
    }
  }
  return undefined;
}
