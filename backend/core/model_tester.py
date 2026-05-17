import os
import httpx
import asyncio
from dotenv import load_dotenv

load_dotenv(override=True)


async def list_available_models():
    api_key = os.getenv("GEMMA_API_KEY")
    if not api_key:
        print("Set GEMMA_API_KEY in .env")
        return

    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    print("Fetching models (filtering gemma-4)...")

    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=30.0)

    if response.status_code != 200:
        print(f"Error {response.status_code}: {response.text[:500]}")
        return

    models = response.json().get("models", [])
    gemma4 = [m for m in models if "gemma-4" in m.get("name", "").lower()]
    print(f"\nGemma 4 models ({len(gemma4)}):")
    for m in gemma4:
        name = m["name"].replace("models/", "")
        methods = m.get("supportedGenerationMethods", [])
        print(f"  - {name}  methods={methods}")


if __name__ == "__main__":
    asyncio.run(list_available_models())
