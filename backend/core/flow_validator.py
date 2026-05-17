import httpx
import asyncio
import sqlite3
import os
import sys

# Proje ana dizinini ekle
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

async def validate_system_flow():
    print("🚀 [VALIDATOR] Starting End-to-End Flow Test...")
    
    # 1. Ingest API'ye Hata Gönder (Anomali Tetikle)
    print("📡 [STEP 1] Sending 10 error traces to trigger anomaly...")
    async with httpx.AsyncClient() as client:
        for i in range(10):
            payload = {
                "trace_id": f"test-flow-{i}",
                "service": "auth-service",
                "operation": "validate_token",
                "duration_ms": 500,
                "status": "error",
                "metadata": {"error": "DB_TIMEOUT"}
            }
            await client.post("http://localhost:8000/api/v1/ingest", json=payload)
    
    print("✅ [STEP 1] Errors sent. Waiting for Anomaly Detector (10s)...")
    await asyncio.sleep(12)
    
    # 2. Kuyruğu ve AI Worker'ı Bekle
    print("🧠 [STEP 2] Waiting for AI Engine to process queue (15s)...")
    await asyncio.sleep(15)
    
    # 3. Veritabanını Kontrol Et
    print("💾 [STEP 3] Checking database for AI Report...")
    conn = sqlite3.connect("traceai_demo.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ai_reports ORDER BY created_at DESC LIMIT 1")
    report = cursor.fetchone()
    conn.close()
    
    if report:
        print("\n" + "="*50)
        print("🎉 SUCCESS! SYSTEM IS REAL AND WORKING!")
        print(f"Kök Neden: {report[2]}")
        print(f"Açıklama: {report[4]}")
        print("="*50)
    else:
        print("\n❌ FAILED! No report found. Check Backend logs.")

if __name__ == "__main__":
    asyncio.run(validate_system_flow())
