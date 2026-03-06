from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
import csv
import io
from decimal import Decimal
from app.database import get_db
from app.models.admin import Admin
from app.utils.admin_auth import get_current_admin
from app.schemas.food_item import (
    FoodItemResponse, 
    FoodItemCreate, 
    FoodItemUpdate, 
    FoodItemListResponse
)
from app.crud import food_item as crud_food

router = APIRouter(prefix="/api/admin/foods", tags=["Admin - Foods"])

@router.get("", response_model=FoodItemListResponse)
def list_food_items(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    diet_type: Optional[str] = None,
    meal_type: Optional[str] = None,
    region: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Get paginated list of food items with optional filters"""
    skip = (page - 1) * page_size
    
    items, total = crud_food.get_food_items(
        db=db,
        skip=skip,
        limit=page_size,
        search=search,
        diet_type=diet_type,
        meal_type=meal_type,
        region=region
    )
    
    total_pages = (total + page_size - 1) // page_size
    
    return FoodItemListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

@router.get("/regions")
def get_regions(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Get list of unique regions"""
    regions = crud_food.get_unique_regions(db)
    return {"regions": regions}

@router.get("/{fdc_id}", response_model=FoodItemResponse)
def get_food_item(
    fdc_id: str,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Get a single food item by fdc_id"""
    food_item = crud_food.get_food_item(db, fdc_id)
    if not food_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Food item not found"
        )
    return food_item

@router.post("", response_model=FoodItemResponse, status_code=status.HTTP_201_CREATED)
def create_food_item(
    food_item: FoodItemCreate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Create a new food item"""
    # Check if fdc_id already exists
    existing = crud_food.get_food_item(db, food_item.fdc_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Food item with this fdc_id already exists"
        )
    
    return crud_food.create_food_item(db, food_item)

@router.put("/{fdc_id}", response_model=FoodItemResponse)
def update_food_item(
    fdc_id: str,
    food_item: FoodItemUpdate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Update an existing food item"""
    updated_item = crud_food.update_food_item(db, fdc_id, food_item)
    if not updated_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Food item not found"
        )
    return updated_item

@router.delete("/{fdc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_food_item(
    fdc_id: str,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Delete a food item"""
    success = crud_food.delete_food_item(db, fdc_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Food item not found"
        )
    return None

@router.post("/import/csv")
async def import_food_items_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Import food items from CSV file"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV"
        )
    
    contents = await file.read()
    csv_file = io.StringIO(contents.decode('utf-8'))
    csv_reader = csv.DictReader(csv_file)
    
    created_count = 0
    updated_count = 0
    errors = []
    
    for row_num, row in enumerate(csv_reader, start=2):
        try:
            # Validate required fields
            required_fields = ['fdc_id', 'name', 'diet_type', 'meal_type', 'protein_g', 'fat_g', 'carb_g', 'calories_kcal']
            missing_fields = [f for f in required_fields if not row.get(f)]
            if missing_fields:
                errors.append(f"Row {row_num}: Missing fields: {', '.join(missing_fields)}")
                continue
            
            # Check if food item exists
            existing = crud_food.get_food_item(db, row['fdc_id'])
            
            food_data = {
                'fdc_id': row['fdc_id'],
                'name': row['name'],
                'diet_type': row['diet_type'],
                'meal_type': row['meal_type'],
                'protein_g': Decimal(row['protein_g']),
                'fat_g': Decimal(row['fat_g']),
                'carb_g': Decimal(row['carb_g']),
                'calories_kcal': Decimal(row['calories_kcal']),
                'serving_size_g': Decimal(row['serving_size_g']) if row.get('serving_size_g') else None,
                'region': row.get('region'),
                'vector_text': row.get('vector_text')
            }
            
            if existing:
                # Update existing
                update_data = FoodItemUpdate(**food_data)
                crud_food.update_food_item(db, row['fdc_id'], update_data)
                updated_count += 1
            else:
                # Create new
                create_data = FoodItemCreate(**food_data)
                crud_food.create_food_item(db, create_data)
                created_count += 1
                
        except Exception as e:
            errors.append(f"Row {row_num}: {str(e)}")
    
    return {
        "created": created_count,
        "updated": updated_count,
        "errors": errors
    }

@router.get("/export/csv")
def export_food_items_csv(
    diet_type: Optional[str] = None,
    meal_type: Optional[str] = None,
    region: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Export food items to CSV file"""
    # Get all food items with filters
    items, _ = crud_food.get_food_items(
        db=db,
        skip=0,
        limit=100000,  # Get all items
        diet_type=diet_type,
        meal_type=meal_type,
        region=region
    )
    
    # Create CSV in memory
    output = io.StringIO()
    fieldnames = ['fdc_id', 'name', 'diet_type', 'meal_type', 'serving_size_g', 
                  'protein_g', 'fat_g', 'carb_g', 'calories_kcal', 'region', 'vector_text']
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    for item in items:
        writer.writerow({
            'fdc_id': item.fdc_id,
            'name': item.name,
            'diet_type': item.diet_type,
            'meal_type': item.meal_type,
            'serving_size_g': str(item.serving_size_g) if item.serving_size_g else '',
            'protein_g': str(item.protein_g),
            'fat_g': str(item.fat_g),
            'carb_g': str(item.carb_g),
            'calories_kcal': str(item.calories_kcal),
            'region': item.region or '',
            'vector_text': item.vector_text or ''
        })
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=food_items.csv"}
    )
