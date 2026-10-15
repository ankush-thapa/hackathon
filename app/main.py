from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.hello import router as hello_router
from app.api.users import router as users_router
from app.core.config import settings
from app.core.ids import new_id
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import User, UserProfile

SEED_USERS = ["World", "Alice", "Bob", "Charlie", "Diana"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Entrypoints run Alembic before startup; retain the existing demo seed users.
    with SessionLocal() as db:
        pw_hash = hash_password("Password1")
        for name in SEED_USERS:
            if db.query(User.id_user).filter_by(user_name=name.lower()).first() is None:
                uid = new_id()
                db.add(User(id_user=uid, user_name=name, password_hash=pw_hash))
                db.flush()  # user row must exist before the profile FK
                db.add(UserProfile(id_user=uid, full_name=name))
        db.commit()
    yield


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(hello_router)
app.include_router(users_router)


@app.get("/")
def root():
    return {"status": "ok"}
