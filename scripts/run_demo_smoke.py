import requests
import time
import sys

BASE_URL = "http://localhost:8000"

def run():
    print(f"Connecting to {BASE_URL}...")
    
    # 1. Health check
    try:
        res = requests.get(f"{BASE_URL}/health")
        res.raise_for_status()
        print("[OK] Health check passed:", res.json())
    except Exception as e:
        print("[FAIL] Health check failed:", e)
        sys.exit(1)

    # 2. Reset DB
    try:
        res = requests.post(f"{BASE_URL}/api/v2/demo/reset")
        res.raise_for_status()
        print("[OK] Demo reset passed:", res.json())
    except Exception as e:
        print("[FAIL] Demo reset failed:", e)
        sys.exit(1)
        
    # 3. Seed DB
    try:
        res = requests.post(f"{BASE_URL}/api/v2/demo/seed")
        res.raise_for_status()
        print("[OK] Demo seed passed:", res.json())
    except Exception as e:
        print("[FAIL] Demo seed failed:", e)
        sys.exit(1)

    print("\n--- SMOKE TEST SUCCESSFUL ---")

if __name__ == "__main__":
    run()
