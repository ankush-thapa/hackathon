from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.hello import router as hello_router
from app.api.users import router as users_router
from app.core.config import settings


app = FastAPI(title=settings.PROJECT_NAME)

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
