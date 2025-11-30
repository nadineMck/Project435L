from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded

from .database import Base, engine
from .routers import users, rooms, bookings, reviews
from .error_handlers import register_exception_handlers

# -----------------------------------------
# Create DB tables
# -----------------------------------------
Base.metadata.create_all(bind=engine)

# -----------------------------------------
# Rate Limiter (Part II - Task 1)
# 5 requests per minute per client IP by default
# -----------------------------------------
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["5/minute"],
)

app = FastAPI(
    title="Smart Meeting Room Backend (Practice)",
    version="0.1.0",
    description="Practice project with users, rooms, bookings, and reviews.",
)

# Attach limiter to app and add middleware
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# -----------------------------------------
# Global exception handlers (your previous setup)
# -----------------------------------------
register_exception_handlers(app)


# Custom handler for rate limit errors (HTTP 429)
@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Rate limit exceeded. Please try again later.",
            "error": "too_many_requests",
            "path": str(request.url.path),
        },
    )


# -----------------------------------------
# Routers (normal + versioned /api/v1)
# -----------------------------------------
app.include_router(users.router)
app.include_router(rooms.router)
app.include_router(bookings.router)
app.include_router(reviews.router)

# Versioned API (v1)
app.include_router(users.router, prefix="/api/v1")
app.include_router(rooms.router, prefix="/api/v1")
app.include_router(bookings.router, prefix="/api/v1")
app.include_router(reviews.router, prefix="/api/v1")


# -----------------------------------------
# Health check endpoint
# -----------------------------------------
@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}
