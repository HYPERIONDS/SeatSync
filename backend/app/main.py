from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.audit.router import router as audit_router
from app.auth.router import router as auth_router
from app.bookings.router import router as bookings_router
from app.core.config import get_settings
from app.events.router import router as events_router
from app.reporting.router import router as reporting_router
from app.seat_holds.router import router as holds_router
from app.shows.router import router as shows_router
from app.users.admin_router import router as admin_router
from app.users.router import router as users_router
from app.venues.router import router as venues_router

settings = get_settings()
app = FastAPI(
    title="SeatSync API",
    version="1.0.0",
    description="Concurrent ticket booking. Payments are simulated; no real money is processed.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(venues_router, prefix="/api/v1")
app.include_router(events_router, prefix="/api/v1")
app.include_router(shows_router, prefix="/api/v1")
app.include_router(holds_router, prefix="/api/v1")
app.include_router(bookings_router, prefix="/api/v1")
app.include_router(reporting_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}
