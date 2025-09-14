#!/usr/bin/env python3
"""
Ultra-simple diagnostic backend to test basic startup.
"""

print("=== Ultra Simple Backend Starting ===")

try:
    from fastapi import FastAPI
    print("✓ FastAPI import successful")
except Exception as e:
    print(f"✗ FastAPI import failed: {e}")
    exit(1)

try:
    import uvicorn
    print("✓ Uvicorn import successful")
except Exception as e:
    print(f"✗ Uvicorn import failed: {e}")
    exit(1)

app = FastAPI(title="Ultra Simple Backend")

@app.get("/")
async def root():
    return {"status": "ok", "message": "Ultra simple backend is working"}

@app.get("/ping")
async def ping():
    return {"status": "ok", "message": "Backend responding"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/debug")
async def debug():
    import sys
    import os
    return {
        "python_version": sys.version,
        "cwd": os.getcwd(),
        "env_count": len(os.environ),
        "message": "Ultra simple backend debug info"
    }

if __name__ == "__main__":
    print("Starting ultra simple backend...")
    try:
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except Exception as e:
        print(f"Failed to start: {e}")
        exit(1)