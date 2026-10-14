from sqlalchemy import Column, Integer, String

from app.db.session import Base


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
