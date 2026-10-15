from app.core.ids import new_id
from app.core.security import hash_password
from app.repositories.user_repo import NewUser, UserRepository
from app.schemas.auth import RegisterRequest


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
