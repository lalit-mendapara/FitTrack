from pydantic import BaseModel, Field, HttpUrl
from typing import Optional

class ExerciseBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    category: str = Field(..., description="e.g., Strength, Cardio, Flexibility, Sports")
    primary_muscle: str = Field(..., description="e.g., Chest, Back, Legs, Arms, Core, Full Body")
    difficulty: str = Field(..., description="e.g., Beginner, Intermediate, Advanced")
    image_url: Optional[str] = Field(None, description="URL to exercise demonstration image")

class ExerciseCreate(ExerciseBase):
    pass

class ExerciseUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    category: Optional[str] = None
    primary_muscle: Optional[str] = None
    difficulty: Optional[str] = None
    image_url: Optional[str] = None

class ExerciseResponse(ExerciseBase):
    id: int
    
    class Config:
        from_attributes = True

class ExerciseListResponse(BaseModel):
    items: list[ExerciseResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
