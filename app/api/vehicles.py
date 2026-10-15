<<<<<<< Updated upstream
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_session
from app.db.session import get_db
from app.repositories.vehicle_repo import DuplicateRegistrationError, VehicleRepository
from app.schemas.vehicle import AddVehicleRequest, VehicleResponse
from app.services.auth_service import CurrentSession
from app.services.vehicle_service import VehicleService

router = APIRouter(prefix="/v1/vehicles", tags=["vehicles"])

=======
from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import require_session
from app.db.session import get_db
from app.repositories.vehicle_repo import DuplicateRegistrationError, VehicleRepository, VehicleRow
from app.schemas.vehicle import VehicleCreate, VehicleResponse, VehicleStatus, VehicleUpdate
from app.services.vehicle_service import InactiveDefaultError, VehicleNotFoundError, VehicleService

router = APIRouter(prefix="/v1/vehicles", tags=["vehicles"])

_UNAUTHORIZED = {401: {"description": "Missing, invalid, expired, or revoked session"}}
_NOT_FOUND = {404: {"description": "No such vehicle for the caller (or it was deleted)"}}
_CONFLICT = {409: {"description": "Registration number taken, or an inactive vehicle set as default"}}

>>>>>>> Stashed changes

def get_vehicle_service(db: Session = Depends(get_db)) -> VehicleService:
    return VehicleService(VehicleRepository(db))


<<<<<<< Updated upstream
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
=======
def _response(v: VehicleRow) -> VehicleResponse:
    return VehicleResponse(
        vehicleId=str(v.id_vehicle),
        make=v.make,
        model=v.model,
        color=v.color,
        registrationNumber=v.registration_number,
        seatCapacity=v.seat_capacity,
        vehicleType=v.vehicle_type,
        isDefault=v.is_default,
        status=v.status,
        createdAt=v.created_at.replace(tzinfo=timezone.utc),  # stored as naive UTC
        updatedAt=v.updated_at.replace(tzinfo=timezone.utc),
    )


def _not_found() -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, detail="vehicle not found")


def _registration_taken() -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, detail="registration number already registered")


@router.post(
    "", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED, responses={**_UNAUTHORIZED, **_CONFLICT}
)
@require_session
def create_vehicle(req: VehicleCreate, current_user_id: int, service: VehicleService = Depends(get_vehicle_service)):
    """Add a vehicle for the caller. The first one becomes the default."""
    try:
        return _response(service.create(current_user_id, req))
    except DuplicateRegistrationError:
        raise _registration_taken() from None


@router.get("", response_model=list[VehicleResponse], responses=_UNAUTHORIZED)
@require_session
def list_vehicles(
    current_user_id: int,
    status_filter: VehicleStatus | None = Query(default=None, alias="status"),
    service: VehicleService = Depends(get_vehicle_service),
):
    """The caller's vehicles, default first. Filter with ?status=active or ?status=inactive."""
    return [_response(v) for v in service.list(current_user_id, status_filter)]


@router.get("/{vehicle_id}", response_model=VehicleResponse, responses={**_UNAUTHORIZED, **_NOT_FOUND})
@require_session
def get_vehicle(vehicle_id: int, current_user_id: int, service: VehicleService = Depends(get_vehicle_service)):
    try:
        return _response(service.get(current_user_id, vehicle_id))
    except VehicleNotFoundError:
        raise _not_found() from None


@router.patch(
    "/{vehicle_id}", response_model=VehicleResponse, responses={**_UNAUTHORIZED, **_NOT_FOUND, **_CONFLICT}
)
@require_session
def update_vehicle(
    vehicle_id: int,
    req: VehicleUpdate,
    current_user_id: int,
    service: VehicleService = Depends(get_vehicle_service),
):
    """Change some fields. isDefault=true unsets the previous default; status=inactive clears the default."""
    try:
        return _response(service.update(current_user_id, vehicle_id, req))
    except VehicleNotFoundError:
        raise _not_found() from None
    except DuplicateRegistrationError:
        raise _registration_taken() from None
    except InactiveDefaultError:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="an inactive vehicle cannot be the default") from None


@router.delete(
    "/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT, responses={**_UNAUTHORIZED, **_NOT_FOUND}
)
@require_session
def delete_vehicle(vehicle_id: int, current_user_id: int, service: VehicleService = Depends(get_vehicle_service)):
    """Soft-delete: the vehicle disappears from the API and its registration number can be used again."""
    try:
        service.delete(current_user_id, vehicle_id)
    except VehicleNotFoundError:
        raise _not_found() from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)
>>>>>>> Stashed changes
