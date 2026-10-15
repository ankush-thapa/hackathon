from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.session_repo import SessionRepository
from app.repositories.user_repo import UserRepository
from app.services.auth_service import AuthService, CurrentSession, InvalidSessionError

_bearer = HTTPBearer(auto_error=False)


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(UserRepository(db), SessionRepository(db))


def get_current_session(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    service: AuthService = Depends(get_auth_service),
) -> CurrentSession:
    """Require `Authorization: Bearer <token>` for a live session. Add to any protected route."""
    try:
        if credentials is None:
            raise InvalidSessionError
        return service.authenticate(credentials.credentials)
    except InvalidSessionError:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="invalid or expired session", headers={"WWW-Authenticate": "Bearer"}
        ) from None
