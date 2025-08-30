import asyncio
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

# Import configuration and utilities
from .config import settings
from .utils.logging import setup_logging, get_logger
from .utils.exceptions import DeepSearchException

# Import services
from .services.session_manager import session_manager
from .services.websocket_service import websocket_manager
from .services.search_service import create_search_service

# Import routes
from .routes import health, search, websocket

# Setup logging
setup_logging()
logger = get_logger("deepsearch.main")

# Create global service instances
search_service = create_search_service(session_manager, websocket_manager)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    
    try:
        # Start background tasks
        await session_manager.start_cleanup_task()
        await websocket_manager.start_heartbeat()
        
        logger.info("Background tasks started successfully")
        logger.info(f"Server will be available at http://{settings.HOST}:{settings.PORT}")
        logger.info(f"WebSocket endpoint: ws://{settings.HOST}:{settings.PORT}/ws")
        
        yield
        
    finally:
        # Shutdown
        logger.info("Shutting down application...")
        
        try:
            # Stop background tasks
            await session_manager.stop_cleanup_task()
            await websocket_manager.stop_heartbeat()
            
            logger.info("Background tasks stopped successfully")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Exception handlers
@app.exception_handler(DeepSearchException)
async def deepsearch_exception_handler(request: Request, exc: DeepSearchException):
    """Handle custom DeepSearch exceptions."""
    logger.error(f"DeepSearch exception: {exc.message} (Code: {exc.error_code})")
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": exc.message,
            "error_code": exc.error_code,
            "timestamp": exc.timestamp.isoformat(),
            "details": exc.details
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    logger.warning(f"Validation error: {exc.errors()}")
    
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Request validation failed",
            "error_code": "VALIDATION_ERROR",
            "timestamp": datetime.utcnow().isoformat(),
            "errors": exc.errors()
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error_code": "HTTP_ERROR",
            "timestamp": datetime.utcnow().isoformat(),
            "status_code": exc.status_code
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error_code": "INTERNAL_ERROR",
            "timestamp": datetime.utcnow().isoformat(),
        }
    )

# Include routers
app.include_router(health.router)
app.include_router(search.router)
app.include_router(websocket.router)

# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint with basic API information.
    """
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/health",
        "websocket": "/ws",
        "timestamp": datetime.utcnow().isoformat()
    }

# Additional middleware for logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests."""
    start_time = datetime.utcnow()
    
    # Process the request
    response = await call_next(request)
    
    # Log the request
    process_time = (datetime.utcnow() - start_time).total_seconds()
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.3f}s"
    )
    
    return response

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level=settings.LOG_LEVEL.lower()
    )
