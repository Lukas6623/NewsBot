from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from serverguard.config import get_settings
from serverguard.database.storage import Storage

settings = get_settings()
storage = Storage(settings.database_path)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await storage.init()
    yield

app = FastAPI(title="ServerGuard News API", docs_url=None, redoc_url=None, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.origins, allow_methods=["GET"], allow_headers=["Accept"])

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.get("/api/news")
async def news(response: Response, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
    response.headers["Cache-Control"] = "no-cache, max-age=0, must-revalidate"
    return {"posts": await storage.public_posts(limit, offset)}

@app.get("/media/{filename}")
async def media(filename: str):
    if filename != Path(filename).name or not filename.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
        raise HTTPException(404)
    path = settings.media_path / filename
    if not path.is_file():
        raise HTTPException(404)
    return FileResponse(path, headers={"Cache-Control": "public, max-age=3600"})
