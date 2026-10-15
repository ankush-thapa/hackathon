from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings
from app.core.ids import new_id
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password_or_dummy
from app.repositories.session_repo import SessionRepository, SessionRow
from app.repositories.user_repo import NewUser, UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest


class InvalidCredentialsError(Exception):
    pass


class AccountBlockedError(Exception):
    pass


class InvalidSessionError(Exception):
    """Token is malformed, expired, revoked, or belongs to a user who can no longer sign in."""


@dataclass(frozen=True)
class LoginResult:
    id_user: int
    id_session: int
    access_token: str
    expires_in: int  # seconds


@dataclass(frozen=True)
class CurrentSession:
    id_user: int
    id_session: int


def _utcnow() -> datetime:
    # Naive UTC: DATETIME(3) columns carry no zone.
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AuthService:
    def __init__(self, users: UserRepository, sessions: SessionRepository):
        self._users = users
        self._sessions = sessions

    def register(self, req: RegisterRequest) -> NewUser:
        # Raises DuplicateUserError on email/phone clash.
        return self._users.create(
            id_user=new_id(),
            email=req.email,
            phone_number=req.phone,
            password_hash=hash_password(req.password),
        )
        # TODO: emit UserRegistered event / send email + phone OTP once verification exists.

    def login(self, req: LoginRequest, user_agent: str | None, ip_address: str | None) -> LoginResult:
        creds = self._users.get_credentials(email=req.email, phone_number=req.phone)
        # Always run the hash check so unknown accounts are not distinguishable by timing.
        if not verify_password_or_dummy(req.password, creds.password_hash if creds else None):
            raise InvalidCredentialsError
        if creds.status == "deleted":
            raise InvalidCredentialsError
        if creds.status != "active":
            raise AccountBlockedError

        now = _utcnow()
        expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        expires_at = now + timedelta(seconds=expires_in)
        id_session = new_id()
        self._sessions.create(
            id_session=id_session,
            id_user=creds.id_user,
            user_agent=user_agent[:255] if user_agent else None,
            ip_address=ip_address,
            created_at=now,
            expires_at=expires_at,
        )
        self._users.touch_last_active(creds.id_user, now)
        token = create_access_token(
            creds.id_user, id_session,
            issued_at=now.replace(tzinfo=timezone.utc), expires_at=expires_at.replace(tzinfo=timezone.utc),
        )
        return LoginResult(creds.id_user, id_session, token, expires_in)

    def authenticate(self, token: str) -> CurrentSession:
        """Resolve a bearer token to its live session, or raise InvalidSessionError."""
        try:
            claims = decode_access_token(token)
            id_session, id_user = int(claims["sid"]), int(claims["sub"])
        except (jwt.InvalidTokenError, ValueError):
            raise InvalidSessionError from None
        session = self._sessions.get_active(id_session, _utcnow())
        if session is None or session.id_user != id_user or session.user_status != "active":
            raise InvalidSessionError
        return CurrentSession(id_user=id_user, id_session=id_session)

    def logout(self, current: CurrentSession) -> None:
        self._sessions.revoke(current.id_session, current.id_user, _utcnow())

    def list_sessions(self, current: CurrentSession) -> list[SessionRow]:
        return self._sessions.list_active(current.id_user, _utcnow())

    def revoke_session(self, current: CurrentSession, id_session: int) -> bool:
        return self._sessions.revoke(id_session, current.id_user, _utcnow())
