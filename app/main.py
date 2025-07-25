from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import users, clubs, events, admin 
from app.db.database import create_db_and_tables
from app.api.routes import users, clubs, events

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Creating database and tables...")
    create_db_and_tables()
    yield
    print("Application shutdown.")

app = FastAPI(
    title="CampusConnect API",
    description="Backend for the Intelligent College Club & Event Platform",
    version="0.2.0",
    lifespan=lifespan
)

origins = [
    "http://localhost:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Updated tags for clarity
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(clubs.router, prefix="/clubs", tags=["Clubs & Announcements"])
app.include_router(events.router, prefix="/events", tags=["Events"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"]) # <-- Add this line
@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to the CampusConnect API! 🚀"}
