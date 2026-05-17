import asyncio
import os
import httpx
from dotenv import load_dotenv

load_dotenv(override=True)


async def test(model: str):
    key = os.getenv("GEMMA_API_KEY") or os.getenv("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    async with httpx.AsyncClient() as c:
        r = await c.post(
            url,
            json={
                "contents": [{"parts": [{"text": 'Return JSON: {"ok": true}'}]}],
                "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
            },
            timeout=90.0,
        )
    print(f"{model}: {r.status_code}", r.text[:150] if r.status_code != 200 else "OK")


async def test_rca():
    key = os.getenv("GEMMA_API_KEY") or os.getenv("GEMINI_API_KEY")
    model = "gemma-4-26b-a4b-it"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    prompt = (
        "Return ONLY valid JSON with keys: root_cause, impact_level, explanation, "
        "recommended_action, confidence_score. Root cause: connection pool leak."
    )
    async with httpx.AsyncClient() as c:
        r = await c.post(
            url,
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
            },
            timeout=90.0,
        )
    print(f"RCA test: {r.status_code}")
    if r.status_code == 200:
        parts = r.json()["candidates"][0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts)
        print("LEN", len(text))
        print("TAIL", text[-400:])


async def test_full_synthesis():
    from backend.database import init_db, async_session
    from backend.core.gemma_agent import GemmaAgent
    from backend.core import agent_tools

    await init_db()
    agent = GemmaAgent()
    async with async_session() as session:
        eb = await agent_tools.get_error_breakdown(session, "payment-service")
        ev = {
            "error_breakdown": eb,
            "deployment": agent_tools.get_deployment("payment-service"),
            "similar_incidents": agent_tools.search_similar_incidents(
                "payment-service", "error_rate", eb
            ),
            "baseline_comparison": agent_tools.compare_to_baseline("payment-service", eb),
        }
        rca, model = await agent._synthesize_rca(ev, "payment-service", "error_rate")
        print(f"model={model}")
        print(f"root_cause={rca.get('root_cause')}")


async def main():
    await test_full_synthesis()


if __name__ == "__main__":
    asyncio.run(main())
