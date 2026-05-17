import os
import sys
import sqlite3
import time

# Ensure terminal output supports UTF-8 to prevent UnicodeEncodeErrors on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Database path for demo validation
DB_PATH = os.path.join("data", "traceai_demo.db")

def validate_pipeline():
    print("🔍 TraceAI Pipeline Validator starting...")
    
    if not os.path.exists(DB_PATH):
        print(f"❌ ERROR: Database not found at {DB_PATH}. Run the backend first.")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Check Traces
        cursor.execute("SELECT COUNT(*) FROM traces")
        trace_count = cursor.fetchone()[0]
        print(f"✅ Telemetry Ingestion: {trace_count} traces found.")

        # Check Reports
        cursor.execute("SELECT COUNT(*) FROM ai_reports")
        report_count = cursor.fetchone()[0]
        print(f"✅ AI Analysis Engine: {report_count} reports generated.")

        if report_count > 0:
            print("🏆 PLATFORM STATUS: OPERATIONAL & INTELLIGENT")
        else:
            print("⚠️ PLATFORM STATUS: MONITORING (Waiting for anomalies)")

        conn.close()
    except Exception as e:
        print(f"❌ ERROR during validation: {str(e)}")

if __name__ == "__main__":
    validate_pipeline()
