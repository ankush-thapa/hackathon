from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.user_repo import DuplicateUserError, UserRepository
from app.schemas.auth import RegisterRequest, RegisterResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/v1/auth", tags=["auth"])


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(UserRepository(db))


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, service: AuthService = Depends(get_auth_service)):
    try:
        user = service.register(req)
    except DuplicateUserError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"{e.field} already registered")
    return RegisterResponse(
        userId=str(user.id_user),  # string: snowflake IDs exceed JS safe-integer range
        email=user.email,
        phone=user.phone_number,
    )
