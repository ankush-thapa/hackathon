import functools
import inspect
from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.session_repo import SessionRepository
from app.repositories.user_repo import UserRepository
from app.services.auth_service import AuthService, CurrentSession, InvalidSessionError, SessionReason

bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="AccessToken",
    bearerFormat="JWT",
    description="Paste the `accessToken` from POST /v1/auth/login (without the word Bearer).",
)

SESSION_ERROR_MESSAGES = {
    SessionReason.token_missing: "missing bearer token",
    SessionReason.token_invalid: "invalid token",
    SessionReason.token_expired: "user session expired, refresh the token",
    SessionReason.session_expired: "user session expired, log in again",
    SessionReason.session_revoked: "session revoked",
    SessionReason.account_inactive: "account inactive",
}


def session_error(reason: SessionReason) -> HTTPException:
    """401 with a machine-readable reason, so clients know whether to refresh or log in again."""
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        detail={"code": reason.value, "message": SESSION_ERROR_MESSAGES[reason]},
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(UserRepository(db), SessionRepository(db))


def get_current_session(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    service: AuthService = Depends(get_auth_service),
) -> CurrentSession:
    """Require `Authorization: Bearer <token>` for a live session."""
    try:
        if credentials is None:
            raise InvalidSessionError(SessionReason.token_missing)
        return service.authenticate(credentials.credentials)
    except InvalidSessionError as e:
        raise session_error(e.reason) from None


def get_current_user_id(current: CurrentSession = Depends(get_current_session)) -> int:
    return current.id_user


def require_session(endpoint: Callable) -> Callable:
    """Protect a route: 401 unless the request carries a live session's access token.

    The logged-in user's id is passed as `current_user_id` when the endpoint declares it.
    Put it below the route decorator:

        @router.get("/trips")
        @require_session
        def list_trips(current_user_id: int):
            ...
    """
    signature = inspect.signature(endpoint)
    wants_user_id = "current_user_id" in signature.parameters
    params = [p for p in signature.parameters.values() if p.name != "current_user_id"]
    injected = inspect.Parameter(
        "current_user_id", inspect.Parameter.KEYWORD_ONLY, default=Depends(get_current_user_id), annotation=int
    )
    # Keyword-only parameters must come before **kwargs.
    at = next((i for i, p in enumerate(params) if p.kind is inspect.Parameter.VAR_KEYWORD), len(params))
    params.insert(at, injected)

    def call_args(kwargs: dict, current_user_id: int) -> dict:
        return {**kwargs, "current_user_id": current_user_id} if wants_user_id else kwargs

    if inspect.iscoroutinefunction(endpoint):
        @functools.wraps(endpoint)
        async def wrapper(*args, current_user_id: int, **kwargs):
            return await endpoint(*args, **call_args(kwargs, current_user_id))
    else:
        @functools.wraps(endpoint)
        def wrapper(*args, current_user_id: int, **kwargs):
            return endpoint(*args, **call_args(kwargs, current_user_id))

    # FastAPI reads this signature to resolve dependencies, so the session check runs first.
    wrapper.__signature__ = signature.replace(parameters=params)
    return wrapper
