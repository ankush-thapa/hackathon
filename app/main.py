from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.auth import router as auth_router
from app.api.hello import router as hello_router
from app.api.media import MEDIA_URL_PATH
from app.api.media import router as media_router
from app.api.profile import router as profile_router
from app.api.rides import router as rides_router
from app.api.stations import router as stations_router
from app.api.users import router as users_router
from app.api.vehicles import router as vehicles_router
from app.core.config import settings
from app.db.fixtures import load_user_fixtures
from app.db.session import SessionLocal


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Entrypoints run Alembic before startup; retain the existing demo seed users.
    with SessionLocal() as db:
        load_user_fixtures(db)
    yield


# persistAuthorization keeps the token entered under Authorize across /docs reloads.
app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
    swagger_ui_parameters={"persistAuthorization": True},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(rides_router)
app.include_router(stations_router)
app.include_router(media_router)
app.include_router(vehicles_router)

settings.MEDIA_DIR.mkdir(parents=True, exist_ok=True)
app.mount(MEDIA_URL_PATH, StaticFiles(directory=settings.MEDIA_DIR), name="media")
app.include_router(hello_router)
app.include_router(users_router)


@app.get("/")
def root():
    return {"status": "ok"}
