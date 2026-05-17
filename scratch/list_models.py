import os
import httpx
import asyncio
from dotenv import load_dotenv

load_dotenv(override=True)

async def list_models():
    api_key = os.getenv("GEMMA_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                models = resp.json().get('models', [])
                print("--- Available Models ---")
                for m in models:
                    name = m['name']
                    # Sadece isimleri bas, hata riskini minimize et
                    print(f"Model: {name}")
            else:
                print(f"Error: {resp.status_code}")
        except Exception as e:
            print(f"Exception: {str(e)}")

if __name__ == "__main__":
    asyncio.run(list_models())
