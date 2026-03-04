from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os

from app.api import auth as auth_router
from app.api import contacts as contacts_router
from app.api import messages as messages_router
from app.api import files as files_router
from app.api import ws as ws_router
from app.db import Base, engine
from app.models import *  # noqa: F401,F403


app = FastAPI(title="Chat App Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup() -> None:
    # For now, auto-create tables in dev. Later we can introduce Alembic migrations.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


app.include_router(auth_router.router)
app.include_router(contacts_router.router)
app.include_router(messages_router.router)
app.include_router(files_router.router)
app.include_router(ws_router.router)

static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index() -> str:
    index_path = os.path.join(static_dir, "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        return f.read()

