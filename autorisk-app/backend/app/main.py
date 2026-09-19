"""
FastAPI application entry point.

Run it with:  uvicorn app.main:app --reload --port 8000   (from backend/)
Then open:    http://localhost:8000/docs   for interactive API docs.
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .routers import auth, regions, coverages, policyholders, vehicles, policies, claims, dashboard, quote

load_dotenv()

app = FastAPI(title="AutoRisk API", version="0.1.0")

# CORS: by default, a browser blocks JavaScript on http://localhost:5173
# (the React dev server) from calling http://localhost:8000 (this API) --
# that's the browser's "same-origin policy". CORSMiddleware explicitly
# tells the browser "requests from this origin are allowed".
origins = [os.getenv("CORS_ORIGIN", "http://localhost:5173")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(regions.router)
app.include_router(coverages.router)
app.include_router(policyholders.router)
app.include_router(vehicles.router)
app.include_router(policies.router)
app.include_router(claims.router)
app.include_router(dashboard.router)
app.include_router(quote.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
