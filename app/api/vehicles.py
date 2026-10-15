from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_session
from app.db.session import get_db
from app.repositories.vehicle_repo import DuplicateRegistrationError, VehicleRepository
from app.schemas.vehicle import AddVehicleRequest, VehicleResponse
from app.services.auth_service import CurrentSession
from app.services.vehicle_service import VehicleService

router = APIRouter(prefix="/v1/vehicles", tags=["vehicles"])


def get_vehicle_service(db: Session = Depends(get_db)) -> VehicleService:
    return VehicleService(VehicleRepository(db))


@router.post(
    "",
    response_model=VehicleResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"description": "Missing, invalid, expired, or revoked session"},
        409: {"description": "Registration number already registered"},
    },
)
def add_vehicle(
    req: AddVehicleRequest,
    current: CurrentSession = Depends(get_current_session),
    service: VehicleService = Depends(get_vehicle_service),
):
    """Add a vehicle for the logged-in user. Upload the photo to POST /v1/media/upload first and send its `url`."""
    try:
        return service.add(current.id_user, req)
    except DuplicateRegistrationError:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="registration_number already registered")
