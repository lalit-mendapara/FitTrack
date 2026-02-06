from sqlalchemy import Column, Integer, String, Date
from app.database import Base
from sqlalchemy.orm import relationship,validates
from datetime import date

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password = Column(String(200), nullable=False)
    dob = Column(Date)
    gender = Column(String(10))
    age = Column(Integer)

    @validates('dob')
    def update_age(self, key, dob_value):
        if dob_value:
            today = date.today()
            self.age = today.year - dob_value.year - ((today.month, today.day) < (dob_value.month, dob_value.day))
        return dob_value
    
    profile = relationship("UserProfile",back_populates="user")