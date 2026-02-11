from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.api.endpoints import router as ia_router
from app.services.llamaOrchestor import LlamaOrchestor
from app.store.session_store import SessionStore

# Initialize settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "http://localhost:5173","http://127.0.0.1:5173"],  # TODO: Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include IA router (all endpoints under /api)
app.include_router(ia_router)
@app.on_event("startup")
async def startup_event():
    print(f"Starting {settings.app_name} v{settings.app_version}")

    app.state.store = SessionStore(ttl_seconds=60*30)
    app.state.orch = LlamaOrchestor(settings)


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event."""
    print(f"Shutting down {settings.app_name}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
