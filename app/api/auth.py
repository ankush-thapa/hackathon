from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.deps import get_auth_service, get_current_session
from app.repositories.user_repo import DuplicateUserError
from app.schemas.auth import LoginRequest, LoginResponse, RegisterRequest, RegisterResponse, SessionInfo
from app.services.auth_service import AccountBlockedError, AuthService, CurrentSession, InvalidCredentialsError

router = APIRouter(prefix="/v1/auth", tags=["auth"])

_UNAUTHORIZED = {401: {"description": "Missing, invalid, expired, or revoked session"}}


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
def login(req: LoginRequest, request: Request, response: Response, service: AuthService = Depends(get_auth_service)):
    response.headers["Cache-Control"] = "no-store"
    try:
        result = service.login(
            req,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
    except InvalidCredentialsError:
        # One message for unknown account, wrong password, or deleted account.
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="invalid credentials", headers={"WWW-Authenticate": "Bearer"}
        )
    except AccountBlockedError:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="account blocked")
    return LoginResponse(
        accessToken=result.access_token,
        expiresIn=result.expires_in,
        userId=str(result.id_user),
        sessionId=str(result.id_session),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, responses=_UNAUTHORIZED)
def logout(
    current: CurrentSession = Depends(get_current_session), service: AuthService = Depends(get_auth_service)
):
    """End the session that made this request. Its token stops working immediately."""
    service.logout(current)


@router.get("/sessions", response_model=list[SessionInfo], responses=_UNAUTHORIZED)
def list_sessions(
    current: CurrentSession = Depends(get_current_session), service: AuthService = Depends(get_auth_service)
):
    """The caller's live sessions, newest first."""
    return [
        SessionInfo(
            sessionId=str(s.id_session),
            current=s.id_session == current.id_session,
            userAgent=s.user_agent,
            ipAddress=s.ip_address,
            createdAt=s.created_at.replace(tzinfo=timezone.utc),  # stored as naive UTC
            expiresAt=s.expires_at.replace(tzinfo=timezone.utc),
        )
        for s in service.list_sessions(current)
    ]


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**_UNAUTHORIZED, 404: {"description": "No live session with this id for the caller"}},
)
def revoke_session(
    session_id: int,
    current: CurrentSession = Depends(get_current_session),
    service: AuthService = Depends(get_auth_service),
):
    """Sign out one of the caller's sessions, e.g. a lost device."""
    if not service.revoke_session(current, session_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="session not found")
