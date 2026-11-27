from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse

from app.db import init_db
from app.routers import courses, progress, study

FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Study Buddy API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
for module in (courses, study, progress):
    app.include_router(module.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/{path:path}", include_in_schema=False)
def frontend(path: str):
    """Serve the built app (frontend/dist) if it exists; otherwise the API docs."""
    if path.startswith("api/"):
        raise HTTPException(404, "Not found")
    if not FRONTEND_DIST.exists():
        return RedirectResponse("/docs")
    file = (FRONTEND_DIST / path).resolve()
    if path and file.is_file() and FRONTEND_DIST in file.parents:
        return FileResponse(file)
    return FileResponse(FRONTEND_DIST / "index.html")
