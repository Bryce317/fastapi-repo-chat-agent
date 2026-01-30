"""Main FastAPI application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.logging_config import get_logger, setup_logging
from config.settings import get_settings
from database import close_neo4j_client, get_neo4j_client, initialize_schema

from .routes import chat, health, index, websocket

# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events.
    
    Args:
        app: FastAPI application instance.
    """
    # Startup
    logger.info("Starting FastAPI Repository Chat Agent...")
    
    settings = get_settings()
    
    try:
        # Initialize Neo4j connection
        neo4j_client = await get_neo4j_client()
        await neo4j_client.verify_connectivity()
        logger.info("Neo4j connection established")
        
        # Initialize schema
        await initialize_schema(neo4j_client)
        logger.info("Neo4j schema initialized")
        
        # Optionally index on startup
        if settings.index_on_startup:
            logger.info("Indexing repository on startup...")
            from agents.indexer.tools import get_indexer_tools
            
            indexer = get_indexer_tools()
            await indexer.index_repository()
            logger.info("Repository indexing completed")
        
        logger.info("Application startup complete")
        
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    
    try:
        await close_neo4j_client()
        logger.info("Neo4j connection closed")
    except Exception as e:
        logger.error(f"Shutdown error: {e}")
    
    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="FastAPI Repository Chat Agent",
    description="Multi-agent system for answering questions about the FastAPI codebase",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router)
app.include_router(index.router)
app.include_router(health.router)
app.include_router(websocket.router)


@app.get("/")
async def root():
    """Root endpoint with API information.
    
    Returns:
        Dictionary with API information.
    """
    return {
        "name": "FastAPI Repository Chat Agent",
        "version": "1.0.0",
        "description": "Multi-agent system for answering questions about FastAPI codebase",
        "endpoints": {
            "chat": "/api/chat",
            "index": "/api/index",
            "index_status": "/api/index/status",
            "health": "/api/agents/health",
            "statistics": "/api/graph/statistics",
            "websocket": "/ws/chat",
        },
    }


@app.get("/health")
async def health_check():
    """Simple health check endpoint.
    
    Returns:
        Health status.
    """
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    
    uvicorn.run(
        "gateway.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
    )
