from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from config import ALLOWED_ORIGINS
from database import init_db_indices
from contextlib import asynccontextmanager

from routers import metadata, leaderboard, players, dashboard, predictions

# Rate Limiter Setup
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure indices exist on startup
    init_db_indices()
    yield

app = FastAPI(lifespan=lifespan)

# Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS + ["http://127.0.0.1:3000"],
    allow_origin_regex="https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup SlowAPI Limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/")
def read_root():
    return {"status": "API is running", "version": "1.0.0"}

# Include Routers
app.include_router(metadata.router)
app.include_router(leaderboard.router)
app.include_router(players.router)
app.include_router(dashboard.router)
app.include_router(predictions.router)

# Mount static files (must be at the end or carefully ordered)
# We serve the frontend directory
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "../frontend")), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
