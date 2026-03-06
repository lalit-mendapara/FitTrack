from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal

class FoodItemBase(BaseModel):
    name: str
    diet_type: str  # "veg", "non-veg"
    meal_type: str  # "breakfast", "lunch", "dinner", "snacks"
    serving_size_g: Optional[Decimal] = None
    protein_g: Decimal
    fat_g: Decimal
    carb_g: Decimal
    calories_kcal: Decimal
    region: Optional[str] = None
    vector_text: Optional[str] = None

class FoodItemCreate(FoodItemBase):
    fdc_id: str

class FoodItemUpdate(BaseModel):
    name: Optional[str] = None
    diet_type: Optional[str] = None
    meal_type: Optional[str] = None
    serving_size_g: Optional[Decimal] = None
    protein_g: Optional[Decimal] = None
    fat_g: Optional[Decimal] = None
    carb_g: Optional[Decimal] = None
    calories_kcal: Optional[Decimal] = None
    region: Optional[str] = None
    vector_text: Optional[str] = None

class FoodItemResponse(FoodItemBase):
    fdc_id: str
    
    class Config:
        from_attributes = True

class FoodItemListResponse(BaseModel):
    items: list[FoodItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
