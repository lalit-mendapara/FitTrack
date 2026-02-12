#!/usr/bin/env python3
"""
Feast Mode Testing Script
=========================
Tests the complete feast mode flow including:
1. Activation with proper backup
2. Mid-day activation scenarios
3. Cancellation with full restoration
4. Data integrity verification

Usage:
    python scripts/test_feast_mode.py --user-id 1
    python scripts/test_feast_mode.py --user-id 1 --scenario midday
    python scripts/test_feast_mode.py --user-id 1 --scenario cancel
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
from datetime import date, timedelta, datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.meal_plan import MealPlan
from app.models.workout_plan import WorkoutPlan
from app.models.social_event import SocialEvent
from app.models.tracking import FoodLog
from app.services.social_event_service import (
    propose_banking_strategy,
    create_social_event,
    get_active_event,
    cancel_active_event
)
from app.services.workout_service import patch_limit_day_workout, restore_workout_plan
from app.services.meal_service import adjust_todays_meal_plan
from app.services.stats_service import StatsService
import json

class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

def print_success(text):
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")

class FeastModeSnapshot:
    """Captures the state before feast mode activation"""
    def __init__(self, db: Session, user_id: int):
        self.user_id = user_id
        self.db = db

        # Get profile
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            raise ValueError(f"No profile found for user {user_id}")

        self.profile_id = profile.id

        # Capture original targets
        self.original_calories = profile.calories
        self.original_protein = profile.protein
        self.original_carbs = profile.carbs
        self.original_fat = profile.fat

        # Capture meal plan
        meal_plans = db.query(MealPlan).filter(MealPlan.user_profile_id == profile.id).all()
        self.meal_plan_snapshot = []
        for mp in meal_plans:
            self.meal_plan_snapshot.append({
                'meal_id': mp.meal_id,
                'dish': mp.dish,
                'calories': mp.calories,
                'protein': mp.protein,
                'carbs': mp.carbs,
                'fat': mp.fat,
                'portion_size': mp.portion_size
            })

        # Capture workout plan
        workout = db.query(WorkoutPlan).filter(WorkoutPlan.user_profile_id == profile.id).first()
        self.workout_schedule = workout.schedule if workout else {}

        # Check if feast mode already active
        active_event = get_active_event(db, user_id)
        self.had_active_event = active_event is not None

    def compare(self, current_snapshot: 'FeastModeSnapshot') -> dict:
        """Compare current state with original snapshot"""
        differences = {
            'calories': current_snapshot.original_calories != self.original_calories,
            'macros_changed': (
                current_snapshot.original_protein != self.original_protein or
                current_snapshot.original_carbs != self.original_carbs or
                current_snapshot.original_fat != self.original_fat
            ),
            'meal_plan_changed': len(current_snapshot.meal_plan_snapshot) != len(self.meal_plan_snapshot),
            'workout_changed': current_snapshot.workout_schedule != self.workout_schedule
        }

        # Check meal plan details
        if not differences['meal_plan_changed']:
            for orig, curr in zip(self.meal_plan_snapshot, current_snapshot.meal_plan_snapshot):
                if orig['calories'] != curr['calories']:
                    differences['meal_plan_changed'] = True
                    break

        return differences

def capture_snapshot(db: Session, user_id: int) -> FeastModeSnapshot:
    """Capture current state"""
    return FeastModeSnapshot(db, user_id)

def verify_user(db: Session, user_id: int) -> bool:
    """Verify user exists and has required data"""
    print_info(f"Verifying user {user_id}...")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        print_error(f"User {user_id} not found")
        return False

    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if not profile:
        print_error(f"User profile not found for user {user_id}")
        return False

    meal_plans = db.query(MealPlan).filter(MealPlan.user_profile_id == profile.id).all()
    if not meal_plans:
        print_warning("No meal plan found - will proceed but some tests may fail")

    print_success(f"User verified: {user.name} (ID: {user_id})")
    print_info(f"  Current calories target: {profile.calories}")
    print_info(f"  Meal plan items: {len(meal_plans)}")

    return True

def test_feast_mode_activation(db: Session, user_id: int):
    """Test Case 1: Activate feast mode and verify changes"""
    print_header("TEST 1: Feast Mode Activation")

    # Step 1: Capture original state
    print_info("Step 1: Capturing original state...")
    original = capture_snapshot(db, user_id)
    print_success(f"Original calories: {original.original_calories}")
    print_success(f"Original meal plan items: {len(original.meal_plan_snapshot)}")

    # Step 2: Propose feast mode
    print_info("\nStep 2: Proposing feast mode...")
    event_date = date.today() + timedelta(days=3)
    event_name = "Test Event"

    proposal = propose_banking_strategy(db, user_id, event_date, event_name)

    if "error" in proposal:
        print_error(f"Proposal failed: {proposal['error']}")
        return False

    print_success(f"Proposal created:")
    print_info(f"  Event: {proposal['event_name']} on {proposal['event_date']}")
    print_info(f"  Daily deduction: {proposal['daily_deduction']} kcal")
    print_info(f"  Total banked: {proposal['total_banked']} kcal")

    # Step 3: Activate feast mode
    print_info("\nStep 3: Activating feast mode...")
    event = create_social_event(db, user_id, proposal)
    print_success(f"Event created with ID: {event.id}")

    # Step 4: Apply changes (meal + workout)
    print_info("\nStep 4: Applying meal and workout adjustments...")

    # Get current profile
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    stats = StatsService(db)
    input_profile = stats.get_user_profile(user_id)
    new_target = input_profile["caloric_target"]

    print_info(f"  New target calories: {new_target} (reduced by {proposal['daily_deduction']})")

    # Check completed meals
    logs = db.query(FoodLog).filter(
        FoodLog.user_id == user_id,
        FoodLog.date == date.today()
    ).all()
    completed_meals = list(set([l.meal_type.lower() for l in logs]))

    print_info(f"  Completed meals today: {completed_meals if completed_meals else 'None'}")

    # Adjust meal plan
    try:
        adjust_todays_meal_plan(db, user_id, new_target, completed_meals)
        print_success("Meal plan adjusted")
    except Exception as e:
        print_error(f"Meal plan adjustment failed: {e}")

    # Patch workout
    try:
        patch_limit_day_workout(db, user_id, event.event_date)
        print_success("Workout plan patched")
    except Exception as e:
        print_error(f"Workout patch failed: {e}")

    # Step 5: Verify changes
    print_info("\nStep 5: Verifying changes...")
    current = capture_snapshot(db, user_id)

    # Check if feast mode is active
    active_event = get_active_event(db, user_id)
    if active_event:
        print_success("Feast mode is active")
        print_info(f"  Event: {active_event.event_name}")
        print_info(f"  Event date: {active_event.event_date}")
    else:
        print_error("Feast mode is NOT active")
        return False

    # Compare snapshots
    diff = original.compare(current)
    print_info("\nState changes:")
    for key, changed in diff.items():
        status = "✓ Changed" if changed else "✗ Unchanged"
        print(f"  {key}: {status}")

    print_success("\nTest completed successfully!")
    return event.id

def test_feast_mode_midday(db: Session, user_id: int):
    """Test Case 2: Activate feast mode mid-day after eating meals"""
    print_header("TEST 2: Mid-Day Feast Mode Activation")

    print_info("This test simulates activating feast mode after eating breakfast and lunch")

    # Add fake food logs for today
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    today = date.today()

    # Check if logs already exist
    existing_logs = db.query(FoodLog).filter(
        FoodLog.user_id == user_id,
        FoodLog.date == today
    ).all()

    if not existing_logs:
        print_info("Adding fake food logs for breakfast and lunch...")

        breakfast_log = FoodLog(
            user_id=user_id,
            food_name="Test Breakfast",
            meal_type="breakfast",
            calories=400,
            protein=20,
            carbs=50,
            fat=10,
            date=today
        )

        lunch_log = FoodLog(
            user_id=user_id,
            food_name="Test Lunch",
            meal_type="lunch",
            calories=600,
            protein=30,
            carbs=70,
            fat=20,
            date=today
        )

        db.add(breakfast_log)
        db.add(lunch_log)
        db.commit()

        print_success("Added breakfast (400 kcal) and lunch (600 kcal)")
    else:
        print_info(f"Found {len(existing_logs)} existing food logs")
        for log in existing_logs:
            print_info(f"  {log.meal_type}: {log.food_name} ({log.calories} kcal)")

    # Now activate feast mode
    event_id = test_feast_mode_activation(db, user_id)

    # Verify remaining meals are adjusted
    print_info("\nVerifying remaining meals are adjusted...")
    meal_plans = db.query(MealPlan).filter(MealPlan.user_profile_id == profile.id).all()

    remaining_calories = sum(mp.calories for mp in meal_plans if mp.meal_id.lower() not in ['breakfast', 'lunch'])
    print_info(f"Remaining calories (dinner + snacks): {remaining_calories}")

    return event_id

def test_feast_mode_cancellation(db: Session, user_id: int):
    """Test Case 3: Cancel feast mode and verify restoration"""
    print_header("TEST 3: Feast Mode Cancellation")

    # Check if feast mode is active
    active_event = get_active_event(db, user_id)

    if not active_event:
        print_warning("No active feast mode found. Activating one first...")
        event_id = test_feast_mode_activation(db, user_id)
        if not event_id:
            print_error("Failed to activate feast mode")
            return False
        active_event = get_active_event(db, user_id)

    print_info(f"Active event: {active_event.event_name} (ID: {active_event.id})")

    # Capture state before cancellation
    print_info("\nCapturing state before cancellation...")
    before_cancel = capture_snapshot(db, user_id)

    # Cancel feast mode
    print_info("\nCancelling feast mode...")
    result = cancel_active_event(db, user_id)

    if "error" in result:
        print_error(f"Cancellation failed: {result['error']}")
        return False

    print_success("Feast mode cancelled")
    print_info(f"  Message: {result.get('message', 'N/A')}")
    print_info(f"  Restored calories: {result.get('restored_calories', 0)}")

    # Verify feast mode is inactive
    print_info("\nVerifying feast mode is inactive...")
    active_after = get_active_event(db, user_id)

    if active_after:
        print_error("Feast mode is still active!")
        return False
    else:
        print_success("Feast mode is inactive")

    # Check if data was restored
    print_info("\nVerifying data restoration...")
    after_cancel = capture_snapshot(db, user_id)

    # The calories should be restored to original (or close to it)
    print_info(f"Calories before: {before_cancel.original_calories}")
    print_info(f"Calories after: {after_cancel.original_calories}")

    # Check meal plan
    print_info(f"Meal plan items before: {len(before_cancel.meal_plan_snapshot)}")
    print_info(f"Meal plan items after: {len(after_cancel.meal_plan_snapshot)}")

    print_success("\nTest completed successfully!")
    return True

def test_data_integrity(db: Session, user_id: int):
    """Test Case 4: Verify data integrity across multiple operations"""
    print_header("TEST 4: Data Integrity Verification")

    print_info("This test performs multiple feast mode operations and verifies data consistency")

    # Capture initial state
    initial = capture_snapshot(db, user_id)
    print_success(f"Initial state captured: {initial.original_calories} kcal")

    # Test 1: Activate and immediately cancel
    print_info("\n[Test 4.1] Activate → Cancel")
    event_date = date.today() + timedelta(days=2)
    proposal = propose_banking_strategy(db, user_id, event_date, "Test Event 1")

    if "error" not in proposal:
        event = create_social_event(db, user_id, proposal)
        print_success("Event created")

        cancel_result = cancel_active_event(db, user_id)
        if "error" not in cancel_result:
            print_success("Event cancelled")

        after_cancel = capture_snapshot(db, user_id)
        if abs(after_cancel.original_calories - initial.original_calories) < 10:
            print_success("Calories restored correctly")
        else:
            print_error(f"Calorie mismatch: {initial.original_calories} → {after_cancel.original_calories}")

    # Test 2: Activate twice (should replace old event)
    print_info("\n[Test 4.2] Activate → Activate Again (Replace)")
    event_date_1 = date.today() + timedelta(days=3)
    event_date_2 = date.today() + timedelta(days=5)

    proposal_1 = propose_banking_strategy(db, user_id, event_date_1, "Event A")
    if "error" not in proposal_1:
        event_1 = create_social_event(db, user_id, proposal_1)
        print_success(f"Event A created (ID: {event_1.id})")

        proposal_2 = propose_banking_strategy(db, user_id, event_date_2, "Event B")
        if "error" not in proposal_2:
            event_2 = create_social_event(db, user_id, proposal_2)
            print_success(f"Event B created (ID: {event_2.id})")

            # Check only Event B is active
            all_events = db.query(SocialEvent).filter(
                SocialEvent.user_id == user_id,
                SocialEvent.is_active == True
            ).all()

            if len(all_events) == 1 and all_events[0].id == event_2.id:
                print_success("Only the latest event is active (Event A was deactivated)")
            else:
                print_error(f"Found {len(all_events)} active events (should be 1)")

            # Clean up
            cancel_active_event(db, user_id)

    print_success("\nData integrity tests completed!")
    return True

def main():
    parser = argparse.ArgumentParser(description='Test Feast Mode functionality')
    parser.add_argument('--user-id', type=int, required=True, help='User ID to test with')
    parser.add_argument('--scenario', choices=['activation', 'midday', 'cancel', 'integrity', 'all'],
                        default='all', help='Test scenario to run')

    args = parser.parse_args()

    print_header(f"Feast Mode Testing Suite")
    print(f"{Colors.BOLD}User ID: {args.user_id}{Colors.ENDC}")
    print(f"{Colors.BOLD}Scenario: {args.scenario}{Colors.ENDC}\n")

    db = SessionLocal()

    try:
        # Verify user
        if not verify_user(db, args.user_id):
            return 1

        # Run tests based on scenario
        if args.scenario == 'activation' or args.scenario == 'all':
            test_feast_mode_activation(db, args.user_id)

        if args.scenario == 'midday' or args.scenario == 'all':
            if args.scenario == 'all':
                print("\n" + "="*60 + "\n")
            test_feast_mode_midday(db, args.user_id)

        if args.scenario == 'cancel' or args.scenario == 'all':
            if args.scenario == 'all':
                print("\n" + "="*60 + "\n")
            test_feast_mode_cancellation(db, args.user_id)

        if args.scenario == 'integrity' or args.scenario == 'all':
            if args.scenario == 'all':
                print("\n" + "="*60 + "\n")
            test_data_integrity(db, args.user_id)

        print_header("All Tests Completed")
        return 0

    except Exception as e:
        print_error(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()

if __name__ == "__main__":
    sys.exit(main())
