import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow requests from your Next.js frontend (local and production)
origins = [
    "http://localhost:3000",
    "https://your-frontend-project.vercel.app",  # Update after creating frontend project
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health_check():
    return {"status": "ok", "framework": "FastAPI"}

# SQLite Note: On Vercel's serverless platform, the filesystem is read-only except for /tmp.
# For persistent data, use PostgreSQL (e.g. Vercel Postgres, Supabase, Neon) in production.