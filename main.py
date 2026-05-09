"""
ProxyMaze — Continuous Proxy Pool Monitoring Service
Entry point: starts the FastAPI server on port 8080.
"""

import uvicorn
from app.server import create_app

app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        log_level="info",
        reload=False,
    )
