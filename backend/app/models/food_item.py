from sqlalchemy import Column, Integer, String, Float, Boolean, Numeric
from app.database import Base

class FoodItem(Base):
    __tablename__ = "food_items"

    fdc_id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    diet_type = Column(String, nullable=False)  # "veg", "non-veg"
    meal_type = Column(String, nullable=False)  # "breakfast", "lunch", "dinner", "snacks"
    
    serving_size_g = Column(Numeric, nullable=True)
    protein_g = Column(Numeric, nullable=False)
    fat_g = Column(Numeric, nullable=False)
    carb_g = Column(Numeric, nullable=False)
    calories_kcal = Column(Numeric, nullable=False)
    
    region = Column(String, nullable=True)
    vector_text = Column(String, nullable=True)
