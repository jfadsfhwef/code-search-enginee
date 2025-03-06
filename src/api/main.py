# src/api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import router
from src.utils.logger import get_logger
import sys

logger = get_logger()

def check_dependencies():
    """Check if all required dependencies are available"""
    required_deps = ['uvicorn', 'numpy', 'pandas', 'faiss']
    missing_deps = []
    
    for dep in required_deps:
        try:
            __import__(dep)
            logger.info(f"[OK] {dep} is available")
        except ImportError as e:
            missing_deps.append(dep)
            logger.error(f"[ERROR] Failed to import {dep}: {str(e)}")
    
    if missing_deps:
        logger.error(f"Missing dependencies: {', '.join(missing_deps)}")
        logger.error("Please install missing dependencies with: pip install " + " ".join(missing_deps))
        return False
    
    logger.info("All required dependencies are available")
    return True

def create_app() -> FastAPI:
    # Check dependencies first
    if not check_dependencies():
        logger.error("Cannot start server due to missing dependencies")
        sys.exit(1)

    app = FastAPI(title="HS Code Search API")

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routes
    app.include_router(router)

    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting API server")
    uvicorn.run(app, host="0.0.0.0", port=8000, workers=1)