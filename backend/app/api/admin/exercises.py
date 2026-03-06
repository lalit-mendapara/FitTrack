from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
import csv
import io
from app.database import get_db
from app.models.admin import Admin
from app.utils.admin_auth import get_current_admin
from app.schemas.exercise import (
    ExerciseResponse, 
    ExerciseCreate, 
    ExerciseUpdate, 
    ExerciseListResponse
)
from app.crud import exercise as crud_exercise

router = APIRouter(prefix="/api/admin/exercises", tags=["Admin - Exercises"])

@router.get("", response_model=ExerciseListResponse)
def list_exercises(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    category: Optional[str] = None,
    primary_muscle: Optional[str] = None,
    difficulty: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Get paginated list of exercises with optional filters"""
    skip = (page - 1) * page_size
    
    items, total = crud_exercise.get_exercises(
        db=db,
        skip=skip,
        limit=page_size,
        search=search,
        category=category,
        primary_muscle=primary_muscle,
        difficulty=difficulty
    )
    
    total_pages = (total + page_size - 1) // page_size
    
    return ExerciseListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

@router.get("/categories")
def get_categories(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Get list of unique categories"""
    categories = crud_exercise.get_unique_categories(db)
    return {"categories": categories}

@router.get("/muscles")
def get_muscles(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Get list of unique primary muscles"""
    muscles = crud_exercise.get_unique_muscles(db)
    return {"muscles": muscles}

@router.get("/difficulties")
def get_difficulties(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Get list of unique difficulty levels"""
    difficulties = crud_exercise.get_unique_difficulties(db)
    return {"difficulties": difficulties}

@router.get("/{exercise_id}", response_model=ExerciseResponse)
def get_exercise(
    exercise_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Get a single exercise by ID"""
    exercise = crud_exercise.get_exercise(db, exercise_id)
    if not exercise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exercise not found"
        )
    return exercise

@router.post("", response_model=ExerciseResponse, status_code=status.HTTP_201_CREATED)
def create_exercise(
    exercise: ExerciseCreate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Create a new exercise"""
    return crud_exercise.create_exercise(db, exercise)

@router.put("/{exercise_id}", response_model=ExerciseResponse)
def update_exercise(
    exercise_id: int,
    exercise: ExerciseUpdate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Update an existing exercise"""
    updated_exercise = crud_exercise.update_exercise(db, exercise_id, exercise)
    if not updated_exercise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exercise not found"
        )
    return updated_exercise

@router.delete("/{exercise_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exercise(
    exercise_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Delete an exercise"""
    success = crud_exercise.delete_exercise(db, exercise_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exercise not found"
        )
    return None

@router.post("/import/csv")
async def import_exercises_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Import exercises from CSV file"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV"
        )
    
    contents = await file.read()
    csv_file = io.StringIO(contents.decode('utf-8'))
    csv_reader = csv.DictReader(csv_file)
    
    created_count = 0
    errors = []
    
    for row_num, row in enumerate(csv_reader, start=2):
        try:
            # Validate required fields
            required_fields = ['name', 'category', 'primary_muscle', 'difficulty']
            missing_fields = [f for f in required_fields if not row.get(f)]
            if missing_fields:
                errors.append(f"Row {row_num}: Missing fields: {', '.join(missing_fields)}")
                continue
            
            exercise_data = {
                'name': row['name'],
                'category': row['category'],
                'primary_muscle': row['primary_muscle'],
                'difficulty': row['difficulty'],
                'image_url': row.get('image_url') or None
            }
            
            # Create new exercise
            create_data = ExerciseCreate(**exercise_data)
            crud_exercise.create_exercise(db, create_data)
            created_count += 1
                
        except Exception as e:
            errors.append(f"Row {row_num}: {str(e)}")
    
    return {
        "created": created_count,
        "errors": errors
    }

@router.get("/export/csv")
def export_exercises_csv(
    category: Optional[str] = None,
    primary_muscle: Optional[str] = None,
    difficulty: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Export exercises to CSV file"""
    # Get all exercises with filters
    items, _ = crud_exercise.get_exercises(
        db=db,
        skip=0,
        limit=100000,  # Get all items
        category=category,
        primary_muscle=primary_muscle,
        difficulty=difficulty
    )
    
    # Create CSV in memory
    output = io.StringIO()
    fieldnames = ['id', 'name', 'category', 'primary_muscle', 'difficulty', 'image_url']
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    for item in items:
        writer.writerow({
            'id': item.id,
            'name': item.name,
            'category': item.category,
            'primary_muscle': item.primary_muscle,
            'difficulty': item.difficulty,
            'image_url': item.image_url or ''
        })
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=exercises.csv"}
    )
