import os

import redis.asyncio as redis
from redis.exceptions import RedisError
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sse_starlette.sse import EventSourceResponse

REDIS_URL = os.environ.get("REDIS_URL", "redis://:root@localhost:6379")

app = FastAPI(title="Saga Dashboard")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "dashboard"}


@app.get("/stream")
async def stream():
    async def events():
        r = redis.from_url(REDIS_URL, decode_responses=True)
        ps = r.pubsub()
        await ps.psubscribe("saga:*")
        try:
            # Poll with a timeout instead of blocking on listen(): get_message returns
            # None when idle, so the stream survives idle gaps and pings without leaking
            # an exception. A torn-down connection surfaces here as a RedisError (redis-py
            # reports the cancelled read as a TimeoutError) — catch it and exit cleanly.
            while True:
                try:
                    m = await ps.get_message(ignore_subscribe_messages=True, timeout=1.0)
                except RedisError:
                    break
                if m and m["type"] == "pmessage":
                    yield {"data": m["data"]}
        finally:
            await ps.aclose()
            await r.aclose()

    return EventSourceResponse(events())


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    return _PAGE


_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>Saga Dashboard</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body { margin:0; font:14px/1.5 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; background:#0d1117; color:#c9d1d9; }
  header { padding:14px 20px; border-bottom:1px solid #21262d; display:flex; align-items:baseline; gap:14px; }
  header h1 { font-size:16px; margin:0; font-weight:600; }
  #status { font-size:12px; }
  #status.live { color:#3fb950; }
  #status.down { color:#f85149; }
  #feed { padding:12px 20px; max-width:920px; }
  .event { display:grid; grid-template-columns:96px 210px 1fr; gap:14px; padding:8px 12px;
           border-left:3px solid #30363d; margin-bottom:5px; background:#161b22; border-radius:5px; }
  .event .time { color:#6e7681; }
  .event .type { font-weight:600; }
  .event .oid  { color:#8b949e; }
  .ok   { border-left-color:#3fb950; } .ok .type   { color:#3fb950; }
  .bad  { border-left-color:#f85149; } .bad .type  { color:#f85149; }
  .comp { border-left-color:#d29922; } .comp .type { color:#d29922; }
  .empty { color:#6e7681; padding:24px 0; }
</style>
</head>
<body>
  <header>
    <h1>Saga Dashboard</h1>
    <span id="status" class="down">connecting&hellip;</span>
  </header>
  <div id="feed"><div class="empty">Waiting for events &mdash; place an order to watch the saga fire.</div></div>
<script>
  const feed = document.getElementById("feed");
  const status = document.getElementById("status");
  const OK   = new Set(["StockReserved", "PaymentCharged", "OrderConfirmed"]);
  const BAD  = new Set(["StockUnavailable", "PaymentFailed", "SagaRolledBack"]);
  const COMP = new Set(["ReleaseStock", "VoidPayment"]);
  const cls = (t) => OK.has(t) ? "ok" : BAD.has(t) ? "bad" : COMP.has(t) ? "comp" : "";

  const es = new EventSource("/stream");
  es.onopen  = () => { status.textContent = "live";         status.className = "live"; };
  es.onerror = () => { status.textContent = "disconnected"; status.className = "down"; };
  es.onmessage = (e) => {
    let ev;
    try { ev = JSON.parse(e.data); } catch { return; }
    feed.querySelector(".empty")?.remove();
    const row = document.createElement("div");
    row.className = "event " + cls(ev.type);
    const cells = [
      ["time", ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString() : ""],
      ["type", ev.type || "(unknown)"],
      ["oid",  ev.order_id || ""],
    ];
    for (const [klass, value] of cells) {
      const span = document.createElement("span");
      span.className = klass;
      span.textContent = value;       // textContent, not innerHTML — no injection from event data
      row.appendChild(span);
    }
    feed.prepend(row);
  };
</script>
</body>
</html>"""
