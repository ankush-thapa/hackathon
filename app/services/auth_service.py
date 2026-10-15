from datetime import datetime, timezone

from app.core.ids import new_id
from app.core.security import create_access_token, hash_password, verify_password_or_dummy
from app.repositories.user_repo import NewUser, UserRepository
from app.schemas.auth import RegisterRequest, LoginRequest


class InvalidCredentialsError(Exception):
    pass


class AccountBlockedError(Exception):
    pass


class AuthService:
    def __init__(self, users: UserRepository):
        self._users = users

    def register(self, req: RegisterRequest) -> NewUser:
        # Raises DuplicateUserError on email/phone clash.
        return self._users.create(
            id_user=new_id(),
            email=req.email,
            phone_number=req.phone,
            password_hash=hash_password(req.password),
        )
        # TODO: emit UserRegistered event / send email + phone OTP once verification exists.

    def login(self, req: LoginRequest) -> tuple[int, str, int]:
        """Return (id_user, access token, expires_in seconds)."""
        creds = self._users.get_credentials(email=req.email, phone_number=req.phone)
        # Always run the hash check so unknown accounts are not distinguishable by timing.
        if not verify_password_or_dummy(req.password, creds.password_hash if creds else None):
            raise InvalidCredentialsError
        if creds.status == "deleted":
            raise InvalidCredentialsError
        if creds.status != "active":
            raise AccountBlockedError
        self._users.touch_last_active(creds.id_user, datetime.now(timezone.utc).replace(tzinfo=None))
        token, expires_in = create_access_token(creds.id_user)
        return creds.id_user, token, expires_in
