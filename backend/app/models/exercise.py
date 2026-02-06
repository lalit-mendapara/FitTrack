from sqlalchemy import Column, Integer, String
from app.database import Base

class Exercise(Base):
    __tablename__ = "exercises"

    id = Column("ID", Integer, primary_key=True, index=True)
    name = Column("Exercise Name", String, index=True, nullable=False)
    category = Column("Category", String, nullable=False)        # e.g., Strength, Cardio
    primary_muscle = Column("Primary Muscle", String, nullable=False)  # e.g., Back, Chest
    difficulty = Column("Difficulty", String, nullable=False)      # e.g., Advanced
    image_url = Column("Image URL", String, nullable=True)
