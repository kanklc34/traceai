import httpx
import asyncio
import uuid
import random
from datetime import datetime, timezone

async def send_trace(service, status, latency):
    trace_id = f"demo-{uuid.uuid4().hex[:6]}"
    payload = {
        "trace_id": trace_id,
        "service": service,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "spans": [{
            "span_id": f"sp-{uuid.uuid4().hex[:4]}",
            "operation": "checkout_flow",
            "status": status,
            "latency_ms": latency,
            "metadata": {"env": "production", "version": "v2.4.1-hotfix"}
        }]
    }
    async with httpx.AsyncClient() as client:
        try:
            await client.post("http://localhost:8000/api/v1/ingest", json=payload)
            print(f"[INGEST] {status.upper()} | {service} | {latency}ms")
        except Exception as e:
            print(f"[ERROR] {e}")

async def run_scenario():
    print("[SYSTEM] Starting incident simulation scenario...")
    svc = "payment-service"
    
    # Phase 1: Latency degradation
    print("\n[PHASE 1] Simulating latency degradation...")
    for _ in range(3):
        await send_trace(svc, "ok", random.uniform(850, 1200))
        await asyncio.sleep(0.5)

    # Phase 2: Flapping service
    print("\n[PHASE 2] Simulating service instability...")
    for _ in range(4):
        status = random.choice(["ok", "error"])
        await send_trace(svc, status, random.uniform(1500, 2500))
        await asyncio.sleep(0.4)

    # Phase 3: Critical failure
    print("\n[PHASE 3] Simulating critical failure...")
    for _ in range(5):
        await send_trace(svc, "error", 3000.0)
        await asyncio.sleep(0.2)

    print("\n[SUCCESS] Scenario injection complete.")
    print("[INFO] Analysis report should be available in the dashboard.")

if __name__ == "__main__":
    asyncio.run(run_scenario())
