from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.user_repo import DuplicateUserError, UserRepository
from app.schemas.auth import RegisterRequest, RegisterResponse, LoginRequest, LoginResponse
from app.services.auth_service import AccountBlockedError, AuthService, InvalidCredentialsError

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


@router.post(
    "/login",
    response_model=LoginResponse,
    responses={401: {"description": "Invalid credentials"}, 403: {"description": "Account blocked"}},
)
def login(req: LoginRequest, response: Response, service: AuthService = Depends(get_auth_service)):
    response.headers["Cache-Control"] = "no-store"
    try:
        id_user, token, expires_in = service.login(req)
    except InvalidCredentialsError:
        # One message for unknown account, wrong password, or deleted account.
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="invalid credentials", headers={"WWW-Authenticate": "Bearer"}
        )
    except AccountBlockedError:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="account blocked")
    return LoginResponse(accessToken=token, expiresIn=expires_in, userId=str(id_user))
