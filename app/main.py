from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.hello import router as hello_router
from app.api.users import router as users_router
from app.core.config import settings
from app.db.session import Base, SessionLocal, engine
from app.models import User

SEED_USERS = [(1, "World"), (2, "Alice"), (3, "Bob"), (4, "Charlie"), (5, "Diana")]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dev convenience: create tables and seed demo users. Use migrations for real apps.
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        for user_id, name in SEED_USERS:
            if db.get(User, user_id) is None:
                db.add(User(id=user_id, name=name))
        db.commit()
    yield


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(hello_router)
app.include_router(users_router)


@app.get("/")
def root():
    return {"status": "ok"}
