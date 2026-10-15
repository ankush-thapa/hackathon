from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import User

router = APIRouter()


@router.get("/hello/{user_id}")
def hello(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    name = user.profile.full_name if user.profile else (user.user_name or user.email or user.phone_number)
    return {"message": f"Hello {name}"}
