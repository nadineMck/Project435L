from fastapi import FastAPI

from .database import Base, engine
from .routers import users, rooms, bookings, reviews
from .error_handlers import register_exception_handlers
# Create DB tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Smart Meeting Room Backend (Practice)",
    version="0.1.0",
    description="Practice project with users, rooms, bookings, and reviews.",
)

register_exception_handlers(app)

app.include_router(users.router)
app.include_router(rooms.router)
app.include_router(bookings.router)
app.include_router(reviews.router)

# Versioned API (v1)
app.include_router(users.router, prefix="/api/v1")
app.include_router(rooms.router, prefix="/api/v1")
app.include_router(bookings.router, prefix="/api/v1")
app.include_router(reviews.router, prefix="/api/v1")


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}
