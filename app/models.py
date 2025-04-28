from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False)    
    hashed_password = Column(String(128), nullable=False)
    first_name = Column(String(64), nullable=False)
    last_name  = Column(String(64), nullable=False)
    country = Column(String(64), nullable=False)
    phone = Column(String(20), unique=True, nullable=True)
    created_at = Column(DateTime(timezone=True),
                        server_default=func.now(),
                        nullable=False)
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(),
                        onupdate=func.now(),
                        nullable=False)
    
    def __repr__(self) -> str:
            return f"<User {self.id} {self.email}>"