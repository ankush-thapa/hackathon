from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import User

router = APIRouter()


@router.get("/users")
def list_users(db: Session = Depends(get_db)):
    # IDs are 63-bit snowflakes: serialize as strings so JS clients don't lose precision.
    return [{"id": str(user_id)} for (user_id,) in db.query(User.id_user).order_by(User.id_user)]
