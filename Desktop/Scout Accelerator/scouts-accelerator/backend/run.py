#!/usr/bin/env python3
"""
Startup script for Scout Accelerator Backend
This script starts the FastAPI server with proper configuration
"""

import uvicorn
from app import app
from secure_config import SERVER_CONFIG

if __name__ == "__main__":
    print("🚀 Starting Scout Accelerator Backend")
    print("=" * 50)
    print(f"Server will run on: http://{SERVER_CONFIG['host']}:{SERVER_CONFIG['port']}")
    print(f"Debug mode: {'ON' if SERVER_CONFIG['debug'] else 'OFF'}")
    print(f"API Documentation: http://localhost:{SERVER_CONFIG['port']}/docs")
    print("=" * 50)

    uvicorn.run(
        "app:app",
        host=SERVER_CONFIG["host"],
        port=SERVER_CONFIG["port"],
        reload=SERVER_CONFIG["debug"],
        log_level="info"
    )
