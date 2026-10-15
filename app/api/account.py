from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.schemas.account import AccountResponse, ChangePasswordRequest, ContactUpdateRequest, PasswordConfirmation
from app.services.account_service import AccountService

router = APIRouter(prefix="/v1/auth", tags=["account"], responses={401: {"description": "Missing/invalid session"}, 403: {"description": "Incorrect current password"}, 409: {"description": "State/contact conflict"}})


def service(db: Session = Depends(get_db)):
    return AccountService(db)


@router.patch("/account", response_model=AccountResponse)
def update_contacts(request: ContactUpdateRequest, user: int = Depends(get_current_user_id), account: AccountService = Depends(service)):
    """Change email and/or phone with current_password. No OTP/verification is performed."""
    return account.contacts(user, request)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(request: ChangePasswordRequest, user: int = Depends(get_current_user_id), account: AccountService = Depends(service)):
    """Change password and revoke ALL sessions, including this one. Log in again afterward."""
    account.password(user, request)


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(request: PasswordConfirmation, user: int = Depends(get_current_user_id), account: AccountService = Depends(service)):
    """Soft-delete account, revoke sessions, deactivate documents/vehicles, cancel future rides/bookings.

    Body requires current_password. Active started rides must finish first. Historical records are retained.
    """
    account.delete(user, request.current_password)
