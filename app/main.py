from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

# Imports ko saaf kiya gaya hai
from app.db.database import create_db_and_tables
from app.api.routes import users, clubs, events, admin, photos, attendance # 'attendance' ko yahan import karein

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Creating database and tables...")
    create_db_and_tables()
    yield
    print("Application shutdown.")

app = FastAPI(
    title="CampusConnect API",
    description="Backend for the Intelligent College Club & Event Platform",
    version="0.4.0", # Version update for AI Attendance
    lifespan=lifespan
)

origins = [
    "http://localhost:5173",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sabhi routers ko yahan include karein
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(clubs.router, prefix="/clubs", tags=["Clubs & Announcements"])
app.include_router(events.router, prefix="/events", tags=["Events"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(photos.router, prefix="/photos", tags=["Photos"])
app.include_router(attendance.router, prefix="/attendance", tags=["Attendance"]) # <-- YEH NAYI LINE ADD KI GAYI HAI

@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to the CampusConnect API! 🚀"}