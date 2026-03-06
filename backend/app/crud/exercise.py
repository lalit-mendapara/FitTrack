from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import List, Optional
from app.models.exercise import Exercise
from app.schemas.exercise import ExerciseCreate, ExerciseUpdate

def get_exercises(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    category: Optional[str] = None,
    primary_muscle: Optional[str] = None,
    difficulty: Optional[str] = None
):
    """Get paginated list of exercises with optional filters"""
    query = db.query(Exercise)
    
    # Apply filters
    if search:
        search_filter = or_(
            Exercise.name.ilike(f"%{search}%"),
            Exercise.category.ilike(f"%{search}%"),
            Exercise.primary_muscle.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)
    
    if category:
        query = query.filter(Exercise.category == category)
    
    if primary_muscle:
        query = query.filter(Exercise.primary_muscle == primary_muscle)
    
    if difficulty:
        query = query.filter(Exercise.difficulty == difficulty)
    
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    
    return items, total

def get_exercise(db: Session, exercise_id: int):
    """Get a single exercise by ID"""
    return db.query(Exercise).filter(Exercise.id == exercise_id).first()

def create_exercise(db: Session, exercise: ExerciseCreate):
    """Create a new exercise"""
    db_exercise = Exercise(**exercise.model_dump())
    db.add(db_exercise)
    db.commit()
    db.refresh(db_exercise)
    return db_exercise

def update_exercise(db: Session, exercise_id: int, exercise: ExerciseUpdate):
    """Update an existing exercise"""
    db_exercise = get_exercise(db, exercise_id)
    if not db_exercise:
        return None
    
    update_data = exercise.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_exercise, field, value)
    
    db.commit()
    db.refresh(db_exercise)
    return db_exercise

def delete_exercise(db: Session, exercise_id: int):
    """Delete an exercise"""
    db_exercise = get_exercise(db, exercise_id)
    if not db_exercise:
        return False
    
    db.delete(db_exercise)
    db.commit()
    return True

def get_unique_categories(db: Session):
    """Get list of unique categories"""
    categories = db.query(Exercise.category).distinct().filter(Exercise.category.isnot(None)).all()
    return [c[0] for c in categories if c[0]]

def get_unique_muscles(db: Session):
    """Get list of unique primary muscles"""
    muscles = db.query(Exercise.primary_muscle).distinct().filter(Exercise.primary_muscle.isnot(None)).all()
    return [m[0] for m in muscles if m[0]]

def get_unique_difficulties(db: Session):
    """Get list of unique difficulty levels"""
    difficulties = db.query(Exercise.difficulty).distinct().filter(Exercise.difficulty.isnot(None)).all()
    return [d[0] for d in difficulties if d[0]]

def get_exercise_count(db: Session):
    """Get total count of exercises"""
    return db.query(func.count(Exercise.id)).scalar()
