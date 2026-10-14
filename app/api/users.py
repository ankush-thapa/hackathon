from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import User

router = APIRouter()


@router.get("/users")
def list_users(db: Session = Depends(get_db)):
    return [{"id": user_id} for (user_id,) in db.query(User.id).order_by(User.id)]
