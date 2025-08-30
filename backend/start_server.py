#!/usr/bin/env python3
"""
Startup script for the OpenProbe Backend API.

This script provides an easy way to start the FastAPI server with proper configuration.
"""

import os
import sys
import uvicorn
from pathlib import Path

# Add the project root to Python path for importing deepsearch modules
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Import configuration
try:
    from app.config import settings
    from app.utils.logging import setup_logging, get_logger
except ImportError as e:
    print(f"Error importing configuration: {e}")
    print("Make sure you're running from the backend directory")
    sys.exit(1)

def main():
    """Main entry point for the server."""
    
    # Setup logging
    setup_logging()
    logger = get_logger("deepsearch.startup")
    
    # Print startup information
    print("=" * 60)
    print(f"🚀 Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    print("=" * 60)
    print(f"📍 Server URL: http://{settings.HOST}:{settings.PORT}")
    print(f"📖 API Docs: http://{settings.HOST}:{settings.PORT}/docs")
    print(f"🔌 WebSocket: ws://{settings.HOST}:{settings.PORT}/ws")
    print(f"💡 Frontend: http://localhost:3000 (if running)")
    print("=" * 60)
    
    # Check for required environment variables
    env_warnings = []
    
    if not os.getenv("WEB_SEARCH_API_KEY"):
        env_warnings.append("WEB_SEARCH_API_KEY not set - web search may not work")
    
    if not os.getenv("GOOGLE_API_KEY") and not os.getenv("LAMBDA_API_KEY"):
        env_warnings.append("Neither GOOGLE_API_KEY nor LAMBDA_API_KEY set - AI models may not work")
    
    if env_warnings:
        print("⚠️  Environment Warnings:")
        for warning in env_warnings:
            print(f"   • {warning}")
        print("   The system will run in mock mode for missing services.")
        print("=" * 60)
    
    # Start the server
    try:
        uvicorn.run(
            "app.main:app",
            host=settings.HOST,
            port=settings.PORT,
            reload=settings.RELOAD,
            log_level=settings.LOG_LEVEL.lower(),
            access_log=True,
            loop="asyncio"
        )
    except KeyboardInterrupt:
        logger.info("Server shutdown by user")
        print("\n👋 Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        print(f"\n❌ Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
