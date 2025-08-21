#!/usr/bin/env python3

import uvicorn
import app

if __name__ == "__main__":
    print("Starting Scout Accelerator API server...")
    print(f"Server will run on http://localhost:8001")
    print("Press Ctrl+C to stop the server")

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
