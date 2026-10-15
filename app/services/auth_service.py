import enum
import hmac
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings
from app.core.ids import new_id
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    new_refresh_token,
    parse_refresh_token,
    verify_password_or_dummy,
)
from app.repositories.session_repo import SessionRepository, SessionRow, SessionState
from app.repositories.user_repo import NewUser, UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest


class InvalidCredentialsError(Exception):
    pass


class AccountBlockedError(Exception):
    pass


class SessionReason(str, enum.Enum):
    """Why a token or session is not usable. The client action is in brackets."""

    token_missing = "token_missing"  # no bearer token sent [log in]
    token_invalid = "token_invalid"  # malformed, bad signature, or unknown session [log in]
    token_expired = "token_expired"  # access token past its exp [call /refresh]
    session_expired = "session_expired"  # session past its absolute lifetime [log in]
    session_revoked = "session_revoked"  # logged out, revoked remotely, or refresh token reused [log in]
    account_inactive = "account_inactive"  # user is blocked or deleted [log in fails too]


class InvalidSessionError(Exception):
    def __init__(self, reason: SessionReason):
        self.reason = reason
        super().__init__(reason.value)


@dataclass(frozen=True)
class LoginResult:
    id_user: int
    id_session: int
    access_token: str
    expires_in: int  # seconds
    refresh_token: str
    session_expires_at: datetime  # naive UTC
    is_profile_completed: bool  # false → client routes the user to profile setup


@dataclass(frozen=True)
class CurrentSession:
    id_user: int
    id_session: int


def _utcnow() -> datetime:
    # Naive UTC: DATETIME(3) columns carry no zone.
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _check_live(state: SessionState | None, now: datetime) -> SessionState:
    if state is None:
        raise InvalidSessionError(SessionReason.token_invalid)
    if state.revoked_at is not None:
        raise InvalidSessionError(SessionReason.session_revoked)
    if state.expires_at <= now:
        raise InvalidSessionError(SessionReason.session_expired)
    if state.user_status != "active":
        raise InvalidSessionError(SessionReason.account_inactive)
    return state


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
        id_session = new_id()
        refresh_token, refresh_hash = new_refresh_token(id_session)
        session_expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        self._sessions.create(
            id_session=id_session,
            id_user=creds.id_user,
            user_agent=user_agent[:255] if user_agent else None,
            ip_address=ip_address,
            created_at=now,
            expires_at=session_expires_at,
            refresh_token_hash=refresh_hash,
        )
        self._users.touch_last_active(creds.id_user, now)
        return self._issue(
            creds.id_user, id_session, session_expires_at, refresh_token, now, creds.is_profile_completed
        )

    def refresh(self, refresh_token: str) -> LoginResult:
        """Trade a refresh token for new tokens. Each refresh token works once."""
        parsed = parse_refresh_token(refresh_token)
        if parsed is None:
            raise InvalidSessionError(SessionReason.token_invalid)
        id_session, presented_hash = parsed
        now = _utcnow()
        state = _check_live(self._sessions.get_state(id_session), now)
        if state.refresh_token_hash is None:  # session from before refresh tokens existed
            raise InvalidSessionError(SessionReason.token_invalid)

        new_token, new_hash = new_refresh_token(id_session)
        if not (
            hmac.compare_digest(presented_hash, state.refresh_token_hash)
            and self._sessions.rotate_refresh(id_session, presented_hash, new_hash, now)
        ):
            # An already-used refresh token came back: assume it leaked and end the session.
            self._sessions.revoke(id_session, state.id_user, now)
            raise InvalidSessionError(SessionReason.session_revoked)
        return self._issue(
            state.id_user, id_session, state.expires_at, new_token, now,
            self._users.is_profile_completed(state.id_user),
        )

    def _issue(
        self,
        id_user: int,
        id_session: int,
        session_expires_at: datetime,
        refresh_token: str,
        now: datetime,
        is_profile_completed: bool,
    ) -> LoginResult:
        # An access token never outlives its session.
        token_expires_at = min(now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES), session_expires_at)
        access_token = create_access_token(
            id_user, id_session,
            issued_at=now.replace(tzinfo=timezone.utc), expires_at=token_expires_at.replace(tzinfo=timezone.utc),
        )
        expires_in = int((token_expires_at - now).total_seconds())
        return LoginResult(
            id_user, id_session, access_token, expires_in, refresh_token, session_expires_at, is_profile_completed
        )

    def authenticate(self, token: str) -> CurrentSession:
        """Resolve a bearer token to its live session, or raise InvalidSessionError with the reason."""
        try:
            claims = decode_access_token(token)
            id_session, id_user = int(claims["sid"]), int(claims["sub"])
        except jwt.ExpiredSignatureError:
            raise InvalidSessionError(SessionReason.token_expired) from None
        except (jwt.InvalidTokenError, ValueError):
            raise InvalidSessionError(SessionReason.token_invalid) from None
        state = self._sessions.get_state(id_session)
        if state is not None and state.id_user != id_user:
            state = None
        _check_live(state, _utcnow())
        return CurrentSession(id_user, id_session)

    def logout(self, current: CurrentSession) -> None:
        self._sessions.revoke(current.id_session, current.id_user, _utcnow())

    def list_sessions(self, current: CurrentSession) -> list[SessionRow]:
        return self._sessions.list_active(current.id_user, _utcnow())

    def revoke_session(self, current: CurrentSession, id_session: int) -> bool:
        return self._sessions.revoke(id_session, current.id_user, _utcnow())
