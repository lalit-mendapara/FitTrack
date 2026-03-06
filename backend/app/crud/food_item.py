from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import List, Optional
from app.models.food_item import FoodItem
from app.schemas.food_item import FoodItemCreate, FoodItemUpdate

def get_food_items(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    diet_type: Optional[str] = None,
    meal_type: Optional[str] = None,
    region: Optional[str] = None
):
    """Get paginated list of food items with optional filters"""
    query = db.query(FoodItem)
    
    # Apply filters
    if search:
        search_filter = or_(
            FoodItem.name.ilike(f"%{search}%"),
            FoodItem.fdc_id.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)
    
    if diet_type:
        query = query.filter(FoodItem.diet_type == diet_type)
    
    if meal_type:
        query = query.filter(FoodItem.meal_type == meal_type)
    
    if region:
        query = query.filter(FoodItem.region == region)
    
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    
    return items, total

def get_food_item(db: Session, fdc_id: str):
    """Get a single food item by fdc_id"""
    return db.query(FoodItem).filter(FoodItem.fdc_id == fdc_id).first()

def create_food_item(db: Session, food_item: FoodItemCreate):
    """Create a new food item"""
    db_food_item = FoodItem(**food_item.model_dump())
    db.add(db_food_item)
    db.commit()
    db.refresh(db_food_item)
    return db_food_item

def update_food_item(db: Session, fdc_id: str, food_item: FoodItemUpdate):
    """Update an existing food item"""
    db_food_item = get_food_item(db, fdc_id)
    if not db_food_item:
        return None
    
    update_data = food_item.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_food_item, field, value)
    
    db.commit()
    db.refresh(db_food_item)
    return db_food_item

def delete_food_item(db: Session, fdc_id: str):
    """Delete a food item"""
    db_food_item = get_food_item(db, fdc_id)
    if not db_food_item:
        return False
    
    db.delete(db_food_item)
    db.commit()
    return True

def get_unique_regions(db: Session):
    """Get list of unique regions"""
    regions = db.query(FoodItem.region).distinct().filter(FoodItem.region.isnot(None)).all()
    return [r[0] for r in regions if r[0]]

def get_food_count(db: Session):
    """Get total count of food items"""
    return db.query(func.count(FoodItem.fdc_id)).scalar()
