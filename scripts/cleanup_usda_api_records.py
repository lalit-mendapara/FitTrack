#!/usr/bin/env python3
"""
Cleanup Script: Remove Old USDA-API Records
--------------------------------------------
This script deletes all food items with region='USDA-API' from the database.
These are legacy records before the intelligent categorization system was implemented.

New USDA API items will now be auto-categorized into proper regions:
- North Indian, South Indian, Indian, Western, Continental

USAGE:
    cd backend
    python ../scripts/cleanup_usda_api_records.py
"""

import sys
import os
from pathlib import Path

# Ensure we're using the backend directory context
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent
backend_dir = project_root / 'backend'

# Change to backend directory to use its environment
os.chdir(backend_dir)
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text
from dotenv import load_dotenv

# Load environment variables from project root
load_dotenv(project_root / '.env')

from app.database import SessionLocal


def cleanup_usda_api_records():
    """Delete all food items with region='USDA-API'"""
    db = SessionLocal()
    
    try:
        # First, count how many records will be deleted
        count_query = text("SELECT COUNT(*) FROM food_items WHERE region = 'USDA-API'")
        count_result = db.execute(count_query).scalar()
        
        print(f"\n{'='*60}")
        print(f"  USDA-API Records Cleanup")
        print(f"{'='*60}")
        print(f"\nFound {count_result} records with region='USDA-API'")
        
        if count_result == 0:
            print("\n✓ No records to delete. Database is already clean!")
            return
        
        # Show sample records before deletion
        print("\nSample records to be deleted:")
        sample_query = text("""
            SELECT fdc_id, name, meal_type, region 
            FROM food_items 
            WHERE region = 'USDA-API' 
            LIMIT 5
        """)
        samples = db.execute(sample_query).fetchall()
        
        for record in samples:
            print(f"  - {record.fdc_id}: {record.name} (meal_type={record.meal_type})")
        
        if count_result > 5:
            print(f"  ... and {count_result - 5} more records")
        
        # Ask for confirmation
        print(f"\n⚠️  WARNING: This will permanently delete {count_result} records!")
        confirmation = input("\nType 'DELETE' to confirm deletion: ")
        
        if confirmation != 'DELETE':
            print("\n❌ Deletion cancelled. No changes made.")
            return
        
        # Perform deletion
        print("\n🗑️  Deleting records...")
        delete_query = text("DELETE FROM food_items WHERE region = 'USDA-API'")
        result = db.execute(delete_query)
        db.commit()
        
        deleted_count = result.rowcount
        print(f"\n✓ Successfully deleted {deleted_count} records!")
        
        # Verify deletion
        verify_query = text("SELECT COUNT(*) FROM food_items WHERE region = 'USDA-API'")
        remaining = db.execute(verify_query).scalar()
        
        if remaining == 0:
            print("✓ Verification passed: No USDA-API records remaining")
        else:
            print(f"⚠️  Warning: {remaining} USDA-API records still exist")
        
        # Show current region distribution
        print("\n" + "="*60)
        print("Current Region Distribution:")
        print("="*60)
        region_query = text("""
            SELECT region, COUNT(*) as count 
            FROM food_items 
            WHERE region IS NOT NULL 
            GROUP BY region 
            ORDER BY count DESC
        """)
        regions = db.execute(region_query).fetchall()
        
        for region in regions:
            print(f"  {region.region:20} : {region.count:5} items")
        
        print(f"\n{'='*60}\n")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error during cleanup: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("\n" + "="*60)
    print("  USDA-API Records Cleanup Script")
    print("="*60)
    print("\nThis script will remove all food items with region='USDA-API'")
    print("New USDA items will be auto-categorized into proper regions.\n")
    
    try:
        cleanup_usda_api_records()
    except KeyboardInterrupt:
        print("\n\n❌ Operation cancelled by user.")
    except Exception as e:
        print(f"\n❌ Script failed: {e}")
        sys.exit(1)
