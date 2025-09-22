from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from app.db.database import create_db_and_tables
from app.api.routes import users, clubs, events, admin, photos, attendance, verification, analytics, forums, role_requests

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Creating database and tables...")
    create_db_and_tables()
    yield
    print("Application shutdown.")

app = FastAPI(
    title="SAMVAD API",
    description="Backend for the SAMVAD Campus Community Platform",
    version="0.5.0", # Version update for WhatsApp Feature
    lifespan=lifespan
)

origins = ["*"]  # Allow all origins temporarily

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,  # Must be False when using "*"
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Sabhi routers ko yahan include karein
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(clubs.router, prefix="/clubs", tags=["Clubs & Announcements"])
app.include_router(events.router, prefix="/events", tags=["Events"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(photos.router, prefix="/photos", tags=["Photos"])
app.include_router(attendance.router, prefix="/attendance", tags=["Attendance"])
app.include_router(verification.router, prefix="/verification", tags=["Verification"])
app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
app.include_router(forums.router, prefix="/forums", tags=["Forums"])
app.include_router(role_requests.router, prefix="/role-requests", tags=["Role Requests"])

@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to the SAMVAD API! 🚀"}

