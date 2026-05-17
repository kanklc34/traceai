import httpx
import asyncio
import random
import uuid
from datetime import datetime, timezone

# Spike durumu takibi
SPIKE_ACTIVE = False

async def send_mock_trace():
    global SPIKE_ACTIVE
    trace_id = str(uuid.uuid4())[:8]
    service = random.choice(["api-gateway", "auth-service", "payment-service", "inventory-service"])
    
    if not SPIKE_ACTIVE and random.random() < 0.2:
        SPIKE_ACTIVE = True
        print(f"🌩️  [SPIKE STARTED] {service}")
    
    spans = []
    for _ in range(random.randint(1, 4)):
        if SPIKE_ACTIVE:
            status = random.choices(["ok", "error", "timeout"], weights=[0.2, 0.5, 0.3])[0]
            latency = random.uniform(1100, 3000)
        else:
            status = random.choices(["ok", "error", "timeout"], weights=[0.8, 0.12, 0.08])[0]
            latency = random.uniform(40, 600)
            
        spans.append({
            "span_id": str(uuid.uuid4())[:6],
            "operation": random.choice(["login", "checkout", "fetch_data"]),
            "status": status,
            "latency_ms": round(latency, 2)
        })

    if SPIKE_ACTIVE and random.random() < 0.4:
        SPIKE_ACTIVE = False
        print("☀️  [SPIKE ENDED]")

    payload = {
        "trace_id": trace_id, "service": service,
        "timestamp": datetime.now(timezone.utc).isoformat(), "spans": spans
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post("http://localhost:8000/api/v1/ingest", json=payload, timeout=5.0)
            print(f"{'🌩️' if SPIKE_ACTIVE else '✅'} {trace_id} | {service} | HTTP {resp.status_code}")
        except Exception as e:
            print(f"❌ Failed: {e}")

async def main():
    print("🚀 TraceAI Simulator Started")
    while True:
        await send_mock_trace()
        await asyncio.sleep(random.uniform(0.5, 1.5))

if __name__ == "__main__":
    asyncio.run(main())
