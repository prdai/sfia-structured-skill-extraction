import type { Env } from "./env";

type ReserveBody = {
  ipHash: string;
  limitPerIp: number;
  globalLimit: number;
};

type RefundBody = {
  ipHash: string;
};

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

function thisMonth(): string {
  return new Date().toISOString().slice(0, 7);
}

export class Budget implements DurableObject {
  constructor(
    private state: DurableObjectState,
    private env: Env,
  ) {}

  async fetch(request: Request): Promise<Response> {
    const { pathname } = new URL(request.url);
    if (pathname === "/reserve") return this.reserve(await request.json<ReserveBody>());
    if (pathname === "/refund") return this.refund(await request.json<RefundBody>());
    return new Response("Not found", { status: 404 });
  }

  private async reserve({ ipHash, limitPerIp, globalLimit }: ReserveBody): Promise<Response> {
    const monthKey = `month:${thisMonth()}`;
    const dayKey = `day:${ipHash}:${today()}`;
    const [monthCount, dayCount] = await Promise.all([
      this.state.storage.get<number>(monthKey),
      this.state.storage.get<number>(dayKey),
    ]);

    if ((monthCount ?? 0) >= globalLimit) {
      return Response.json({
        ok: false,
        reason: "budget_exhausted",
        remaining: { month: 0, day: Math.max(0, limitPerIp - (dayCount ?? 0)) },
      });
    }

    if ((dayCount ?? 0) >= limitPerIp) {
      return Response.json({
        ok: false,
        reason: "ip_limited",
        remaining: { month: Math.max(0, globalLimit - (monthCount ?? 0)), day: 0 },
      });
    }

    await Promise.all([
      this.state.storage.put(monthKey, (monthCount ?? 0) + 1),
      this.state.storage.put(dayKey, (dayCount ?? 0) + 1),
    ]);

    if (Math.random() < 0.02) await this.prune();

    return Response.json({
      ok: true,
      remaining: {
        month: Math.max(0, globalLimit - (monthCount ?? 0) - 1),
        day: Math.max(0, limitPerIp - (dayCount ?? 0) - 1),
      },
    });
  }

  private async refund({ ipHash }: RefundBody): Promise<Response> {
    const monthKey = `month:${thisMonth()}`;
    const dayKey = `day:${ipHash}:${today()}`;
    const [monthCount, dayCount] = await Promise.all([
      this.state.storage.get<number>(monthKey),
      this.state.storage.get<number>(dayKey),
    ]);

    await Promise.all([
      monthCount ? this.state.storage.put(monthKey, Math.max(0, monthCount - 1)) : undefined,
      dayCount ? this.state.storage.put(dayKey, Math.max(0, dayCount - 1)) : undefined,
    ]);

    return Response.json({ ok: true });
  }

  private async prune(): Promise<void> {
    const monthKey = `month:${thisMonth()}`;
    const dayPrefix = "day:";
    const todaySuffix = `:${today()}`;
    const [months, days] = await Promise.all([
      this.state.storage.list<number>({ prefix: "month:" }),
      this.state.storage.list<number>({ prefix: dayPrefix }),
    ]);

    const deletions: string[] = [];
    for (const key of months.keys()) if (key !== monthKey) deletions.push(key);
    for (const key of days.keys()) if (!key.endsWith(todaySuffix)) deletions.push(key);
    if (deletions.length) await this.state.storage.delete(deletions);
  }
}
